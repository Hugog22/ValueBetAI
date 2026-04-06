import sys
import logging
import random
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from db.session import get_db, engine, Base
from db.models import Match
from core.scheduler import start_scheduler, stop_scheduler
from core.shared_predictor import predictor
from core.match_evaluator import _evaluate_match as _evaluate_match_core, _calculate_risk as _calculate_risk_core

# Local imports
from routers.bets import router as bets_router
from routers.auth import router as auth_router

logger = logging.getLogger(__name__)

# Global Cache for high-compute endpoints
_cache = {"jornada": {"time": 0, "data": []}, "parlay": {"time": 0, "data": {}}}
CACHE_TTL = 300

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Initializing Render Application Layer & Databases...")
        # Create tables only once at startup
        Base.metadata.create_all(bind=engine)
        start_scheduler()
        yield
    except Exception as e:
        logger.error(f"CRITICAL: Application failed to start. Reason: {str(e)}")
        sys.exit(1)
    finally:
        stop_scheduler()

app = FastAPI(
    title="Value Betting API",
    description="API for predictive sports betting",
    version="4.0.0",
    lifespan=lifespan
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

def _evaluate_match(match: Match, db: Session | None = None) -> dict:
    return _evaluate_match_core(match, predictor, db)

def _calculate_risk(prob: float, bookmaker_odds: float = 0.0) -> dict:
    return _calculate_risk_core(prob, bookmaker_odds)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Value Betting API v4 — Multi-market edition"}

@app.get("/api/matches/{match_id}/all-markets")
def get_match_all_markets(match_id: int, db: Session = Depends(get_db)):
    from db.models import MarketOdds
    odds = db.query(MarketOdds).filter(MarketOdds.match_id == match_id).all()
    if not odds:
        return {"error": "No odds found for this match"}
    res = {}
    for o in odds:
        if o.market_key not in res:
            res[o.market_key] = {"bookmaker": o.bookmaker, "outcomes": []}
        res[o.market_key]["outcomes"].append({
            "name": o.outcome_name,
            "price": o.price,
            "point": o.point
        })
    return res

@app.get("/api/matches/jornada")
def get_jornada(db: Session = Depends(get_db)):
    if time.time() - _cache["jornada"]["time"] < CACHE_TTL and _cache["jornada"]["data"]:
        return _cache["jornada"]["data"]

    now = datetime.utcnow()
    seven_days = now + timedelta(days=7)
    upcoming = (
        db.query(Match)
        .filter(Match.date >= now, Match.date <= seven_days)
        .order_by(Match.date.asc())
        .limit(15)
        .all()
    )
    if not upcoming:
        return []
    
    matches = [_evaluate_match(m, db) for m in upcoming]
    _cache["jornada"]["time"] = time.time()
    _cache["jornada"]["data"] = matches
    return matches

@app.get("/api/super-boosts")
def get_super_boosts(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    seven_days = now + timedelta(days=7)
    upcoming = (
        db.query(Match)
        .filter(Match.date >= now, Match.date <= seven_days)
        .order_by(Match.date.asc())
        .limit(10)
        .all()
    )
    boosts = []
    for m in upcoming:
        rng = random.Random(m.id + 9999)
        if rng.random() < 0.4:
            boosts.append({
                "match":        f"{m.home_team.name} vs {m.away_team.name}",
                "date":         m.date.isoformat() + "Z" if m.date else None,
                "market":       rng.choice(["Victoria Local", "Ambos Equipos Marcan", "Más de 2.5 Goles"]),
                "normalOdds":   round(rng.uniform(1.6, 2.4), 2),
                "boostedOdds":  round(rng.uniform(2.8, 4.5), 2),
                "bookmaker":    rng.choice(["Bet365", "Betfair", "Codere", "Betway"]),
            })
    return boosts

@app.get("/api/perfect_parlay")
def get_perfect_parlay(db: Session = Depends(get_db)):
    if time.time() - _cache["parlay"]["time"] < CACHE_TTL and _cache["parlay"]["data"]:
        return _cache["parlay"]["data"]

    now = datetime.utcnow()
    seven_days = now + timedelta(days=7)
    upcoming = (
        db.query(Match)
        .filter(Match.date >= now, Match.date <= seven_days)
        .order_by(Match.date.asc())
        .limit(15)
        .all()
    )
    if not upcoming:
        return {"legs": [], "totalOdds": 1.0, "jointProbability": 100.0, "message": "No hay partidos disponibles"}

    PROB_THRESHOLD = 0.60
    all_candidates = []

    for match in upcoming:
        evaluated = _evaluate_match(match, db)
        for c in evaluated["allCandidates"]:
            if c["probability"] >= PROB_THRESHOLD and c["ev"] > 0:
                all_candidates.append({
                    "matchId":       match.id,
                    "homeTeam":      evaluated["homeTeam"],
                    "awayTeam":      evaluated["awayTeam"],
                    "date":          evaluated["date"],
                    "market":        c["market"],
                    "outcome":       c["outcome"],
                    "label":         c["label"],
                    "probability":   c["probability"],
                    "bookmakerOdds": c["bookmaker_odds"],
                    "fairOdds":      c["fair_odds"],
                    "ev":            c["ev"],
                })

    all_candidates.sort(key=lambda c: c["probability"] * c["ev"], reverse=True)

    selected: list[dict] = []
    used_matches: set[int] = set()
    for c in all_candidates:
        if c["matchId"] not in used_matches:
            selected.append(c)
            used_matches.add(c["matchId"])
        if len(selected) == 4:
            break

    if not selected:
        return {"legs": [], "totalOdds": 1.0, "jointProbability": 0.0, "message": "No hay selecciones con suficiente confianza"}

    from functools import reduce
    total_odds = round(float(reduce(lambda a, b: a * b, [c["bookmakerOdds"] for c in selected])), 2)
    joint_prob = round(float(reduce(lambda a, b: a * b, [c["probability"] for c in selected])) * 100, 2)

    res = {
        "legs":              selected,
        "totalOdds":         total_odds,
        "jointProbability":  joint_prob,
        "markets_used":      list({c["market"] for c in selected}),
        "message":           f"Combinada de {len(selected)} selecciones | Cuota total: {total_odds}",
    }
    _cache["parlay"]["time"] = time.time()
    _cache["parlay"]["data"] = res
    return res

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
