import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# Import our ETL functions
from scripts.flush_odds import flush_and_reload
from etl.run_etl import run_pipeline

logger = logging.getLogger(__name__)

# Create a global background scheduler instance. 
# We use BackgroundScheduler because the ETL functions are synchronous 
# and this runs them in a separate thread pool without blocking FastAPI's async loop.
scheduler = BackgroundScheduler()

def start_scheduler():
    """
    Initializes and starts the APScheduler. 
    Registers the daily ETL pipeline and the 4-hour odds updates.
    """
    logger.info("Initializing Background Scheduler for ETL tasks...")

    # Task 1: Update API-Football matches and stats at 04:00 AM daily
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=4, minute=0),
        id="daily_match_etl",
        name="Update matches and team stats",
        replace_existing=True
    )
    logger.info("✓ Scheduled daily ETL for 04:00 AM.")

    # Task 2: Update Odds every 4 hours (ensures freshness without hitting The Odds API free limit)
    scheduler.add_job(
        flush_and_reload,
        trigger=IntervalTrigger(hours=4),
        id="four_hour_odds_flush",
        name="Update betting odds from The Odds API",
        replace_existing=True
    )
    logger.info("✓ Scheduled odds update for every 4 hours.")

    scheduler.start()
    logger.info("Background Scheduler started successfully.")

def stop_scheduler():
    """
    Gracefully shuts down the background scheduler.
    """
    if scheduler.running:
        logger.info("Shutting down Background Scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("Background Scheduler stopped.")
