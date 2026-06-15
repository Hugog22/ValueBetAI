"""
world_cup_etl.py
----------------
ETL pipeline for FIFA World Cup 2026 match data.

Two data sources:
  1. The Odds API  — live upcoming match odds (h2h, over/under)
  2. football-data.org — official match schedule + team info

Syncs Teams + Matches + Odds into the database for the cache evaluator.
"""

import logging
import os
import unicodedata
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# The Odds API sport key for FIFA World Cup
WC_ODDS_KEY = "soccer_fifa_world_cup"

# football-data.org
FD_BASE      = "https://api.football-data.org/v4"
FD_WC_CODE   = "WC"

# Internal sport key
SPORT_KEY = "worldcup"

# Team name aliases (various APIs use different names for the same team)
# IMPORTANT: both source name AND all variants must map to the SAME canonical name
TEAM_ALIASES: dict[str, str] = {
    # API-Sports / Odds API variants
    "USA":                          "United States",
    "Korea Republic":               "South Korea",
    "Republic of Korea":            "South Korea",
    "Türkiye":                      "Turkey",
    "Czech Republic":               "Czechia",
    "IR Iran":                      "Iran",
    "Côte d'Ivoire":                "Ivory Coast",
    # Bosnia variants — the most common source of duplicates
    "Bosnia-Herzegovina":           "Bosnia and Herzegovina",
    "Bosnia & Herzegovina":         "Bosnia and Herzegovina",
    # Other hyphenated variants
    "Guinea-Bissau":                "Guinea Bissau",
    "Equatorial-Guinea":            "Equatorial Guinea",
    # Football-data.org variants
    "North Macedonia":              "North Macedonia",
    "DR Congo":                     "Democratic Republic of Congo",
    "Congo DR":                     "Democratic Republic of Congo",
    "Cape Verde Islands":           "Cape Verde",
    "Cabo Verde":                   "Cape Verde",
    "New Zealand":                  "New Zealand",
}


def _normalize_name(name: str) -> str:
    """Normalize team name: apply aliases, strip accents, lower, normalize separators."""
    # Apply alias first (catches 'Bosnia-Herzegovina' → 'Bosnia and Herzegovina')
    name = TEAM_ALIASES.get(name, name)
    # Normalize hyphenated country names to space-separated
    # so 'Bosnia-Herzegovina' == 'Bosnia and Herzegovina' after alias is applied
    nfkd  = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Replace hyphens used as conjunctions with a space for comparison purposes
    ascii_name = ascii_name.replace("-", " ")
    return ascii_name.lower().strip()


def _get_or_create_team(db: Session, name: str):
    from db.models import Team
    norm = _normalize_name(name)
    teams = db.query(Team).all()
    for t in teams:
        if _normalize_name(t.name) == norm:
            return t
    t = Team(name=name)
    db.add(t)
    db.flush()
    return t


