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
        wc_updated = sync_world_cup_schedule()
        logger.info(f"🔄 [scheduler] World Cup results synced. Changes detected: {wc_updated}")
        
        if wc_updated > 0:
            logger.info("🔄 [scheduler] Match finished/updated. Fetching players and retraining...")
            from etl.players_etl import sync_world_cup_players
            sync_world_cup_players()
            
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
            logger.info("✅ [scheduler] World Cup AI retrained successfully on new match data.")
            
    except Exception as e:
        logger.warning(f"⚠️  [scheduler] WC results sync/train failed: {e}")

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

        # ── Model 2: World Cup XGBoost ────────────────────────────────────
        t1 = time.time()
        try:
            import sys, os
            scripts_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "scripts"
            )
            if scripts_dir not in sys.path:
                sys.path.insert(0, scripts_dir)
                
            import importlib
            wc_mod = importlib.import_module("train_model_worldcup")
            importlib.reload(wc_mod)
            
            wc_mod.train()
            elapsed_2 = time.time() - t1
            logger.info(f"✅ [scheduler] World Cup model retrained in {elapsed_2:.0f}s")
            
        except Exception as e:
            elapsed_2 = time.time() - t1
            logger.error(f"❌ [scheduler] World Cup model retraining failed: {e}", exc_info=True)
            write_training_report(
                model_name="World Cup — XGBoost Ensemble",
                success=False,
                error=str(e),
                duration_seconds=elapsed_2,
            )

        logger.info("🤖 [scheduler] AI retraining cycle complete (Club Leagues & World Cup).")

    scheduler.add_job(
        _run_training,
        trigger=CronTrigger(hour=4, minute=30, timezone="Europe/Madrid"),
        id="daily_model_retrain",
        name="Daily: Retrain XGBoost Models + write training report",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 1.5 → Daily Auto-Retrain at 04:30 Madrid time (report → logs/training_report.log).")


    # ── Task 2+3: Unified cache refresh every 2 hours, 7 days a week ─────────
    # HuggingFace is always-on (no sleep), so we refresh uniformly.
    # ── Task 2: Cache refresh 144 veces al día (Mundial) ──────────────────────
    # Al estar desactivadas las ligas de clubes (ENABLE_CLUB_LEAGUES=false),
    # el coste es de solo 1 petición por refresco (Mundial).
    # Refrescando cada 10 min, 24 horas al día = 144 refrescos/día.
    # 144 peticiones × 30 días = 4320 peticiones/mes (presupuesto 4500 con 9 keys).
    scheduler.add_job(
        refresh_cache,
        trigger=CronTrigger(minute="0,10,20,30,40,50", timezone="Europe/Madrid"),
        id="daily_cache_refresh",
        name="144x/day cache refresh (WC only)",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("  ✓ Task 2 → Cache refresh cada 10 minutos 24/7 (~4320 créd/mes)")

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
