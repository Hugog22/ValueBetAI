"""
cache_service.py
----------------
Centralized in-RAM cache for pre-computed predictions — MULTI-SPORT edition.

Structure:
    _cache["sports"][sport_key]["jornada"] → list of evaluated matches
    _cache["sports"][sport_key]["parlay"]  → dict (CombinAIA for that sport)
    _cache["all_parlays"]                  → list of all non-empty parlays
    _cache["last_updated"]                 → epoch float

Backward-compatible aliases:
    get_cache()["jornada"] → _cache["sports"]["laliga"]["jornada"]
    get_cache()["parlay"]  → _cache["sports"]["laliga"]["parlay"]
"""

import logging
import time
from datetime import datetime, timedelta
from functools import reduce

logger = logging.getLogger(__name__)

SUPPORTED_SPORTS = ["laliga", "premier", "champions", "nba"]

# ---------------------------------------------------------------------------
# Global in-RAM cache
# ---------------------------------------------------------------------------
_cache: dict = {
    "sports": {s: {"jornada": [], "parlay": {}} for s in SUPPORTED_SPORTS},
    "all_parlays":  [],
    "boosts":       [],
    "last_updated": 0.0,
}


def get_cache() -> dict:
    """Return the current cache snapshot with backward-compat aliases."""
    _cache["jornada"] = _cache["sports"]["laliga"]["jornada"]
    _cache["parlay"]  = _cache["sports"]["laliga"]["parlay"]
    return _cache


def is_cache_warm() -> bool:
    return _cache["last_updated"] > 0.0


# ---------------------------------------------------------------------------
# Parlay builder (shared for any sport's candidate list)
# ---------------------------------------------------------------------------

def _build_parlay(jornada: list[dict]) -> dict:
    PROB_THRESHOLD = 0.60
    all_candidates = []
    for evaluated in jornada:
        for c in evaluated.get("allCandidates", []):
            if c.get("probability", 0) >= PROB_THRESHOLD and c.get("ev", 0) > 0:
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
    used_matches: set = set()
    for c in all_candidates:
        if c["matchId"] not in used_matches:
            selected.append(c)
            used_matches.add(c["matchId"])
        if len(selected) == 4:
            break

    if selected:
        total_odds = round(float(reduce(lambda a, b: a * b, [c["bookmakerOdds"] for c in selected])), 2)
        joint_prob = round(float(reduce(lambda a, b: a * b, [c["probability"] for c in selected])) * 100, 2)
        return {
            "legs":             selected,
            "totalOdds":        total_odds,
            "jointProbability": joint_prob,
            "markets_used":     list({c["market"] for c in selected}),
            "message":          f"Combinada de {len(selected)} selecciones | Cuota total: {total_odds}",
        }
    return {"legs": [], "totalOdds": 1.0, "jointProbability": 0.0,
            "message": "No hay selecciones con suficiente confianza"}


# ---------------------------------------------------------------------------
# Per-sport refresh
# ---------------------------------------------------------------------------

def _refresh_sport(sport_key: str, db, predictor, nba_predictor) -> list[dict]:
    """Evaluate all upcoming matches for a given sport and return jornada list."""
    from db.models import Match, Team
    from core.match_evaluator import _evaluate_match as _eval_football, _evaluate_match_nba
    from etl.multi_sport_etl import SPORT_TYPE

    sport_type = SPORT_TYPE.get(sport_key, "football")

    now = datetime.utcnow()
    upcoming = (
        db.query(Match)
        .filter(Match.date >= now, Match.date <= now + timedelta(days=7))
        .order_by(Match.date.asc())
        .limit(20)
        .all()
    )

    # For LaLiga we already have all matches; for other sports we need to tag
    # by team names present in the DB from multi_sport_etl. A simple heuristic:
    # filter by teams that appear in upcoming events recently synced.
    # Since all sports share the same matches table, we can't distinguish by sport
    # easily without adding a `sport_key` column to matches. For now, we tag by
    # checking which matches were created vs already existing from Understat.
    # TODO: Add sport_key column to Match model for clean separation.

    jornada = []
    for m in upcoming:
        try:
            if sport_type == "basketball":
                jornada.append(_evaluate_match_nba(m, nba_predictor, db))
            else:
                jornada.append(_eval_football(m, predictor, db))
        except Exception as e:
            logger.warning(f"⚠️  [cache] Skipping match {m.id} ({sport_key}): {e}")

    return jornada


# ---------------------------------------------------------------------------
# Full cache refresh
# ---------------------------------------------------------------------------

