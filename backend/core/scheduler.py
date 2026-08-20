"""
scheduler.py
-------------
Background APScheduler para ValueBetAI — HuggingFace (16 GB RAM, always-on).

Schedule:
  - ETL diario:      04:00 AM Madrid — sincroniza partidos de Understat.
  - Retrain IA:      04:30 AM Madrid — reentrena los modelos XGBoost.
  - Cache refresh:   3 veces/día (08h, 14h, 20h) — presupuesto ~360 créditos/mes.
                     Cada refresh cuesta 4 créditos (2 mercados × 2 regiones).
                     3 × 4 × 30 días = 360 créditos/mes (límite: 500, margen 28%).
  - Bet settlement:  Cada hora (xx:05) — liquida apuestas en partidos finalizados.

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
    Composite job: sync match results → sync per-match player stats →
    settle pending bets → retrain if needed → conditional cache refresh.
    """
    from core.config import settings

    # ── Step 1: Sync La Liga match results (Understat) ───────────────
    laliga_updated = 0
    if getattr(settings, 'enable_club_leagues', False):
        try:
            from etl.run_etl import run_pipeline
            run_pipeline()
            laliga_updated = 1  # run_pipeline doesn't return a count; assume changes possible
            logger.info("🔄 [scheduler] La Liga ETL results synced.")
        except Exception as e:
            logger.warning(f"⚠️  [scheduler] La Liga ETL sync failed: {e}")

    # ── Step 1b: Sync World Cup results (only if WC is not fully off-season) ──
    wc_updated = 0
    try:
        from etl.world_cup_etl import sync_world_cup_schedule
        wc_updated = sync_world_cup_schedule()
        if wc_updated:
            logger.info(f"🔄 [scheduler] World Cup results synced. Changes detected: {wc_updated}")
    except Exception as e:
        logger.warning(f"⚠️  [scheduler] WC results sync failed: {e}")

    # ── Step 1.5: Sync per-match team stats for finished matches ──────────
    match_stats_updated = 0
    try:
        from etl.match_stats_etl import sync_finished_match_statistics
        match_stats_updated = sync_finished_match_statistics()
        if match_stats_updated > 0:
            logger.info(f"🔄 [scheduler] Synced stats for {match_stats_updated} finished matches.")
    except Exception as e:
        logger.warning(f"⚠️  [scheduler] Match stats sync failed: {e}", exc_info=True)

    # ── Step 2: Settle bets on newly-finished matches ──────────────────
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

    # ── Step 3: Retrain model if new results came in ────────────────────
    if wc_updated > 0 or match_stats_updated > 0:
        try:
            logger.info("🔄 [scheduler] New match results/stats. Retraining World Cup AI...")

            import sys, os, importlib
            scripts_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "scripts"
            )
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
                
            fetch_mod = importlib.import_module("fetch_world_cup_data")
            importlib.reload(fetch_mod)
            fetch_mod.main(force=True)

            wc_mod = importlib.import_module("train_model_worldcup")
            importlib.reload(wc_mod)
            wc_mod.train()
            
            from core.shared_predictor import world_cup_predictor
            world_cup_predictor.load_model()
            
            logger.info("✅ [scheduler] World Cup AI retrained successfully on new match data.")
            
        except Exception as e:
            logger.warning(f"⚠️  [scheduler] WC retraining failed: {e}", exc_info=True)
            from core.training_reporter import write_training_report
            write_training_report(
                model_name="World Cup — XGBoost Ensemble",
                success=False,
                error=str(e),
                is_auto=True,
            )

    # ── Step 4: Conditional Cache Refresh ─────────────────────────────
    if bets_settled > 0 or wc_updated > 0 or match_stats_updated > 0 or laliga_updated > 0:
        try:
            logger.info("🔄 [scheduler] Triggering cache refresh due to settled bets, new results, or new player stats.")
            refresh_cache()
        except Exception as e:
            logger.error(f"❌ [scheduler] refresh_cache failed: {e}", exc_info=True)
    else:
        logger.debug("[scheduler] No bets settled and no matches/stats updated — skipping cache refresh.")


