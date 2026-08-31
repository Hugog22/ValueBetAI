import logging
from datetime import datetime
from db.session import engine, SessionLocal, Base
from db.models import Team, Match
from etl.understat_api import get_laliga_historical_data
from etl.odds_api import get_laliga_odds, detect_super_boosts
from etl.update_characteristics import update_team_characteristics
from core.config import get_current_season

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_db():
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)


def fetch_and_store_laliga_matches(season: str | None = None):
    """
    Fetches all La Liga matches for the current season from Understat
    and stores them in the database. Handles both played and unplayed matches.
    """
    if season is None:
        season = str(get_current_season())

    logger.info(f"Fetching La Liga match data from Understat for season {season}")
    matches = get_laliga_historical_data(season=season)
    logger.info(f"Downloaded {len(matches)} matches from Understat.")

    db = SessionLocal()
    stored_count = 0
    try:
        for m in matches:
            home_team_name = m["h"]["title"]
            away_team_name = m["a"]["title"]

            # Upsert teams
            for t_name in [home_team_name, away_team_name]:
                if not db.query(Team).filter(Team.name == t_name).first():
                    db.add(Team(name=t_name))
            db.flush()

            home_team = db.query(Team).filter(Team.name == home_team_name).first()
            away_team = db.query(Team).filter(Team.name == away_team_name).first()

            # Parse match date — Understat gives "YYYY-MM-DD HH:MM:SS"
            try:
                match_date = datetime.strptime(m["datetime"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, KeyError):
                match_date = datetime.utcnow()

            is_played = m.get("isResult", False)
            status = "Finished" if is_played else "Not Started"

            # Goals and xG are None for unplayed matches – handle gracefully
            home_goals = int(m["goals"]["h"]) if is_played and m["goals"]["h"] is not None else None
            away_goals = int(m["goals"]["a"]) if is_played and m["goals"]["a"] is not None else None
            home_xg    = float(m["xG"]["h"]) if is_played and m["xG"]["h"] is not None else None
            away_xg    = float(m["xG"]["a"]) if is_played and m["xG"]["a"] is not None else None

            # Understat match IDs are stored in api_football_id column for cross-referencing
            understat_id = int(m.get("id", 0))

            # Match existing by api_football_id or (home_team, away_team, same day)
            existing = None
            if understat_id > 0:
                existing = db.query(Match).filter(Match.api_football_id == understat_id).first()

            if not existing and home_team and away_team:
                from datetime import timedelta
                day_start = match_date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                existing = db.query(Match).filter(
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.date >= day_start,
                    Match.date < day_end
                ).first()

            if existing:
                # Assign understat_id if missing
                if understat_id > 0 and not existing.api_football_id:
                    existing.api_football_id = understat_id
                # Update status and scores if match finished or goals were missing
                if existing.status != status or (is_played and existing.home_goals is None):
                    existing.status = status
                    existing.home_goals = home_goals
                    existing.away_goals = away_goals
                    existing.home_xg = home_xg
                    existing.away_xg = away_xg
                continue

            match_model = Match(
                api_football_id=understat_id,
                date=match_date,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_goals=home_goals,
                away_goals=away_goals,
                home_xg=home_xg,
                away_xg=away_xg,
                status=status,
            )
            db.add(match_model)
            stored_count += 1

        db.commit()
        logger.info(f"ETL complete: {stored_count} new matches stored.")
    except Exception as e:
        logger.error(f"Error during ETL: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def sync_football_data_results() -> int:
    """
    Syncs finished match scores and statuses from Football-Data.org API
    for La Liga matches, updates match records in DB, and settles pending bets.
    """
    key = settings.FOOTBALL_DATA_API_KEY
    if not key:
        logger.warning("⚠️ FOOTBALL_DATA_API_KEY not configured — skipping football-data sync.")
        return 0

    url = "https://api.football-data.org/v4/competitions/PD/matches"
    headers = {"X-Auth-Token": key}
    
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"⚠️ Football-Data API returned status {resp.status_code}")
                return 0
            data = resp.json()
            fd_matches = data.get("matches", [])
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch Football-Data.org matches: {e}")
        return 0

    db = SessionLocal()
    updated_count = 0
    try:
        def normalize_name(name: str) -> str:
            name = name.lower()
            replacements = {
                'deportivo alavés': 'alavés',
                'rcd espanyol de barcelona': 'espanyol',
                'rc deportivo la coruña': 'deportivo la coruña',
                'rayo vallecano de madrid': 'rayo vallecano',
                'getafe cf': 'getafe',
                'sevilla fc': 'sevilla',
                'villarreal cf': 'villarreal',
                'levante ud': 'levante',
                'elche cf': 'elche cf',
                'fc barcelona': 'barcelona',
                'real madrid cf': 'real madrid',
                'atletico madrid': 'atlético madrid',
                'atlético de madrid': 'atlético madrid',
                'athletic club': 'athletic bilbao',
                'real betis balompié': 'real betis',
                'real sociedad de fútbol': 'real sociedad',
                'celta de vigo': 'celta vigo',
                'rc celta de vigo': 'celta vigo',
                'valencia cf': 'valencia',
                'ca osasuna': 'ca osasuna',
                'málaga cf': 'málaga'
            }
            for k, v in replacements.items():
                if k in name:
                    return v
            return name

        teams = {t.id: normalize_name(t.name) for t in db.query(Team).all()}
        db_matches = db.query(Match).all()

        for f in fd_matches:
            if f.get("status") != "FINISHED":
                continue
            
            h_name = normalize_name(f["homeTeam"]["name"])
            a_name = normalize_name(f["awayTeam"]["name"])
            h_goals = f["score"]["fullTime"]["home"]
            a_goals = f["score"]["fullTime"]["away"]
            
            for m in db_matches:
                db_h = teams.get(m.home_team_id, "")
                db_a = teams.get(m.away_team_id, "")
                
                if db_h and db_a and (db_h in h_name or h_name in db_h) and (db_a in a_name or a_name in db_a):
                    if m.status != "Finished" or m.home_goals != h_goals or m.away_goals != a_goals:
                        m.status = "Finished"
                        m.home_goals = h_goals
                        m.away_goals = a_goals
                        updated_count += 1
                        logger.info(f"✅ Synced finished match #{m.id}: {db_h} vs {db_a} ({h_goals}-{a_goals})")

        db.commit()
    except Exception as e:
        logger.error(f"❌ Error syncing Football-Data results: {e}")
        db.rollback()
    finally:
        db.close()

    return updated_count


def run_pipeline():
    init_db()
    
    try:
        fetch_and_store_laliga_matches()
    except Exception as e:
        logger.error(f"Failed to fetch historical data from Understat: {e}")

    try:
        sync_count = sync_football_data_results()
        logger.info(f"Synced {sync_count} match results from Football-Data.org")
    except Exception as e:
        logger.error(f"Failed to sync Football-Data results: {e}")

    logger.info("⚙️ Auto-updating Team Characteristics based on recent performance...")
    try:
        update_team_characteristics()
    except Exception as e:
        logger.error(f"Failed to update team characteristics: {e}")

    logger.info("Fetching current La Liga odds from Bet365...")
    try:
        odds_data = get_laliga_odds()
        boosts = detect_super_boosts(odds_data)
        logger.info(f"Detected {len(boosts)} potential Super Boosts.")
    except Exception as e:
        logger.error(f"Failed to fetch odds: {e}")

    # ── Settle bets for any matches that just finished ──────────────────────
    logger.info("🎲 Settling pending bets for newly finished matches...")
    try:
        from core.bet_settler import settle_pending_bets
        summary = settle_pending_bets()
        logger.info(
            f"✅ Bet settlement complete: {summary['won']} Won / "
            f"{summary['lost']} Lost / {summary['void']} Void"
        )
    except Exception as e:
        logger.error(f"Bet settlement failed: {e}")

    # ── Refresh the AI prediction cache after new data ──────────────────────
    logger.info("🔄 Refreshing AI prediction cache post-ETL...")
    try:
        from core.cache_service import refresh_cache
        refresh_cache()
    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")


if __name__ == "__main__":
    run_pipeline()
