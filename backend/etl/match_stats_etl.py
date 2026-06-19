import logging
import os
import json
import time
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from db.session import SessionLocal
from db.models import Match, Team, MatchTeamStatistics
from etl.world_cup_etl import _normalize_name, TEAM_ALIASES

logger = logging.getLogger(__name__)

MATCH_STATS_DELAY = timedelta(hours=2)
TRACKER_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "processed_match_stats.json")
SQUADS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "world_cup_squads.json")

def _get_headers():
    return {
        "x-rapidapi-key": settings.SOFASCORE_RAPIDAPI_KEY,
        "x-rapidapi-host": settings.SOFASCORE_RAPIDAPI_HOST,
        "Content-Type": "application/json"
    }

def find_sofascore_event(match: Match) -> int | None:
    if not settings.SOFASCORE_RAPIDAPI_KEY:
        logger.warning("[match_stats_etl] SOFASCORE_RAPIDAPI_KEY not set")
        return None

    home_target = _normalize_name(match.home_team.name)
    away_target = _normalize_name(match.away_team.name)
    match_ts = match.date.timestamp()

    url = f"https://{settings.SOFASCORE_RAPIDAPI_HOST}/api/sofascore/v1/search/matches"
    
    # Try searching with both team names combined first, then fallback to individual names
    queries = [
        f"{match.home_team.name} {match.away_team.name}",
        match.home_team.name,
        match.away_team.name
    ]

    for query in queries:
        try:
            resp = httpx.get(url, params={"q": query}, headers=_get_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            # The prompt says: "Respuesta: array de objetos."
            events = data if isinstance(data, list) else data.get("results", [])
            if not isinstance(events, list):
                events = data.get("events", []) # Just in case
                
            for event in events:
                if event.get("type") != "match":
                    continue
                    
                entity = event.get("entity", {})
                event_id = entity.get("id")
                event_ts = entity.get("timestamp", 0)
                
                home_name = _normalize_name(entity.get("homeTeam", {}).get("name", ""))
                away_name = _normalize_name(entity.get("awayTeam", {}).get("name", ""))
                
                # Check names
                match_teams = {home_target, away_target}
                
                # We check substring matches if perfect match fails, but start with equality check or inclusion
                if (home_name in match_teams or home_target in home_name) and (away_name in match_teams or away_target in away_name):
                    # Check timestamp diff <= 12 hours
                    if abs(event_ts - match_ts) <= 12 * 3600:
                        logger.info(f"[match_stats_etl] Found sofascore_event_id={event_id} for Match {match.id} (query: {query})")
                        return event_id
                        
        except Exception as e:
            logger.error(f"[match_stats_etl] Error finding sofascore event with query '{query}': {e}")
        
        # Rate limit between queries
        time.sleep(2)
        
    logger.warning(f"[match_stats_etl] Could not find event for {match.home_team.name} vs {match.away_team.name} on {match.date}")
    return None

def fetch_match_statistics(event_id: int) -> dict | None:
    url = f"https://{settings.SOFASCORE_RAPIDAPI_HOST}/api/sofascore/v1/match/statistics"
    
    try:
        resp = httpx.get(url, params={"match_id": event_id}, headers=_get_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Respuesta: array de objetos por "period"
        statistics = data if isinstance(data, list) else data.get("statistics", [])
        
        all_period = next((p for p in statistics if p.get("period") == "ALL"), None)
        if not all_period:
            return None
            
        groups = all_period.get("groups", [])
        if not groups:
            return None
            
        parsed_stats = {"home": {}, "away": {}}
        
        key_mapping = {
            "ballPossession": "possession_pct",
            "expectedGoals": "xg",
            "bigChanceCreated": "big_chances",
            "bigChanceScored": "big_chances_scored",
            "bigChanceMissed": "big_chances_missed",
            "totalShotsOnGoal": "shots_total",
            "shotsOnGoal": "shots_on_target",
            "shotsOffGoal": "shots_off_target",
            "blockedScoringAttempt": "shots_blocked",
            "totalShotsInsideBox": "shots_inside_box",
            "totalShotsOutsideBox": "shots_outside_box",
            "cornerKicks": "corners",
            "fouls": "fouls",
            "passes": "passes_total",
            "accuratePasses": "passes_accurate",
            "finalThirdEntries": "final_third_entries",
            "totalTackle": "tackles",
            "interceptionWon": "interceptions",
            "ballRecovery": "recoveries",
            "totalClearance": "clearances",
            "goalkeeperSaves": "goalkeeper_saves",
            "goalsPrevented": "goals_prevented",
            "yellowCards": "yellow_cards",
            "duelWonPercent": "duels_won_pct"
        }
        
        found_keys = set()
        
        for group in groups:
            for item in group.get("statisticsItems", []):
                key = item.get("key")
                found_keys.add(key)
                
                # Ignorar renderType=3 y valueType=team si no esta en el mapeo
                if item.get("valueType") == "team" and item.get("renderType") == 3 and key not in key_mapping:
                    continue
                    
                if key in key_mapping:
                    col_name = key_mapping[key]
                    
                    home_val = item.get("homeValue")
                    away_val = item.get("awayValue")
                    
                    parsed_stats["home"][col_name] = float(home_val) if home_val is not None else None
                    parsed_stats["away"][col_name] = float(away_val) if away_val is not None else None
                    
        # Log keys for summary as requested
        unmapped_keys = found_keys - set(key_mapping.keys())
        if unmapped_keys:
            logger.debug(f"[match_stats_etl] Unmapped keys for event {event_id}: {unmapped_keys}")
                    
        return parsed_stats
        
    except Exception as e:
        logger.error(f"[match_stats_etl] Error fetching match stats for event {event_id}: {e}")
        return None

def sync_finished_match_statistics() -> int:
    if not settings.SOFASCORE_RAPIDAPI_KEY:
        logger.warning("[match_stats_etl] Skipping sync: SOFASCORE_RAPIDAPI_KEY not set.")
        return 0

    db = SessionLocal()
    processed_matches = 0
    
    try:
        wc_team_names = []
        if os.path.exists(SQUADS_FILE):
            with open(SQUADS_FILE, "r") as f:
                squads_data = json.load(f)
                wc_team_names = list(squads_data.keys())
                
        if not wc_team_names:
            logger.warning("[match_stats_etl] world_cup_squads.json not found, cannot filter WC matches")
            return 0

        # Build a broader candidate set: canonical names from the JSON + any alias keys
        # that resolve to one of those names (e.g. "USA" → "United States").
        wc_canonical_set = set(wc_team_names)
        wc_candidate_names = set(wc_team_names)
        for alias_key, canonical in TEAM_ALIASES.items():
            if canonical in wc_canonical_set:
                wc_candidate_names.add(alias_key)

        wc_teams = db.query(Team).filter(Team.name.in_(wc_candidate_names)).all()
        wc_team_ids = [t.id for t in wc_teams]
        
        now = datetime.utcnow()
        threshold = now - MATCH_STATS_DELAY
        
        matches = db.query(Match).filter(
            Match.status.in_(["Finished", "AWARDED"]),
            Match.date <= threshold
        ).all()
        
        # Get IDs of all matches that already have statistics
        processed_match_ids = {
            m_id[0] for m_id in db.query(MatchTeamStatistics.match_id).distinct().all()
        }
        
        pending_matches = [
            m for m in matches 
            if m.id not in processed_match_ids 
            and (m.home_team_id in wc_team_ids or m.away_team_id in wc_team_ids)
        ]
        
        if not pending_matches:
            logger.debug("[match_stats_etl] No pending finished WC matches for stats sync.")
            return 0
            
        for match in pending_matches:
            # 1. Resolve sofascore_event_id
            if not match.sofascore_event_id:
                event_id = find_sofascore_event(match)
                if not event_id:
                    continue
                match.sofascore_event_id = event_id
                db.commit()
                time.sleep(2) # Rate limit
                
            # 2. Fetch statistics
            stats_data = fetch_match_statistics(match.sofascore_event_id)
            if not stats_data:
                logger.debug(f"[match_stats_etl] No stats available yet for match {match.id} (SofaScore ID: {match.sofascore_event_id})")
                continue
                
            # 3. Create MatchTeamStatistics rows
            home_stats = MatchTeamStatistics(
                match_id=match.id,
                team_id=match.home_team_id,
                is_home=True,
                **stats_data["home"]
            )
            
            away_stats = MatchTeamStatistics(
                match_id=match.id,
                team_id=match.away_team_id,
                is_home=False,
                **stats_data["away"]
            )
            
            db.add(home_stats)
            db.add(away_stats)
            
            processed_matches += 1
            logger.info(f"[match_stats_etl] Synced statistics for match {match.id}")
            time.sleep(2) # Rate limit
            
        db.commit()
                
    except Exception as e:
        logger.error(f"[match_stats_etl] Sync failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()
        
    return processed_matches

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sync_finished_match_statistics()
