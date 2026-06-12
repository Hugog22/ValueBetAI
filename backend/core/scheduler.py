"""
scheduler.py
-------------
Background APScheduler with a *Smart Schedule* for The Odds API quota protection.

                 QUOTA BUDGET  (soccer_spain_la_liga free tier ≈ 500 req/month)
                 ───────────────────────────────────────────────────────────────
  Valley days  Mon–Thu  3 calls/day × 4 days = 12 calls/week
  Peak days    Fri–Sun  11 calls/day × 3 days = 33 calls/week
                                                ─────────────
  Weekly total  ≈ 45 calls/week  →  ~180 calls/month  (well under the 500 limit)

The CRON expressions are loaded from environment variables so they can be
adjusted in the Render dashboard without touching source code:
  CRON_WEEKDAY   default: "0 10,16,22 * * 1-4"   (Mon–Thu at 10h, 16h, 22h)
  CRON_WEEKEND   default: "0 12-22 * * 5,6,0"    (Fri–Sun every hour 12h–22h)

All times are in Europe/Madrid timezone.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Europe/Madrid")


def _parse_cron(expr: str) -> dict:
    """
    Parse a 5-field cron expression into APScheduler CronTrigger kwargs.
    Fields: minute hour day_of_month month day_of_week
    """
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression (expected 5 fields): {expr!r}"
        )
    minute, hour, day, month, day_of_week = parts
    return {
        "minute":       minute,
        "hour":         hour,
        "day":          day,
        "month":        month,
        "day_of_week":  day_of_week,
    }


def _settle_and_refresh():
    """
    Composite job: sync match results → settle pending bets → conditional cache refresh.

    Called hourly (xx:05) so that finished matches are detected promptly
    and bets get resolved within ~1 hour of match completion.

    Key insight: bet_settler requires Match.status == "Finished", but that
    status is only set by the ETL sync.  We MUST sync results first.
    """
    # ── Step 1: Sync match results from external sources ──────────────
    # This marks recently-finished matches as "Finished" in the DB.
    try:
        from etl.world_cup_etl import sync_world_cup_schedule
        sync_world_cup_schedule()
        logger.info("🔄 [scheduler] World Cup results synced.")
    except Exception as e:
        logger.warning(f"⚠️  [scheduler] WC results sync failed: {e}")

    try:
        from etl.run_etl import run_pipeline
        run_pipeline()
        logger.info("🔄 [scheduler] La Liga ETL results synced.")
    except Exception as e:
        logger.warning(f"⚠️  [scheduler] La Liga ETL sync failed: {e}")

    # ── Step 2: Settle bets on newly-finished matches ─────────────────
    from core.bet_settler import settle_pending_bets
    from core.cache_service import refresh_cache
    try:
        summary = settle_pending_bets()
        if summary.get("settled", 0) > 0:
            logger.info(f"🔄 [scheduler] Settled {summary['settled']} bets — triggering cache refresh.")
            refresh_cache()
        else:
            logger.debug("[scheduler] No bets settled — skipping cache refresh.")
    except Exception as e:
        logger.error(f"❌ [scheduler] settle_and_refresh failed: {e}", exc_info=True)


def start_scheduler():
    """
    Initialize and start the APScheduler.

    Registers:
      1. Daily ETL — match data from Understat (04:00 AM Madrid).
      2. Smart cache refresh (valley) — Mon–Thu: 10h, 16h, 22h Madrid.
      3. Smart cache refresh (peak)   — Fri–Sun: every hour 12h–22h Madrid.
      4. Hourly bet settlement + cache refresh (every hour, all days).
    """
    from core.config import settings
    from core.cache_service import refresh_cache
    from etl.run_etl import run_pipeline

    logger.info("🗓  Initializing Smart Background Scheduler (Europe/Madrid)…")

    # ── Task 1: Daily ETL (Understat match data) ──────────────────────────────
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=4, minute=0, timezone="Europe/Madrid"),
        id="daily_match_etl",
        name="Daily: sync matches from Understat",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("  ✓ Task 1 → Daily ETL at 04:00 Madrid time.")

    # ── Task 1.5: Auto-Retrain ML Models (After ETL) ──────────────────────────
    import subprocess
    def _run_training():
        logger.info("🤖 Starting automated ML retraining...")
        try:
            subprocess.run(["python", "scripts/train_model.py"], check=True)
            subprocess.run(["python", "scripts/train_model_worldcup.py"], check=True)
            logger.info("✅ ML retraining complete. Models updated.")
        except Exception as e:
            logger.error(f"❌ ML retraining failed: {e}")

    scheduler.add_job(
        _run_training,
        trigger=CronTrigger(hour=4, minute=30, timezone="Europe/Madrid"),
        id="daily_model_retrain",
        name="Daily: Retrain XGBoost Models",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info("  ✓ Task 1.5 → Daily Auto-Retrain at 04:30 Madrid time.")

    # ── Task 2: Valley days cache refresh (Mon–Thu) ───────────────────────────
    try:
        weekday_kwargs = _parse_cron(settings.CRON_WEEKDAY)
    except ValueError as e:
        logger.error(f"  ✗ Invalid CRON_WEEKDAY: {e}. Using default.")
        weekday_kwargs = _parse_cron("0 10,16,22 * * 1-4")

    scheduler.add_job(
        refresh_cache,
        trigger=CronTrigger(**weekday_kwargs, timezone="Europe/Madrid"),
        id="valley_cache_refresh",
        name="Valley (Mon–Thu): refresh predictions cache",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info(
        f"  ✓ Task 2 → Valley refresh | cron: \"{settings.CRON_WEEKDAY}\" (Europe/Madrid)"
    )

    # ── Task 3: Peak days cache refresh (Fri–Sun, hourly 12h–22h) ────────────
    try:
        weekend_kwargs = _parse_cron(settings.CRON_WEEKEND)
    except ValueError as e:
        logger.error(f"  ✗ Invalid CRON_WEEKEND: {e}. Using default.")
        weekend_kwargs = _parse_cron("0 12-22 * * 5,6,0")

    scheduler.add_job(
        refresh_cache,
        trigger=CronTrigger(**weekend_kwargs, timezone="Europe/Madrid"),
        id="peak_cache_refresh",
        name="Peak (Fri–Sun): refresh predictions cache hourly",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info(
        f"  ✓ Task 3 → Peak refresh   | cron: \"{settings.CRON_WEEKEND}\" (Europe/Madrid)"
    )

    # ── Task 4: Hourly bet settlement + conditional cache refresh ────────────
    scheduler.add_job(
        _settle_and_refresh,
        trigger=CronTrigger(minute=5, timezone="Europe/Madrid"),  # xx:05 every hour
        id="hourly_settle_and_refresh",
        name="Hourly: settle pending bets + refresh AI cache if needed",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("  ✓ Task 4 → Hourly bet settlement + conditional cache refresh (xx:05 Madrid).")

    scheduler.start()
    logger.info("✅ Smart Scheduler started. Quota budget: ~180 Odds API calls/month.")


def stop_scheduler():
    """Gracefully shut down the background scheduler."""
    if scheduler.running:
        logger.info("Shutting down Smart Scheduler…")
        scheduler.shutdown(wait=False)
        logger.info("Smart Scheduler stopped.")
