import logging
from datetime import datetime
from db.session import engine, SessionLocal, Base
from db.models import Team, Match
from etl.understat_api import get_laliga_historical_data
from etl.odds_api import get_laliga_odds, detect_super_boosts
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

            # Skip if already stored (avoid duplicates on re-run)
            existing = db.query(Match).filter(Match.api_football_id == understat_id).first()
            if existing:
                # Update status if match finished since last ETL run
                if existing.status != status:
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


def run_pipeline():
    init_db()
    fetch_and_store_laliga_matches()

    logger.info("Fetching current La Liga odds from Bet365...")
    try:
        odds_data = get_laliga_odds()
        boosts = detect_super_boosts(odds_data)
        logger.info(f"Detected {len(boosts)} potential Super Boosts.")
    except Exception as e:
        logger.error(f"Failed to fetch odds: {e}")


if __name__ == "__main__":
    run_pipeline()
