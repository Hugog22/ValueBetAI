"""
players_etl.py
--------------
Fetches and synchronizes player statistics from API-Football (api-sports.io).
Updates the Player database model.
"""

import logging
import os
import httpx
from datetime import datetime, timedelta
import time

from db.session import SessionLocal
from db.models import Team, Player, WorldCupTeamStats
from core.config import settings
import json

logger = logging.getLogger(__name__)

API_URL = "https://v3.football.api-sports.io"

# Minimum time after kickoff before we attempt to fetch /fixtures/players from
# API-Football. Right when football-data.org marks a match "Finished",
# API-Football usually hasn't finished publishing per-fixture player stats
# yet. This is just an optimization to avoid wasted API calls — if stats
# still aren't ready after this window, the match is retried on the next
# scheduler run (it's only added to processed_ids once real data comes back).
MATCH_STATS_DELAY = timedelta(hours=2)

def get_headers():
    return {
        "x-apisports-key": settings.API_SPORTS_KEY
    }

def fetch_team_api_football_id(team_name: str) -> int:
    """Finds the API-Football team ID for a given team name."""
    import time
    try:
        # Try exact name match
        resp = httpx.get(f"{API_URL}/teams", headers=get_headers(), params={"name": team_name})
        resp.raise_for_status()
        data = resp.json()
        
        # If no exact match, try search
        if not data.get("response"):
            time.sleep(6) # Respect rate limits
            resp = httpx.get(f"{API_URL}/teams", headers=get_headers(), params={"search": team_name})
            resp.raise_for_status()
            data = resp.json()
            
        if data.get("response"):
            # National teams often have national=True
            for t in data["response"]:
                if t["team"].get("national") is True:
                    return t["team"]["id"]
            return data["response"][0]["team"]["id"]
    except Exception as e:
        logger.error(f"[players_etl] Failed to find API-Football ID for {team_name}: {e}")
    return None

def sync_team_players(team_id_db: int, season: int = 2026) -> int:
    """Fetches players for a specific team and saves to the database."""
    db = SessionLocal()
    updated_count = 0
    try:
        team = db.query(Team).filter(Team.id == team_id_db).first()
        if not team:
            return 0
        
        if not team.api_football_id:
            api_id = fetch_team_api_football_id(team.name)
            if api_id:
                team.api_football_id = api_id
                db.commit()
            else:
                return 0
                
        # Fetch players
        # The /players endpoint is paginated, but usually a national team squad fits in 1 or 2 pages.
        page = 1
        total_pages = 1
        while page <= total_pages:
            resp = httpx.get(
                f"{API_URL}/players", 
                headers=get_headers(), 
                params={"team": team.api_football_id, "season": season, "page": page}
            )
            resp.raise_for_status()
            data = resp.json()
            
            paging = data.get("paging", {})
            total_pages = paging.get("total", 1)
            
            for item in data.get("response", []):
                p_data = item.get("player", {})
                s_data = item.get("statistics", [{}])[0] # Get first stat object (should be the WC/season stats)
                
                api_football_id = p_data.get("id")
                name = p_data.get("name")
                
                games = s_data.get("games", {})
                goals = s_data.get("goals", {})
                cards = s_data.get("cards", {})
                
                position = games.get("position")
                rating_str = games.get("rating")
                rating = float(rating_str) if rating_str else None
                
                matches_played = games.get("appearences") or 0
                minutes_played = games.get("minutes") or 0
                
                goals_total = goals.get("total") or 0
                assists_total = goals.get("assists") or 0
                
                yellow = cards.get("yellow") or 0
                red = cards.get("red") or 0
                
                if not api_football_id:
                    continue
                    
                player = db.query(Player).filter(Player.api_football_id == api_football_id).first()
                if player:
                    player.rating = rating
                    player.matches_played = matches_played
                    player.minutes_played = minutes_played
                    player.goals = goals_total
                    player.assists = assists_total
                    player.yellow_cards = yellow
                    player.red_cards = red
                    player.last_updated = datetime.utcnow()
                else:
                    player = Player(
                        api_football_id=api_football_id,
                        team_id=team.id,
                        name=name,
                        position=position,
                        rating=rating,
                        matches_played=matches_played,
                        minutes_played=minutes_played,
                        goals=goals_total,
                        assists=assists_total,
                        yellow_cards=yellow,
                        red_cards=red
                    )
                    db.add(player)
                updated_count += 1
            
            page += 1
            time.sleep(6) # Respect API rate limits
            
        db.commit()
        logger.info(f"[players_etl] Synced {updated_count} players for team {team.name}")
    except Exception as e:
        logger.error(f"[players_etl] Failed to sync players for team {team_id_db}: {e}")
        db.rollback()
    finally:
        db.close()
        
    return updated_count