def refresh_cache() -> None:
    """
    Run the full multi-sport prediction pipeline and update the in-RAM cache.
    """
    logger.info("🔄 [cache_service] Starting multi-sport cache refresh...")
    t0 = time.time()

    try:
        from db.session import SessionLocal
        from db.models import Match
        from core.shared_predictor import predictor, nba_predictor
        from core.match_evaluator import _evaluate_match as _evaluate_match_core

        # ── 1. Refresh La Liga odds from The Odds API ──────────────────────
        try:
            from scripts.flush_odds import flush_and_reload
            flush_and_reload()
            logger.info("✅ [cache] LaLiga odds refreshed.")
        except Exception as e:
            logger.warning(f"⚠️  [cache] LaLiga odds refresh failed: {e}")

        # ── 2. Sync other sports from The Odds API ─────────────────────────
        try:
            from etl.multi_sport_etl import sync_all_sports
            sync_results = sync_all_sports()
            logger.info(f"✅ [cache] Multi-sport sync: {sync_results}")
        except Exception as e:
            logger.warning(f"⚠️  [cache] Multi-sport sync failed: {e}")

        # ── 3. Evaluate upcoming matches per sport ─────────────────────────
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            seven_days = now + timedelta(days=7)
            upcoming = (
                db.query(Match)
                .filter(Match.date >= now, Match.date <= seven_days)
                .order_by(Match.date.asc())
                .limit(60)
                .all()
            )

            if not upcoming:
                logger.warning("⚠️  [cache] No upcoming matches found — keeping stale cache.")
                return

            # Evaluate all matches (football evaluator for all for now;
            # NBA matches will need sport tagging in future iteration)
            jornada_all: list[dict] = []
            for m in upcoming:
                try:
                    jornada_all.append(_evaluate_match_core(m, predictor, db))
                except Exception as e:
                    logger.warning(f"⚠️  [cache] Skipping match {m.id}: {e}")

            # Tag matches per sport by checking team names (interim approach)
            # LaLiga teams are seeded by Understat; others by multi_sport_etl
            # We use heuristic: check home_team name against known league teams
            laliga_teams = _get_laliga_team_names(db)
            premier_teams = _get_premier_team_names()
            champions_teams = _get_champions_team_names()

            for sport_key, team_set in [
                ("laliga", laliga_teams),
                ("premier", premier_teams),
                ("champions", champions_teams),
            ]:
                sport_jornada = [
                    m for m in jornada_all
                    if m["homeTeam"] in team_set or m["awayTeam"] in team_set
                ] if team_set else (jornada_all if sport_key == "laliga" else [])

                parlay = _build_parlay(sport_jornada)
                _cache["sports"][sport_key]["jornada"] = sport_jornada
                _cache["sports"][sport_key]["parlay"]  = parlay

            # NBA — evaluate separately (placeholder until NBA model is trained)
            _cache["sports"]["nba"]["jornada"] = []
            _cache["sports"]["nba"]["parlay"]  = {"legs": [], "totalOdds": 1.0,
                                                   "jointProbability": 0.0,
                                                   "message": "NBA próximamente"}

        finally:
            db.close()

        # ── 4. Build "all_parlays" list ────────────────────────────────────
        all_parlays = []
        sport_labels = {
            "laliga":    {"label": "La Liga", "flag": "🇪🇸"},
            "premier":   {"label": "Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
            "champions": {"label": "Champions League", "flag": "🏆"},
            "nba":       {"label": "NBA", "flag": "🏀"},
        }
        for sk in SUPPORTED_SPORTS:
            parlay = _cache["sports"][sk]["parlay"]
            if parlay.get("legs"):
                all_parlays.append({
                    "sport": sk,
                    **sport_labels.get(sk, {"label": sk, "flag": ""}),
                    **parlay,
                })

        _cache["all_parlays"]  = all_parlays
        _cache["boosts"]       = []
        _cache["last_updated"] = time.time()

        elapsed = round(time.time() - t0, 2)
        logger.info(
            f"✅ [cache] Multi-sport refresh complete in {elapsed}s — "
            f"{sum(len(_cache['sports'][s]['jornada']) for s in SUPPORTED_SPORTS)} total matches, "
            f"{len(all_parlays)} CombinAIas."
        )

    except Exception as e:
        logger.error(f"❌ [cache] Refresh failed: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Team name helpers (interim sport detection without DB sport_key column)
# ---------------------------------------------------------------------------

def _get_laliga_team_names(db) -> set[str]:
    """Return team names that were seeded from Understat (La Liga source)."""
    from db.models import Team
    # All teams in DB that were added by the Understat ETL — best approximation:
    # La Liga teams are the oldest in the DB (lowest IDs)
    teams = db.query(Team).order_by(Team.id.asc()).limit(40).all()
    return {t.name for t in teams}


def _get_premier_team_names() -> set[str]:
    """Known Premier League teams for sport detection."""
    return {
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
        "Burnley", "Chelsea", "Crystal Palace", "Everton", "Fulham",
        "Liverpool", "Leeds United", "Leicester City", "Manchester City",
        "Manchester United", "Newcastle United", "Nottingham Forest",
        "Sheffield United", "Tottenham Hotspur", "West Ham United",
        "Wolverhampton Wanderers", "Luton Town", "Ipswich Town", "Southampton",
    }


def _get_champions_team_names() -> set[str]:
    """Known Champions League participants (approximate — top clubs)."""
    return {
        "Real Madrid", "Barcelona", "Bayern Munich", "Manchester City",
        "Paris Saint-Germain", "Liverpool", "Chelsea", "Juventus",
        "Inter Milan", "AC Milan", "Borussia Dortmund", "Atletico Madrid",
        "Porto", "Benfica", "Ajax", "Napoli", "RB Leipzig", "Villarreal",
        "Sporting CP", "Red Bull Salzburg", "Celtic", "Rangers",
        "Shakhtar Donetsk", "Club Brugge", "Sevilla", "Feyenoord",
        "Bayer Leverkusen", "Lazio", "Real Sociedad", "Brest", "Atalanta",
    }
