"""
cache_service.py
----------------
Centralized in-RAM cache for pre-computed football predictions.

Structure:
    _cache["sports"][sport_key]["jornada"] → list of evaluated matches
    _cache["sports"][sport_key]["parlay"]  → dict (CombinAIA for that sport)
    _cache["all_parlays"]                  → list of all non-empty parlays
    _cache["last_updated"]                 → epoch float

Backward-compatible aliases (LaLiga default):
    get_cache()["jornada"] → _cache["sports"]["laliga"]["jornada"]
    get_cache()["parlay"]  → _cache["sports"]["laliga"]["parlay"]

Supported sports: La Liga, Premier League, Champions League.
"""

import logging
import time
from datetime import datetime, timedelta
from functools import reduce

logger = logging.getLogger(__name__)

SUPPORTED_SPORTS = ["laliga", "premier", "champions"]

# Sport display metadata
_SPORT_META = {
    "laliga":    {"label": "La Liga",          "flag": "🇪🇸"},
    "premier":   {"label": "Premier League",   "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "champions": {"label": "Champions League", "flag": "🏆"},
}


# ---------------------------------------------------------------------------
# Global in-RAM cache
# ---------------------------------------------------------------------------

_cache: dict = {
    "sports":       {s: {"jornada": [], "parlay": {}} for s in SUPPORTED_SPORTS},
    "all_parlays":  [],
    "boosts":       [],
    "last_updated": 0.0,
}


def get_cache() -> dict:
    """Return the current cache snapshot with backward-compat aliases for LaLiga."""
    _cache["jornada"] = _cache["sports"]["laliga"]["jornada"]
    _cache["parlay"]  = _cache["sports"]["laliga"]["parlay"]
    return _cache


def is_cache_warm() -> bool:
    return _cache["last_updated"] > 0.0


# ---------------------------------------------------------------------------
# Parlay builder
# ---------------------------------------------------------------------------

def _build_parlay(jornada: list[dict]) -> dict:
    """
    Build the best CombinAIA (multi-leg parlay) from a sport's match list.

    Selection criteria:
      - AI probability >= 60 %
      - Positive Expected Value
      - At most one leg per match
      - Maximum 4 legs total
    """
    PROB_THRESHOLD = 0.60
    candidates = []

    for match in jornada:
        for c in match.get("allCandidates", []):
            if c.get("probability", 0) >= PROB_THRESHOLD and c.get("ev", 0) > 0:
                candidates.append({
                    "matchId":       match["id"],
                    "homeTeam":      match["homeTeam"],
                    "awayTeam":      match["awayTeam"],
                    "date":          match["date"],
                    "market":        c["market"],
                    "outcome":       c["outcome"],
                    "label":         c["label"],
                    "probability":   c["probability"],
                    "bookmakerOdds": c["bookmaker_odds"],
                    "fairOdds":      c["fair_odds"],
                    "ev":            c["ev"],
                })

    # Rank by combined probability × EV score
    candidates.sort(key=lambda c: c["probability"] * c["ev"], reverse=True)

    selected: list[dict] = []
    used_matches: set    = set()
    for c in candidates:
        if c["matchId"] not in used_matches:
            selected.append(c)
            used_matches.add(c["matchId"])
        if len(selected) == 4:
            break

    if selected:
        total_odds = round(float(reduce(lambda a, b: a * b, [c["bookmakerOdds"] for c in selected])), 2)
        joint_prob = round(float(reduce(lambda a, b: a * b, [c["probability"]   for c in selected])) * 100, 2)
        return {
            "legs":             selected,
            "totalOdds":        total_odds,
            "jointProbability": joint_prob,
            "markets_used":     list({c["market"] for c in selected}),
            "message":          f"Combinada de {len(selected)} selecciones | Cuota total: {total_odds}",
        }

    return {
        "legs":             [],
        "totalOdds":        1.0,
        "jointProbability": 0.0,
        "message":          "No hay selecciones con suficiente confianza",
    }


# ---------------------------------------------------------------------------
# Team name helpers — interim sport detection without a sport_key DB column
# ---------------------------------------------------------------------------

def _get_laliga_team_names(db) -> set[str]:
    """Return team names seeded from Understat (La Liga source)."""
    from db.models import Team
    teams = db.query(Team).order_by(Team.id.asc()).limit(40).all()
    return {t.name for t in teams}


def _get_premier_team_names() -> set[str]:
    """Known Premier League team names for sport detection."""
    return {
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
        "Burnley", "Chelsea", "Crystal Palace", "Everton", "Fulham",
        "Liverpool", "Leeds United", "Leicester City", "Manchester City",
        "Manchester United", "Newcastle United", "Nottingham Forest",
        "Sheffield United", "Tottenham Hotspur", "West Ham United",
        "Wolverhampton Wanderers", "Luton Town", "Ipswich Town", "Southampton",
    }


def _get_champions_team_names() -> set[str]:
    """Known Champions League participant names for sport detection."""
    return {
        "Real Madrid", "Barcelona", "Bayern Munich", "Manchester City",
        "Paris Saint-Germain", "Liverpool", "Chelsea", "Juventus",
        "Inter Milan", "AC Milan", "Borussia Dortmund", "Atletico Madrid",
        "Porto", "Benfica", "Ajax", "Napoli", "RB Leipzig", "Villarreal",
        "Sporting CP", "Red Bull Salzburg", "Celtic", "Rangers",
        "Shakhtar Donetsk", "Club Brugge", "Sevilla", "Feyenoord",
        "Bayer Leverkusen", "Lazio", "Real Sociedad", "Brest", "Atalanta",
    }


# ---------------------------------------------------------------------------
# Full cache refresh
# ---------------------------------------------------------------------------

def refresh_cache() -> None:
    """
    Run the full multi-sport football prediction pipeline and update the
    in-RAM cache.

    Steps:
      1. Refresh La Liga odds via flush_odds (The Odds API).
      2. Sync Premier League and Champions League via multi_sport_etl.
      3. Evaluate all upcoming matches with the football predictor.
      4. Tag matches per sport by team name heuristic.
      5. Build CombinAIas (parlays) per sport and the all_parlays list.
    """
    logger.info("🔄 [cache_service] Starting multi-sport cache refresh...")
    t0 = time.time()

    try:
        from db.session import SessionLocal
        from db.models import Match
        from core.shared_predictor import predictor
        from core.match_evaluator import _evaluate_match

        # ── Step 1: Refresh La Liga odds ──────────────────────────────────
        try:
            from scripts.flush_odds import flush_and_reload
            flush_and_reload()
            logger.info("✅ [cache] LaLiga odds refreshed.")
        except Exception as e:
            logger.warning(f"⚠️  [cache] LaLiga odds refresh failed: {e}")

        # ── Step 2: Sync Premier League and Champions League ──────────────
        try:
            from etl.multi_sport_etl import sync_all_sports
            sync_results = sync_all_sports()
            logger.info(f"✅ [cache] Multi-sport sync: {sync_results}")
        except Exception as e:
            logger.warning(f"⚠️  [cache] Multi-sport sync failed: {e}")

        # ── Step 3: Evaluate all upcoming matches ─────────────────────────
        db = SessionLocal()
        try:
            now       = datetime.utcnow()
            seven_days = now + timedelta(days=7)
            upcoming  = (
                db.query(Match)
                .filter(Match.date >= now, Match.date <= seven_days)
                .order_by(Match.date.asc())
                .limit(60)
                .all()
            )

            if not upcoming:
                logger.warning("⚠️  [cache] No upcoming matches found — keeping stale cache.")
                return

            jornada_all: list[dict] = []
            for m in upcoming:
                try:
                    jornada_all.append(_evaluate_match(m, predictor, db))
                except Exception as e:
                    logger.warning(f"⚠️  [cache] Skipping match {m.id}: {e}")

            # ── Step 4: Tag matches per sport ─────────────────────────────
            laliga_teams    = _get_laliga_team_names(db)
            premier_teams   = _get_premier_team_names()
            champions_teams = _get_champions_team_names()

            for sport_key, team_set in [
                ("laliga",    laliga_teams),
                ("premier",   premier_teams),
                ("champions", champions_teams),
            ]:
                sport_jornada = (
                    [m for m in jornada_all if m["homeTeam"] in team_set or m["awayTeam"] in team_set]
                    if team_set
                    else (jornada_all if sport_key == "laliga" else [])
                )
                _cache["sports"][sport_key]["jornada"] = sport_jornada
                _cache["sports"][sport_key]["parlay"]  = _build_parlay(sport_jornada)

        finally:
            db.close()

        # ── Step 5: Build the all_parlays list ────────────────────────────
        all_parlays = []
        for sk in SUPPORTED_SPORTS:
            parlay = _cache["sports"][sk]["parlay"]
            if parlay.get("legs"):
                all_parlays.append({
                    "sport": sk,
                    **_SPORT_META.get(sk, {"label": sk, "flag": ""}),
                    **parlay,
                })

        _cache["all_parlays"]  = all_parlays
        _cache["boosts"]       = []
        _cache["last_updated"] = time.time()

        elapsed      = round(time.time() - t0, 2)
        total_matches = sum(len(_cache["sports"][s]["jornada"]) for s in SUPPORTED_SPORTS)
        logger.info(
            f"✅ [cache] Refresh complete in {elapsed}s — "
            f"{total_matches} total matches, {len(all_parlays)} CombinAIas."
        )

    except Exception as e:
        logger.error(f"❌ [cache] Refresh failed: {e}", exc_info=True)
