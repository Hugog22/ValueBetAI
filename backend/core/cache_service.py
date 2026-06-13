"""
cache_service.py
----------------
Centralized in-RAM cache for pre-computed football predictions.

Architecture (v2 — Atomic Swap):
    All data is built into a LOCAL dict during refresh, then swapped
    atomically into the global `_cache` reference.  This eliminates the
    "0 matches" window that occurred when the old cache was mutated
    in-place during a long-running refresh.

Structure:
    _cache["sports"][sport_key]["jornada"] → list of evaluated matches
    _cache["sports"][sport_key]["parlay"]  → dict (CombinAIA for that sport)
    _cache["sports"][sport_key]["is_off_season"] → bool
    _cache["all_parlays"]                  → list of all non-empty parlays
    _cache["last_updated"]                 → epoch float

Backward-compatible aliases (LaLiga default):
    get_cache()["jornada"] → _cache["sports"]["laliga"]["jornada"]
    get_cache()["parlay"]  → _cache["sports"]["laliga"]["parlay"]

Supported sports: La Liga, Premier League, Champions League, World Cup 2026.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from functools import reduce

logger = logging.getLogger(__name__)

SUPPORTED_SPORTS = ["laliga", "premier", "champions", "worldcup"]

# Sport display metadata
_SPORT_META = {
    "laliga":    {"label": "La Liga",          "flag": "🇪🇸"},
    "premier":   {"label": "Premier League",   "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "champions": {"label": "Champions League", "flag": "🏆"},
    "worldcup":  {"label": "Mundial 2026",     "flag": "⚽"},
}

# Months when European leagues are off-season (June–July).
# World Cup runs in summer so it's never marked as off-season.
_OFF_SEASON_MONTHS = {6, 7}


# ---------------------------------------------------------------------------
# Global in-RAM cache + concurrency guard
# ---------------------------------------------------------------------------

def _empty_cache() -> dict:
    """Return a fresh, empty cache structure."""
    return {
        "sports": {
            s: {"jornada": [], "parlay": {}, "is_off_season": False}
            for s in SUPPORTED_SPORTS
        },
        "all_parlays":  [],
        "boosts":       [],
        "jornada":      [],   # backward-compat alias (LaLiga)
        "parlay":       {},   # backward-compat alias (LaLiga)
        "last_updated": 0.0,
    }

_cache: dict = _empty_cache()

# Prevent two refresh_cache() calls from running concurrently
# (e.g. a scheduled peak refresh + the hourly settle_and_refresh overlap).
_refresh_lock = threading.Lock()


def get_cache() -> dict:
    """Return the current cache snapshot (read-only reference)."""
    return _cache


def is_cache_warm() -> bool:
    return _cache["last_updated"] > 0.0


def get_sport_info(sport_key: str) -> dict:
    """Return sport metadata including off-season flag."""
    sport = _cache["sports"].get(sport_key, {"jornada": [], "parlay": {}, "is_off_season": False})
    meta  = _SPORT_META.get(sport_key, {"label": sport_key, "flag": ""})
    return {
        **meta,
        "match_count":    len(sport["jornada"]),
        "is_off_season":  sport["is_off_season"],
    }


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
# Team name helpers
# ---------------------------------------------------------------------------

def _get_laliga_team_names(db) -> set[str]:
    """Return team names seeded from Understat (La Liga source)."""
    from db.models import Team
    teams = db.query(Team).order_by(Team.id.asc()).all()
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


def _get_worldcup_team_names() -> set[str]:
    """Return all 48 FIFA World Cup 2026 national team names."""
    try:
        from etl.world_cup_etl import get_world_cup_team_names
        return get_world_cup_team_names()
    except Exception:
        return set()


def _is_off_season() -> bool:
    """True during June–July when European leagues are off."""
    return datetime.utcnow().month in _OFF_SEASON_MONTHS


# ---------------------------------------------------------------------------
# Full cache refresh  — ATOMIC SWAP (double-buffer pattern)
# ---------------------------------------------------------------------------

def refresh_cache() -> None:
    """
    Run the full multi-sport football prediction pipeline and update the
    in-RAM cache.

    Uses the double-buffer / atomic-swap pattern:
      1. All new data is built into a LOCAL `new_cache` dict.
      2. Only after ALL computation succeeds, the global `_cache` reference
         is swapped to the new dict in a single assignment (atomic under
         CPython's GIL).
      3. If anything fails, the old cache is kept intact — users never
         see 0 matches.

    Steps:
      1. Sync World Cup matches (The Odds API + football-data.org).
      2. Refresh La Liga odds via flush_odds (The Odds API).
      3. Sync Premier League and Champions League via multi_sport_etl.
      4. Evaluate all upcoming matches with the correct predictor.
      5. Tag matches per sport by team name heuristic.
      6. Mark European leagues as off-season when no upcoming matches found.
      7. Build CombinAIas (parlays) per sport and the all_parlays list.
      8. Atomic swap: _cache = new_cache.
    """
    # Prevent overlapping refreshes (scheduler can fire multiple jobs)
    if not _refresh_lock.acquire(blocking=False):
        logger.warning("⏳ [cache] Refresh already in progress — skipping this invocation.")
        return

    try:
        _do_refresh()
    finally:
        _refresh_lock.release()


def _do_refresh() -> None:
    """Inner refresh logic — called only while holding _refresh_lock."""
    global _cache

    logger.info("🔄 [cache_service] Starting multi-sport cache refresh…")
    t0 = time.time()

    try:
        from db.session import SessionLocal
        from db.models import Match, Bet, Odds
        from core.shared_predictor import predictor, world_cup_predictor
        from core.match_evaluator import _evaluate_match, _evaluate_world_cup_match
        from core.config import settings

        # ── Step 1: Sync World Cup matches ────────────────────────────────
        try:
            from etl.world_cup_etl import sync_world_cup_odds, sync_world_cup_schedule
            wc_new1 = sync_world_cup_odds()
            wc_new2 = sync_world_cup_schedule()
            logger.info(f"✅ [cache] World Cup sync: odds={wc_new1} new, schedule={wc_new2} new")
        except Exception as e:
            logger.warning(f"⚠️  [cache] World Cup sync failed: {e}")

        # ── Step 2: Refresh La Liga odds ──────────────────────────────────
        if settings.enable_club_leagues:
            try:
                from scripts.flush_odds import flush_and_reload
                flush_and_reload()
                logger.info("✅ [cache] LaLiga odds refreshed.")
            except Exception as e:
                logger.warning(f"⚠️  [cache] LaLiga odds refresh failed: {e}")
        else:
            logger.info("⏸  [cache] Skipping LaLiga odds (ENABLE_CLUB_LEAGUES=False)")

        # ── Step 3: Sync Premier League and Champions League ──────────────
        if settings.enable_club_leagues:
            try:
                from etl.multi_sport_etl import sync_all_sports
                sync_results = sync_all_sports()
                logger.info(f"✅ [cache] Multi-sport sync: {sync_results}")
            except Exception as e:
                logger.warning(f"⚠️  [cache] Multi-sport sync failed: {e}")
        else:
            logger.info("⏸  [cache] Skipping Multi-sport sync (ENABLE_CLUB_LEAGUES=False)")

        # ── Step 4: Evaluate all upcoming matches ─────────────────────────
        # Build everything into a NEW local cache dict.
        new_cache = _empty_cache()

        db = SessionLocal()
        try:
            now        = datetime.utcnow()
            seven_days = now + timedelta(days=7)  # 7-day horizon for stable odds
            upcoming   = (
                db.query(Match)
                .join(Odds, (Odds.match_id == Match.id) & (Odds.market == "h2h"))
                .filter(Match.date >= now, Match.date <= seven_days)
                .order_by(Match.date.asc())
                .distinct()
                .all()
            )

            wc_teams       = _get_worldcup_team_names()
            jornada_all:    list[dict] = []
            jornada_wc:     list[dict] = []

            for m in upcoming:
                try:
                    home_name = m.home_team.name
                    away_name = m.away_team.name

                    # Route to World Cup evaluator if both teams are national teams
                    if home_name in wc_teams or away_name in wc_teams:
                        result = _evaluate_world_cup_match(m, world_cup_predictor, db)
                        if result:
                            jornada_wc.append(result)
                    else:
                        result = _evaluate_match(m, predictor, db)
                        if result:
                            jornada_all.append(result)
                            
                    if not result:
                        continue
                        
                    # Auto-track the system's value bet recommendation
                    best_pick = result.get("bestPick")
                    if best_pick and best_pick.get("isValueBet"):
                        existing_sys_bet = db.query(Bet).filter(
                            Bet.user_id == None,
                            Bet.match_id == m.id,
                            Bet.market == best_pick["market"],
                            Bet.selection == best_pick["outcome"]
                        ).first()
                        
                        if not existing_sys_bet:
                            sys_bet = Bet(
                                user_id=None,
                                match_id=m.id,
                                bookmaker=result.get("oddsSource", "system"),
                                market=best_pick["market"],
                                selection=best_pick["outcome"],
                                odds_taken=best_pick["bookmakerOdds"],
                                stake=best_pick["stake"],
                                status="Pending"
                            )
                            db.add(sys_bet)
                            db.commit()
                            logger.info(f"🤖 [cache] Auto-tracked system bet: {m.id} -> {best_pick['market']} {best_pick['outcome']} @ {best_pick['bookmakerOdds']}")

                except Exception as e:
                    db.rollback()
                    logger.warning(f"⚠️  [cache] Skipping match {m.id}: {e}")

            # ── Step 5: Tag club matches per sport ────────────────────────
            laliga_teams    = _get_laliga_team_names(db) if settings.enable_club_leagues else set()
            premier_teams   = _get_premier_team_names() if settings.enable_club_leagues else set()
            champions_teams = _get_champions_team_names() if settings.enable_club_leagues else set()

            off_season_now  = _is_off_season() or not settings.enable_club_leagues

            for sport_key, team_set in [
                ("laliga",    laliga_teams),
                ("premier",   premier_teams),
                ("champions", champions_teams),
            ]:
                sport_jornada = (
                    [m for m in jornada_all if m["homeTeam"] in team_set or m["awayTeam"] in team_set]
                    if team_set
                    else []
                )
                is_off = len(sport_jornada) == 0 and off_season_now
                new_cache["sports"][sport_key]["jornada"]      = sport_jornada
                new_cache["sports"][sport_key]["parlay"]       = _build_parlay(sport_jornada)
                new_cache["sports"][sport_key]["is_off_season"] = is_off

            # World Cup always gets its own bucket
            new_cache["sports"]["worldcup"]["jornada"]       = jornada_wc
            new_cache["sports"]["worldcup"]["parlay"]        = _build_parlay(jornada_wc)
            new_cache["sports"]["worldcup"]["is_off_season"] = False  # WC is never "off-season"

        finally:
            db.close()

        # ── Step 6: Build the all_parlays list ────────────────────────────
        all_parlays = []
        for sk in SUPPORTED_SPORTS:
            parlay = new_cache["sports"][sk]["parlay"]
            if parlay.get("legs"):
                all_parlays.append({
                    "sport": sk,
                    **_SPORT_META.get(sk, {"label": sk, "flag": ""}),
                    **parlay,
                })

        new_cache["all_parlays"]  = all_parlays
        new_cache["boosts"]       = []
        new_cache["last_updated"] = time.time()

        # Backward-compat aliases baked into the dict (no mutation on read)
        new_cache["jornada"] = new_cache["sports"]["laliga"]["jornada"]
        new_cache["parlay"]  = new_cache["sports"]["laliga"]["parlay"]

        # ── Step 7: ATOMIC SWAP ───────────────────────────────────────────
        # Single reference assignment is atomic under CPython's GIL.
        # Readers that already grabbed the old _cache keep a valid snapshot;
        # new readers immediately see the fresh data.
        _cache = new_cache

        elapsed       = round(time.time() - t0, 2)
        total_matches = sum(len(new_cache["sports"][s]["jornada"]) for s in SUPPORTED_SPORTS)
        logger.info(
            f"✅ [cache] Refresh complete in {elapsed}s — "
            f"{total_matches} total matches, {len(all_parlays)} CombinAIas."
        )

    except Exception as e:
        logger.error(f"❌ [cache] Refresh failed: {e}", exc_info=True)
        # On failure, _cache is NOT touched — old data stays live.
