"""
scheduler.py
-------------
Background APScheduler para QuantStake — HuggingFace (16 GB RAM, always-on).

Schedule:
  - ETL diario:      04:00 AM Madrid — sincroniza partidos de La Liga (Understat).
  - Retrain IA:      04:30 AM Madrid — reentrena el modelo XGBoost de La Liga.
  - Cache refresh:   Cada 2 horas 24/7 — 12 refrescos/día × 1 API call/refresco = 360 créditos/mes.
  - Bet settlement:  Cada hora (xx:05) — liquida apuestas en partidos finalizados.

All times are in Europe/Madrid timezone.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Europe/Madrid")


def _settle_and_refresh():
    """
    Composite job (hourly): sync La Liga results → settle pending bets →
    conditional cache refresh.
    """
    from core.config import settings

    # ── Step 1: Sync La Liga match results (Understat) ──────────────────────
    laliga_updated = 0
    try:
        from etl.run_etl import run_pipeline
        run_pipeline()
        laliga_updated = 1
        logger.info("🔄 [scheduler] La Liga ETL results synced.")
    except Exception as e:
        logger.warning(f"⚠️  [scheduler] La Liga ETL sync failed: {e}")

    # ── Step 2: Sync per-match team stats for finished matches ───────────────
    match_stats_updated = 0
    try:
        from etl.match_stats_etl import sync_finished_match_statistics
        match_stats_updated = sync_finished_match_statistics()
        if match_stats_updated > 0:
            logger.info(f"🔄 [scheduler] Synced stats for {match_stats_updated} finished matches.")
    except Exception as e:
        logger.warning(f"⚠️  [scheduler] Match stats sync failed: {e}", exc_info=True)

    # ── Step 3: Settle bets on newly-finished matches ────────────────────────
    from core.bet_settler import settle_pending_bets
    from core.cache_service import refresh_cache

    bets_settled = 0
    try:
        summary = settle_pending_bets()
        bets_settled = summary.get("settled", 0)
        if bets_settled > 0:
            logger.info(f"🔄 [scheduler] Settled {bets_settled} bets.")
    except Exception as e:
        logger.error(f"❌ [scheduler] settle_pending_bets failed: {e}", exc_info=True)

    # ── Step 4: Conditional cache refresh ───────────────────────────────────
    if bets_settled > 0 or laliga_updated > 0 or match_stats_updated > 0:
        try:
            logger.info("🔄 [scheduler] Triggering cache refresh.")
            refresh_cache()
        except Exception as e:
            logger.error(f"❌ [scheduler] refresh_cache failed: {e}", exc_info=True)
    else:
        logger.debug("[scheduler] No changes detected — skipping cache refresh.")


def start_scheduler():
    """
    Initialize and start the APScheduler.

    Registers:
      1. Daily ETL — match data from Understat (04:00 AM Madrid).
      2. Daily AI retrain — XGBoost La Liga model (04:30 AM Madrid).
      3. Cache refresh every 2 hours (12x/day, ~360 créditos/mes).
      4. Hourly bet settlement + conditional cache refresh (xx:05 Madrid).
    """
    from core.cache_service import refresh_cache
    from etl.run_etl import run_pipeline

    logger.info("🗓  Initializing Background Scheduler (Europe/Madrid)…")

    # ── Task 1: Daily ETL (Understat La Liga match data) ─────────────────────
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=4, minute=0, timezone="Europe/Madrid"),
        id="daily_match_etl",
        name="Daily: sync La Liga matches from Understat",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 1 → Daily La Liga ETL at 04:00 Madrid time.")

    # ── Task 2: Daily AI Retrain (La Liga XGBoost) ────────────────────────────
    def _run_training():
        """Daily La Liga AI retraining job (04:30 Madrid)."""
        import time, json, os, sys, importlib
        from core.training_reporter import write_training_report, REPORT_PATH

        logger.info("🤖 [scheduler] Starting La Liga AI retraining...")
        logger.info(f"📝 Training report → {REPORT_PATH}")

        t0 = time.time()
        try:
            scripts_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "scripts"
            )
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)

            train_mod = importlib.import_module("train_model_v2")
            importlib.reload(train_mod)
            train_mod.main()
            elapsed = time.time() - t0

            logger.info(f"✅ [scheduler] La Liga model retrained in {elapsed:.0f}s")

        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"❌ [scheduler] La Liga model retraining failed: {e}", exc_info=True)
            write_training_report(
                model_name="La Liga — XGBoost",
                success=False,
                error=str(e),
                duration_seconds=elapsed,
            )

    scheduler.add_job(
        _run_training,
        trigger=CronTrigger(hour=4, minute=30, timezone="Europe/Madrid"),
        id="daily_model_retrain",
        name="Daily: Retrain La Liga XGBoost model",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 2 → Daily La Liga AI retrain at 04:30 Madrid time.")

    # ── Task 3: Cache refresh every 15 minutos ────────────────────────────────
    # 1 API request per refresh (La Liga odds only).
    # 4 refreshes/hour × 24h × 30 days = ~2880 créditos/mes.
    # Gracias a la rotación de claves en odds_api.py, podemos soportar este volumen.
    scheduler.add_job(
        refresh_cache,
        trigger=CronTrigger(minute="*/15", timezone="Europe/Madrid"),
        id="cache_refresh",
        name="Every 15m: La Liga cache refresh",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 3 → Cache refresh every 15m (~2880 créd/mes).")

    # ── Task 4: Hourly bet settlement + conditional cache refresh ────────────
    scheduler.add_job(
        _settle_and_refresh,
        trigger=CronTrigger(minute=5, timezone="Europe/Madrid"),
        id="hourly_settle_and_refresh",
        name="Hourly: settle bets + refresh if needed",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 4 → Hourly bet settlement at xx:05 Madrid.")

    scheduler.start()
    logger.info("✅ Scheduler started — La Liga only, 360 créd/mes.")


def stop_scheduler():
    """Gracefully shut down the background scheduler."""
    if scheduler.running:
        logger.info("Shutting down Scheduler…")
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