def sync_world_cup_match_players():
    """
    Finds finished World Cup matches.
    Maps them to API-Football fixtures if not already mapped.
    Fetches per-match player stats from /fixtures/players.
    Updates the cumulative Player model and prevents double-counting using a local file.

    A match is only added to the processed list once API-Football actually
    returns player stats for it. If the fixture mapping fails, or
    /fixtures/players comes back empty (stats not published yet), the match
    is left unmarked and retried on the next scheduler run.
    """
    db = SessionLocal()
    processed_matches_file = os.path.join(os.path.dirname(__file__), "..", "data", "processed_player_stats.json")
    
    # Load already processed matches
    processed_ids = []
    if os.path.exists(processed_matches_file):
        with open(processed_matches_file, "r") as f:
            try:
                processed_ids = json.load(f)
            except:
                processed_ids = []

    try:
        from db.models import Match, Team
        from sqlalchemy import or_
        from etl.world_cup_etl import _normalize_name, TEAM_ALIASES

        # Load World Cup teams to filter matches.
        # Match by normalized name (the same normalization world_cup_etl.py
        # uses when creating Team rows), so this still works even if
        # world_cup_squads.json uses slightly different spellings/aliases
        # than the canonical Team.name values stored in the DB.
        squads_file = os.path.join(os.path.dirname(__file__), "..", "data", "world_cup_squads.json")
        wc_team_names = []
        if os.path.exists(squads_file):
            with open(squads_file, "r") as f:
                squads_data = json.load(f)
                wc_team_names = list(squads_data.keys())

        wc_team_ids = []
        if wc_team_names:
            normalized_wc_names = {
                _normalize_name(TEAM_ALIASES.get(n, n)) for n in wc_team_names
            }
            all_teams = db.query(Team).all()
            wc_team_ids = [t.id for t in all_teams if _normalize_name(t.name) in normalized_wc_names]
            if not wc_team_ids:
                logger.warning(
                    "[players_etl] world_cup_squads.json found but no Team names matched "
                    "(check for naming/alias mismatches). Falling back to all finished matches."
                )

        # Filter: Status is Finished AND (no usable WC team list, OR either
        # side of the match is a World Cup team). Checking both home and
        # away avoids silently skipping matches if only one side matches.
        query = db.query(Match).filter(Match.status == "Finished")
        if wc_team_ids:
            query = query.filter(
                or_(
                    Match.home_team_id.in_(wc_team_ids),
                    Match.away_team_id.in_(wc_team_ids),
                )
            )
        finished_matches = query.all()
        
        total_players_updated = 0
        now = datetime.utcnow()
        
        for match in finished_matches:
            if match.id in processed_ids:
                continue

            # Give API-Football time to publish per-fixture player stats
            # after the match ends. If this isn't ready yet, skip without
            # marking as processed — it'll be retried on the next run.
            if now - match.date < MATCH_STATS_DELAY:
                logger.info(
                    f"[players_etl] Match {match.id} ({match.home_team.name} vs {match.away_team.name}) "
                    f"finished recently ({match.date}); waiting before fetching player stats."
                )
                continue
                
            logger.info(f"[players_etl] Processing player stats for match {match.id} ({match.home_team.name} vs {match.away_team.name})")
            
            # Map to api_football_id if not present
            if not match.api_football_id:
                if not match.home_team.api_football_id:
                    match.home_team.api_football_id = fetch_team_api_football_id(match.home_team.name)
                    db.commit()
                
                if not match.home_team.api_football_id:
                    logger.warning(f"[players_etl] Could not find API id for {match.home_team.name}")
                    continue
                    
                match_date_str = match.date.strftime("%Y-%m-%d")
                
                # Fetch fixture by date and home team
                try:
                    resp = httpx.get(
                        f"{API_URL}/fixtures", 
                        headers=get_headers(), 
                        params={"date": match_date_str, "team": match.home_team.api_football_id}
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("response"):
                        fixture_id = data["response"][0]["fixture"]["id"]
                        match.api_football_id = fixture_id
                        db.commit()
                        logger.info(f"[players_etl] Mapped Match {match.id} to Fixture {fixture_id}")
                    else:
                        logger.warning(f"[players_etl] No fixture found for team {match.home_team.name} on {match_date_str}")
                        continue
                except Exception as e:
                    logger.error(f"[players_etl] Fixture search failed: {e}")
                    continue
            
            # Now we have match.api_football_id
            try:
                resp = httpx.get(
                    f"{API_URL}/fixtures/players",
                    headers=get_headers(),
                    params={"fixture": match.api_football_id}
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("response"):
                    # Fixture is mapped, but API-Football hasn't published
                    # player stats for it yet. Don't mark as processed —
                    # retry on the next run.
                    logger.info(
                        f"[players_etl] No player stats available yet for fixture "
                        f"{match.api_football_id} (match {match.id}). Will retry later."
                    )
                    continue

                for team_data in data.get("response", []):
                    team_api_id = team_data["team"]["id"]
                    
                    # find local team
                    local_team = db.query(Team).filter(Team.api_football_id == team_api_id).first()
                    if not local_team:
                        continue
                        
                    for p in team_data.get("players", []):
                        player_info = p.get("player", {})
                        stats = p.get("statistics", [{}])[0]
                        
                        api_football_id = player_info.get("id")
                        if not api_football_id:
                            continue
                            
                        name = player_info.get("name")
                        
                        games = stats.get("games", {})
                        goals = stats.get("goals", {})
                        cards = stats.get("cards", {})
                        
                        minutes = games.get("minutes") or 0
                        rating_str = games.get("rating")
                        rating = float(rating_str) if rating_str else None
                        
                        goals_scored = goals.get("total") or 0
                        assists = goals.get("assists") or 0
                        
                        yellow = cards.get("yellow") or 0
                        red = cards.get("red") or 0
                        
                        # Find or create player
                        player = db.query(Player).filter(Player.api_football_id == api_football_id).first()
                        if player:
                            if minutes > 0:
                                player.matches_played = (player.matches_played or 0) + 1
                            player.minutes_played = (player.minutes_played or 0) + minutes
                            player.goals = (player.goals or 0) + goals_scored
                            player.assists = (player.assists or 0) + assists
                            player.yellow_cards = (player.yellow_cards or 0) + yellow
                            player.red_cards = (player.red_cards or 0) + red
                            if rating is not None:
                                player.rating = rating  # update to latest rating
                            player.last_updated = datetime.utcnow()
                        else:
                            player = Player(
                                api_football_id=api_football_id,
                                team_id=local_team.id,
                                name=name,
                                position=games.get("position"),
                                rating=rating,
                                matches_played=1 if minutes > 0 else 0,
                                minutes_played=minutes,
                                goals=goals_scored,
                                assists=assists,
                                yellow_cards=yellow,
                                red_cards=red
                            )
                            db.add(player)
                        
                        total_players_updated += 1
                        
                # Mark match as processed — only reached if API-Football
                # actually returned player stats for this fixture.
                processed_ids.append(match.id)
                # Ensure data directory exists
                os.makedirs(os.path.dirname(processed_matches_file), exist_ok=True)
                with open(processed_matches_file, "w") as f:
                    json.dump(processed_ids, f)
                    
                db.commit()
                time.sleep(15) # Increase sleep to 15s to respect 10 req/min API-Football free plan limits
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.error(f"[players_etl] Rate limit exceeded for fixture {match.api_football_id}. Try again later.")
                else:
                    logger.error(f"[players_etl] Failed to fetch players for fixture {match.api_football_id}: {e}")
            except Exception as e:
                logger.error(f"[players_etl] Failed to fetch players for fixture {match.api_football_id}: {e}")
                
        return total_players_updated
    finally:
        db.close()

if __name__ == "__main__":
    sync_world_cup_match_players()
