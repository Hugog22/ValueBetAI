"""
main.py
-------
FastAPI application entry point.

Architecture after the keep-alive + background-cache refactor:
  • All heavy computation lives in core/cache_service.py and is run by the
    Smart Scheduler (core/scheduler.py).
  • Public endpoints (jornada, parlay, super-boosts) ONLY read the in-RAM
    cache → response time < 10 ms.
  • /api/health is the UptimeRobot target — keeps Render awake every 10 min.
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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("🚀 Starting Value Betting API…")
        Base.metadata.create_all(bind=engine)

        # Pre-warm the cache synchronously so the very first request is instant.
        # If it fails (e.g. no odds yet), the scheduler will fill it later.
        logger.info("🔄 Pre-warming prediction cache at startup…")
        try:
            refresh_cache()
        except Exception as e:
            logger.warning(f"⚠️  Startup cache warm-up failed (will retry on next schedule): {e}")

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


# ---------------------------------------------------------------------------
# Health / Keep-Alive endpoint  ← UptimeRobot pings this every 10 min
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    """
    Lightweight liveness probe.
    UptimeRobot / external monitors should call this every 10 minutes to
    prevent Render's free tier from suspending the instance.
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
    """
    Returns the pre-computed list of upcoming La Liga matches with predictions.
    Data is refreshed by the Smart Scheduler (not on request).
    """
    cache = get_cache()
    jornada = cache.get("jornada", [])
    if not jornada and not is_cache_warm():
        # First-ever request before the scheduler had a chance to run
        return {"status": "warming_up", "data": [], "message": "Cache warming up, retry in a few seconds."}
    return jornada


@app.get("/api/perfect_parlay")
def get_perfect_parlay():
    """
    Returns the pre-computed perfect parlay selection.
    Data is refreshed by the Smart Scheduler (not on request).
    """
    cache = get_cache()
    parlay = cache.get("parlay", {})
    if not parlay and not is_cache_warm():
        return {"legs": [], "totalOdds": 1.0, "jointProbability": 0.0, "message": "Cache warming up…"}
    return parlay


@app.get("/api/super-boosts")
def get_super_boosts():
    """
    Returns the pre-computed super-boost opportunities.
    Data is refreshed by the Smart Scheduler (not on request).
    """
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