def sync_world_cup_odds() -> int:
    """
    Fetch World Cup matches from The Odds API and sync to DB.
    Returns number of new matches inserted.
    """
    from db.session import SessionLocal
    from db.models import Team, Match, Odds
    from core.config import settings
    from etl.odds_api import fetch_with_rotation

    db = SessionLocal()
    new_count = 0

    try:
        url = f"https://api.the-odds-api.com/v4/sports/{WC_ODDS_KEY}/odds"
        params = {
            "apiKey":     settings.ODDS_API_KEY,
            "regions":    "eu,uk",
            "markets":    "h2h,totals",
            "oddsFormat": "decimal",
        }

        resp = fetch_with_rotation(url, params=params, timeout=30)
        if resp.status_code == 422:
            logger.warning(f"[world_cup_etl] 422 from Odds API — {WC_ODDS_KEY} may not be available yet")
            return 0
        if resp.status_code == 401:
            logger.warning("[world_cup_etl] Odds API auth error — check ODDS_API_KEYS")
            return 0
        resp.raise_for_status()
        events = resp.json()
        logger.info(f"[world_cup_etl] {len(events)} World Cup events from The Odds API")

        for event in events:
            home_name = event.get("home_team", "")
            away_name = event.get("away_team", "")
            commence  = event.get("commence_time", "")

            if not home_name or not away_name or not commence:
                continue

            try:
                match_date = datetime.strptime(commence[:19], "%Y-%m-%dT%H:%M:%S")
            except (ValueError, TypeError):
                match_date = datetime.utcnow() + timedelta(days=1)

            if match_date < datetime.utcnow():
                continue

            # Apply TEAM_ALIASES before lookup so both API sources use the
            # same canonical team name, preventing duplicate Team rows.
            canonical_home = TEAM_ALIASES.get(home_name, home_name)
            canonical_away = TEAM_ALIASES.get(away_name, away_name)
            home_team = _get_or_create_team(db, canonical_home)
            away_team = _get_or_create_team(db, canonical_away)

            # Upsert match
            existing = (
                db.query(Match)
                .filter(
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.date >= match_date - timedelta(hours=3),
                    Match.date <= match_date + timedelta(hours=3),
                )
                .first()
            )

            if not existing:
                # El usuario ha pedido que The Odds API solo se use para cuotas.
                # Si el partido no existe todavía (no lo ha bajado football-data.org), lo saltamos.
                continue
                
            match = existing

            # Store h2h odds for all bookmakers
            bookmakers = event.get("bookmakers", [])
            for bookmaker in bookmakers:
                bm_key = bookmaker.get("key")
                if not bm_key:
                    continue
                for mkt in bookmaker.get("markets", []):
                    if mkt["key"] != "h2h":
                        continue
                    outcomes = mkt.get("outcomes", [])
                    ho = dr = aw = 0.0
                    for o in outcomes:
                        nm = o["name"].strip().lower()
                        if nm == "draw":
                            dr = float(o["price"])
                        elif _normalize_name(o["name"]) in _normalize_name(home_name) \
                                or _normalize_name(home_name) in _normalize_name(o["name"]):
                            ho = float(o["price"])
                        else:
                            aw = float(o["price"])
                    if ho and aw:
                        existing_odds = (
                            db.query(Odds)
                            .filter(Odds.match_id == match.id, Odds.market == "h2h",
                                    Odds.bookmaker == bm_key)
                            .first()
                        )
                        if existing_odds:
                            existing_odds.home_odds = ho
                            existing_odds.draw_odds = dr
                            existing_odds.away_odds = aw
                            existing_odds.timestamp = datetime.utcnow()
                        else:
                            db.add(Odds(
                                match_id=match.id, bookmaker=bm_key,
                                market="h2h",
                                home_odds=ho, draw_odds=dr, away_odds=aw,
                                timestamp=datetime.utcnow(),
                            ))

        db.commit()
        logger.info(f"[world_cup_etl] {new_count} new WC matches inserted")

    except Exception as e:
        logger.error(f"[world_cup_etl] Failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

    return new_count

def update_world_cup_team_stats(db: Session):
    from db.models import Match, Team, WorldCupTeamStats
    from sqlalchemy import or_, and_
    import json
    import os
    
    # Get only WC teams
    squads_file = os.path.join(os.path.dirname(__file__), "..", "data", "world_cup_squads.json")
    wc_team_names = []
    if os.path.exists(squads_file):
        with open(squads_file, "r") as f:
            squads_data = json.load(f)
            wc_team_names = list(squads_data.keys())
            
    if not wc_team_names:
        logger.warning("[world_cup_etl] world_cup_squads.json not found, skipping stats update")
        return
        
    teams = db.query(Team).filter(Team.name.in_(wc_team_names)).all()
    
    for team in teams:
        # Get all finished matches for this team
        matches = db.query(Match).filter(
            or_(Match.home_team_id == team.id, Match.away_team_id == team.id),
            Match.status == "Finished"
        ).all()
        
        if not matches:
            continue
            
        played = len(matches)
        goals_for = 0
        goals_against = 0
        wins = 0
        draws = 0
        losses = 0
        
        for m in matches:
            if m.home_team_id == team.id:
                gf = m.home_goals or 0
                ga = m.away_goals or 0
            else:
                gf = m.away_goals or 0
                ga = m.home_goals or 0
                
            goals_for += gf
            goals_against += ga
            
            if gf > ga:
                wins += 1
            elif gf < ga:
                losses += 1
            else:
                draws += 1
                
        stats = db.query(WorldCupTeamStats).filter(WorldCupTeamStats.team_id == team.id).first()
        if stats:
            stats.matches_played = played
            stats.goals_for = goals_for
            stats.goals_against = goals_against
            stats.wins = wins
            stats.draws = draws
            stats.losses = losses
            stats.last_updated = datetime.utcnow()
        else:
            stats = WorldCupTeamStats(
                team_id=team.id,
                matches_played=played,
                goals_for=goals_for,
                goals_against=goals_against,
                wins=wins,
                draws=draws,
                losses=losses
            )
            db.add(stats)
            
    db.commit()
    logger.info("[world_cup_etl] WorldCupTeamStats updated.")



def sync_world_cup_schedule() -> int:
    """
    Fetch official World Cup 2026 schedule from football-data.org.
    More reliable for match timing than Odds API.
    Returns number of new matches inserted.
    """
    fd_key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if not fd_key:
        try:
            from core.config import settings
            fd_key = getattr(settings, "FOOTBALL_DATA_API_KEY", "")
        except Exception:
            pass

    if not fd_key:
        logger.warning("[world_cup_etl] FOOTBALL_DATA_API_KEY not set — skipping schedule sync")
        return 0

    from db.session import SessionLocal
    from db.models import Match

    db = SessionLocal()
    new_count = 0

    try:
        headers = {"X-Auth-Token": fd_key}
        url     = f"{FD_BASE}/competitions/{FD_WC_CODE}/matches"
        
        # Retry mechanism for transient network errors
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = httpx.get(url, headers=headers, timeout=30)
                break
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"[world_cup_etl] Network error during schedule sync (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(2 * (attempt + 1))
        if resp.status_code in (404, 422):
            logger.warning("[world_cup_etl] WC schedule not available on football-data.org yet")
            return 0
        resp.raise_for_status()
        matches = resp.json().get("matches", [])
        logger.info(f"[world_cup_etl] {len(matches)} WC matches from football-data.org")

        for raw in matches:
            status = raw.get("status", "")

            home_name = raw.get("homeTeam", {}).get("name", "")
            away_name = raw.get("awayTeam", {}).get("name", "")
            utc_date  = raw.get("utcDate", "")
            stage     = raw.get("stage", "").lower()

            if not home_name or not away_name or not utc_date:
                continue

            try:
                match_date = datetime.strptime(utc_date[:19], "%Y-%m-%dT%H:%M:%S")
            except (ValueError, TypeError):
                continue

            home_team = _get_or_create_team(db, TEAM_ALIASES.get(home_name, home_name))
            away_team = _get_or_create_team(db, TEAM_ALIASES.get(away_name, away_name))

            existing = (
                db.query(Match)
                .filter(
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.date >= match_date - timedelta(hours=3),
                    Match.date <= match_date + timedelta(hours=3),
                )
                .first()
            )

            db_status = "Finished" if status in ("FINISHED", "AWARDED") else "Not Started"
            home_goals = None
            away_goals = None
            if db_status == "Finished":
                score = raw.get("score", {}).get("fullTime", {})
                home_goals = score.get("home")
                away_goals = score.get("away")

            if not existing:
                db.add(Match(
                    date=match_date,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    status=db_status,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    stage=stage,
                ))
                new_count += 1
            else:
                if existing.status != db_status or existing.home_goals != home_goals or existing.away_goals != away_goals or existing.stage != stage:
                    existing.status = db_status
                    existing.home_goals = home_goals
                    existing.away_goals = away_goals
                    existing.stage = stage
                    new_count += 1

        db.commit()
        logger.info(f"[world_cup_etl] {new_count} new WC matches from football-data.org schedule")
        
        # Update WorldCupTeamStats based on latest results
        update_world_cup_team_stats(db)

    except Exception as e:
        logger.error(f"[world_cup_etl] Schedule sync failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

    return new_count



def get_world_cup_team_names() -> set[str]:
    """Return the set of all 48 World Cup 2026 national team names."""
    from models.world_cup_predictor import FIFA_POINTS, TEAM_ALIASES
    names = set(FIFA_POINTS.keys())
    names.update(TEAM_ALIASES.keys())
    return names
