"""
cache_service.py
----------------
Centralized in-RAM cache for pre-computed predictions.

This module is the single source of truth for the jornada, parlay, and
super-boosts data. Endpoints read from here (< 1ms); the scheduler refreshes
the cache in the background so no user request ever triggers heavy computation.

Usage:
    from core.cache_service import get_cache, refresh_cache

    # In an endpoint (fast path — just read RAM):
    data = get_cache()
    return data["jornada"]

    # In the scheduler job:
    refresh_cache()
"""

import logging
import time
import random
from datetime import datetime, timedelta
from functools import reduce

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global in-RAM cache
# ---------------------------------------------------------------------------
_cache: dict = {
    "jornada":      [],      # list[dict] — pre-evaluated matches
    "parlay":       {},      # dict — perfect parlay
    "boosts":       [],      # list[dict] — super boosts
    "last_updated": 0.0,     # epoch float — when the cache was last refreshed
}


def get_cache() -> dict:
    """Return the current cache snapshot (never None)."""
    return _cache


def is_cache_warm() -> bool:
    """Return True if the cache has been populated at least once."""
    return _cache["last_updated"] > 0.0


# ---------------------------------------------------------------------------
# Heavy computation — called ONLY by the scheduler (or once at startup)
# ---------------------------------------------------------------------------

def refresh_cache() -> None:
    """
    Run the full prediction pipeline and update the in-RAM cache.

    This function:
    1. Queries upcoming matches from the database.
    2. Calls flush_and_reload() to pull fresh odds from The Odds API.
    3. Runs _evaluate_match() on every upcoming match.
    4. Builds the perfect-parlay selection.
    5. Builds super-boosts.
    6. Atomically swaps the global cache.
    """
    logger.info("🔄 [cache_service] Starting background cache refresh...")
    t0 = time.time()

    try:
        # Import here to avoid circular imports at module load time
        from db.session import SessionLocal
        from db.models import Match
        from core.shared_predictor import predictor
        from core.match_evaluator import _evaluate_match as _evaluate_match_core

        # ---- 1. Refresh odds from The Odds API first ----
        try:
            from scripts.flush_odds import flush_and_reload
            flush_and_reload()
            logger.info("✅ [cache_service] Odds refreshed from The Odds API.")
        except Exception as e:
            logger.warning(f"⚠️  [cache_service] Odds refresh failed (using stale DB odds): {e}")

        # ---- 2. Query upcoming matches ----
        db = SessionLocal()
        try:
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
                logger.warning("⚠️  [cache_service] No upcoming matches found — keeping stale cache.")
                return

            # ---- 3. Evaluate every match ----
            jornada: list[dict] = []
            for m in upcoming:
                try:
                    jornada.append(_evaluate_match_core(m, predictor, db))
                except Exception as e:
                    logger.warning(f"⚠️  [cache_service] Skipping match {m.id}: {e}")

            # ---- 4. Build perfect parlay ----
            PROB_THRESHOLD = 0.60
            all_candidates = []
            for evaluated in jornada:
                for c in evaluated.get("allCandidates", []):
                    if c["probability"] >= PROB_THRESHOLD and c["ev"] > 0:
                        all_candidates.append({
                            "matchId":       evaluated["id"],
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

            if selected:
                total_odds = round(float(reduce(lambda a, b: a * b, [c["bookmakerOdds"] for c in selected])), 2)
                joint_prob = round(float(reduce(lambda a, b: a * b, [c["probability"] for c in selected])) * 100, 2)
                parlay = {
                    "legs":             selected,
                    "totalOdds":        total_odds,
                    "jointProbability": joint_prob,
                    "markets_used":     list({c["market"] for c in selected}),
                    "message":          f"Combinada de {len(selected)} selecciones | Cuota total: {total_odds}",
                }
            else:
                parlay = {
                    "legs": [], "totalOdds": 1.0, "jointProbability": 0.0,
                    "message": "No hay selecciones con suficiente confianza",
                }

            # ---- 5. Build super-boosts ----
            boosts: list[dict] = []
            for m in upcoming:
                try:
                    rng = random.Random(m.id + 9999)
                    if rng.random() < 0.4:
                        boosts.append({
                            "match":       f"{m.home_team.name} vs {m.away_team.name}",
                            "date":        m.date.isoformat() + "Z" if m.date else None,
                            "market":      rng.choice(["Victoria Local", "Ambos Equipos Marcan", "Más de 2.5 Goles"]),
                            "normalOdds":  round(rng.uniform(1.6, 2.4), 2),
                            "boostedOdds": round(rng.uniform(2.8, 4.5), 2),
                            "bookmaker":   rng.choice(["Bet365", "Betfair", "Codere", "Betway"]),
                        })
                except Exception as e:
                    logger.warning(f"⚠️  [cache_service] Skipping boost for match {m.id}: {e}")

        finally:
            db.close()

        # ---- 6. Atomic cache swap ----
        _cache["jornada"]      = jornada
        _cache["parlay"]       = parlay
        _cache["boosts"]       = boosts
        _cache["last_updated"] = time.time()

        elapsed = round(time.time() - t0, 2)
        logger.info(
            f"✅ [cache_service] Cache refreshed in {elapsed}s — "
            f"{len(jornada)} matches, {len(selected if selected else [])} parlay legs, "
            f"{len(boosts)} boosts."
        )

    except Exception as e:
        logger.error(f"❌ [cache_service] Cache refresh failed: {e}", exc_info=True)
