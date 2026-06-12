"""
main.py
-------
FastAPI application entry point — running on HuggingFace (16 GB RAM, always-on).

Architecture:
  • All heavy computation lives in core/cache_service.py and is run by the
    Background Scheduler (core/scheduler.py).
  • Public endpoints (jornada, parlay, super-boosts) ONLY read the in-RAM
    cache → response time < 10 ms.
  • /api/health is a standard liveness probe for monitoring.
"""

import sys
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from db.session import get_db, engine, Base
from db.models import Match
from core.scheduler import start_scheduler, stop_scheduler
from core.cache_service import get_cache, refresh_cache, is_cache_warm

# Routers
from routers.bets import router as bets_router
from routers.auth import router as auth_router
from routers.admin import router as admin_router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Starting Value Betting API…")
        Base.metadata.create_all(bind=engine)

        # Warm the cache in a daemon thread so the server binds quickly
        # while still loading predictions in the background.
        logger.info("🔄 Triggering background prediction cache warm-up…")
        import threading
        def _warm_cache_bg():
            # Step 1: Clean duplicate teams/matches in the DB
            try:
                from scripts.fix_duplicate_teams import fix_duplicate_teams
                from db.session import SessionLocal
                with SessionLocal() as db:
                    logger.info("🧹 Ejecutando limpieza de equipos duplicados en el arranque...")
                    fix_duplicate_teams(db)
                    logger.info("✅ Limpieza de duplicados completada.")
            except Exception as e:
                logger.error(f"⚠️ Failed to clean duplicates: {e}")

            # Step 2: Warm the prediction cache
            try:
                refresh_cache()
            except Exception as e:
                logger.warning(f"⚠️  Startup cache warm-up failed: {e}")

        threading.Thread(target=_warm_cache_bg, daemon=True).start()

        start_scheduler()
        yield
    except Exception as e:
        logger.error(f"CRITICAL: Application failed to start. Reason: {e}")
        sys.exit(1)
    finally:
        stop_scheduler()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Value Betting API",
    description="API for predictive sports betting",
    version="5.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bets_router)
app.include_router(auth_router)
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Health / Keep-Alive endpoint  ← UptimeRobot pings this every 10 min
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """
    Lightweight liveness probe for monitoring.
    """
    cache = get_cache()
    last_updated = cache.get("last_updated", 0.0)
    cache_age = round(time.time() - last_updated, 1) if last_updated else None
    return {
        "status":            "ok",
        "timestamp":         datetime.utcnow().isoformat() + "Z",
        "cache_warm":        is_cache_warm(),
        "cache_age_seconds": cache_age,
        "matches_cached":    len(cache.get("jornada", [])),
    }

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Value Betting API v5 — Smart Schedule edition"}


# ---------------------------------------------------------------------------
# Public data endpoints — READ-ONLY from RAM cache (< 10 ms)
# ---------------------------------------------------------------------------

@app.get("/api/matches/jornada")
def get_jornada():
    """Returns La Liga matches (default — backward compat)."""
    cache = get_cache()
    jornada = cache.get("jornada", [])
    if not jornada and not is_cache_warm():
        return {"status": "warming_up", "data": [], "message": "Cache warming up, retry in a few seconds."}
    return jornada


VALID_SPORTS = {"laliga", "premier", "champions", "worldcup"}

@app.get("/api/matches/{sport}/jornada")
def get_sport_jornada(sport: str):
    """Returns upcoming matches with AI predictions for the given sport."""
    if sport not in VALID_SPORTS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not supported. Valid: {sorted(VALID_SPORTS)}")
    cache = get_cache()
    jornada = cache.get("sports", {}).get(sport, {}).get("jornada", [])
    if not jornada and not is_cache_warm():
        return {"status": "warming_up", "data": [], "message": "Cache warming up, retry in a few seconds."}
    return jornada


@app.get("/api/perfect_parlay")
def get_perfect_parlay():
    """Returns La Liga parlay (backward compat)."""
    cache = get_cache()
    parlay = cache.get("parlay", {})
    if not parlay and not is_cache_warm():
        return {"legs": [], "totalOdds": 1.0, "jointProbability": 0.0, "message": "Cache warming up…"}
    return parlay


@app.get("/api/{sport}/parlay")
def get_sport_parlay(sport: str):
    """Returns the CombinAIA for the given sport."""
    if sport not in VALID_SPORTS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not supported.")
    cache = get_cache()
    parlay = cache.get("sports", {}).get(sport, {}).get("parlay", {})
    if not parlay and not is_cache_warm():
        return {"legs": [], "totalOdds": 1.0, "jointProbability": 0.0, "message": "Cache warming up…"}
    return parlay


@app.get("/api/sports/all_parlays")
def get_all_parlays():
    """
    Returns all active CombinAIas across every sport in a single call.
    Each entry includes sport key, flag emoji, label, and parlay legs.
    Frontend uses this to render the multi-parlay section.
    """
    cache = get_cache()
    return cache.get("all_parlays", [])


@app.get("/api/sports/status")
def get_sports_status():
    """
    Returns per-sport metadata: match count, off-season flag, label, flag emoji.
    Frontend uses this to show/hide off-season badges without loading matches.
    """
    from core.cache_service import get_sport_info, SUPPORTED_SPORTS
    return {sk: get_sport_info(sk) for sk in SUPPORTED_SPORTS}


@app.get("/api/super-boosts")
def get_super_boosts():
    cache = get_cache()
    return cache.get("boosts", [])


# ---------------------------------------------------------------------------
# Raw market data endpoint (on-demand DB query — low frequency)
# ---------------------------------------------------------------------------

@app.get("/api/matches/{match_id}/all-markets")
def get_match_all_markets(match_id: int, db: Session = Depends(get_db)):
    from db.models import MarketOdds
    odds = db.query(MarketOdds).filter(MarketOdds.match_id == match_id).all()
    if not odds:
        return {"error": "No odds found for this match"}
    res: dict = {}
    for o in odds:
        if o.market_key not in res:
            res[o.market_key] = {"bookmaker": o.bookmaker, "outcomes": []}
        res[o.market_key]["outcomes"].append({
            "name":  o.outcome_name,
            "price": o.price,
            "point": o.point,
        })
    return res


# ---------------------------------------------------------------------------
# Dev entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")