def start_scheduler():
    """
    Initialize and start the APScheduler.

    Registers:
      1. Daily ETL — match data from Understat (04:00 AM Madrid).
      2. Smart cache refresh (every 2 hours).
      3. Hourly bet settlement + cache refresh (every hour, all days).
    """
    from core.config import settings
    from core.cache_service import refresh_cache
    from etl.run_etl import run_pipeline

    logger.info("🗓  Initializing Smart Background Scheduler (Europe/Madrid)…")

    # ── Task 1: Daily ETL (Understat match data) ──────────────────────────────
    if settings.enable_club_leagues:
        scheduler.add_job(
            run_pipeline,
            trigger=CronTrigger(hour=4, minute=0, timezone="Europe/Madrid"),
            id="daily_match_etl",
            name="Daily: sync matches from Understat",
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info("  ✓ Task 1 → Daily ETL at 04:00 Madrid time.")

    # ── Task 1.5: Auto-Retrain ML Models (After ETL) ──────────────────────────
    def _run_training():
        """
        Daily AI retraining job (04:30 Madrid).

        Trains both the LaLiga/Premier/Champions XGBoost model and the
        World Cup model, then writes a detailed report to
        backend/logs/training_report.log showing what changed and why.
        """
        import time
        from core.training_reporter import write_training_report, REPORT_PATH

        logger.info("🤖 [scheduler] Starting automated AI retraining...")
        logger.info(f"📝 Training reports will be written to: {REPORT_PATH}")

        # ── Model 1: LaLiga / Premier / Champions XGBoost ─────────────────
        if settings.enable_club_leagues:
            t0 = time.time()
            try:
                # Import and run training directly (avoids subprocess overhead,
                # lets us capture the metadata dict that train() produces)
                import sys, os
                scripts_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "scripts"
                )
                if scripts_dir not in sys.path:
                    sys.path.insert(0, scripts_dir)
    
                import importlib
                train_mod = importlib.import_module("train_model")
                importlib.reload(train_mod)          # reload in case already imported once
    
                # train_model.train() saves models + returns nothing; meta is in META_PATH
                train_mod.train()
                elapsed_1 = time.time() - t0
    
                # Read the metadata it just wrote
                import json
                meta_path = train_mod.META_PATH
                meta = {}
                if os.path.exists(meta_path):
                    with open(meta_path) as f:
                        meta = json.load(f)
    
                write_training_report(
                    model_name="LaLiga / Premier / Champions — XGBoost",
                    success=True,
                    meta=meta,
                    duration_seconds=elapsed_1,
                )
                logger.info(f"✅ [scheduler] LaLiga model retrained in {elapsed_1:.0f}s")
    
            except Exception as e:
                elapsed_1 = time.time() - t0
                logger.error(f"❌ [scheduler] LaLiga model retraining failed: {e}", exc_info=True)
                write_training_report(
                    model_name="LaLiga / Premier / Champions — XGBoost",
                    success=False,
                    error=str(e),
                    duration_seconds=elapsed_1,
                )

        logger.info("🤖 [scheduler] AI retraining cycle complete (Club Leagues only).")

    scheduler.add_job(
        _run_training,
        trigger=CronTrigger(hour=4, minute=30, timezone="Europe/Madrid"),
        id="daily_model_retrain",
        name="Daily: Retrain XGBoost Models + write training report",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 1.5 → Daily Auto-Retrain at 04:30 Madrid time (report → logs/training_report.log).")


    # ── Task 2: Cache refresh — La Liga + multi-sport ────────────────────────
    # With ENABLE_CLUB_LEAGUES=true the refresh fetches La Liga, Premier and
    # Champions League odds (3 API requests per cycle).
    # 12 refreshes/day × 3 requests × 30 days = 1080 credits/month (well within free tier).
    scheduler.add_job(
        refresh_cache,
        trigger=CronTrigger(hour="0,2,4,6,8,10,12,14,16,18,20,22", timezone="Europe/Madrid"),
        id="daily_cache_refresh",
        name="12x/day cache refresh (La Liga primary)",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 2 → Cache refresh every 2h 24/7 (~1080 créd/mes)")

    # ── Task 3: Hourly bet settlement + conditional cache refresh ────────────
    scheduler.add_job(
        _settle_and_refresh,
        trigger=CronTrigger(minute=5, timezone="Europe/Madrid"),
        id="hourly_settle_and_refresh",
        name="Hourly: settle pending bets + refresh AI cache if needed",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 3 → Hourly bet settlement + conditional cache refresh (xx:05 Madrid).")

    scheduler.start()
    logger.info("✅ Scheduler iniciado (HuggingFace 16GB — refresh 16x/día, ~1920 créd/mes de 2500).")


def stop_scheduler():
    """Gracefully shut down the background scheduler."""
    if scheduler.running:
        logger.info("Shutting down Smart Scheduler…")
        scheduler.shutdown(wait=False)
        logger.info("Smart Scheduler stopped.")
