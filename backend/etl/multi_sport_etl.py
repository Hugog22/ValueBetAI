"""
multi_sport_etl.py
------------------
ETL pipeline for non-Understat sports (Premier, Champions, NBA).

For each sport, this module:
1. Fetches upcoming events from The Odds API (home_team, away_team, commence_time).
2. Upserts Team + Match rows in the database so the evaluator can reference them.
3. Stores odds in the Odds table for EV calculation.

This complements the Understat ETL (run_etl.py) which handles La Liga natively.
"""

import logging
import unicodedata
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Mapping: our internal sport key → The Odds API sport key
SPORT_ODDS_KEY = {
    "premier":   "soccer_england_premier_league",
    "champions": "soccer_uefa_champions_league",
    "nba":       "basketball_nba",
}

# Mapping: sport key → sport type
SPORT_TYPE = {
    "laliga":    "football",
    "premier":   "football",
    "champions": "football",
    "nba":       "basketball",
}


def _normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_name.lower().strip()


def sync_sport_matches(sport_key: str) -> int:
    """
    Download upcoming matches from The Odds API for a given sport and sync
    them into the database. Returns number of new matches inserted.

    Parameters
    ----------
    sport_key : "premier" | "champions" | "nba"
    """
    if sport_key not in SPORT_ODDS_KEY:
        logger.warning(f"[multi_sport_etl] Unknown sport_key: {sport_key}")
        return 0

    odds_key = SPORT_ODDS_KEY[sport_key]

    from db.session import SessionLocal
    from db.models import Team, Match, Odds
    from core.config import settings
    import httpx

    db = SessionLocal()
    new_count = 0

    try:
        # ── Fetch from The Odds API ────────────────────────────────────────
        url = f"https://api.the-odds-api.com/v4/sports/{odds_key}/odds"
        params = {
            "apiKey":     settings.ODDS_API_KEY,
            "regions":    "eu,uk",
            "markets":    "h2h",
            "oddsFormat": "decimal",
            "bookmakers": "pinnacle,bet365,williamhill,betway",
        }
        resp = httpx.get(url, params=params, timeout=30)

        if resp.status_code == 422:
            logger.warning(f"[multi_sport_etl] {sport_key}: 422 from Odds API (market not available on free tier)")
            return 0
        resp.raise_for_status()
        events = resp.json()

        logger.info(f"[multi_sport_etl] {sport_key}: {len(events)} events from The Odds API")

        all_teams = db.query(Team).all()
        team_by_norm = {_normalize(t.name): t for t in all_teams}

        for event in events:
            home_name = event.get("home_team", "")
            away_name = event.get("away_team", "")
            commence  = event.get("commence_time", "")

            if not home_name or not away_name or not commence:
                continue

            # Parse date
            try:
                match_date = datetime.strptime(commence[:19], "%Y-%m-%dT%H:%M:%S")
            except (ValueError, TypeError):
                match_date = datetime.utcnow() + timedelta(days=1)

            # Skip if already in the past
            if match_date < datetime.utcnow():
                continue

            # ── Upsert teams ───────────────────────────────────────────────
            def get_or_create_team(name: str) -> Team:
                norm = _normalize(name)
                if norm in team_by_norm:
                    return team_by_norm[norm]
                t = Team(name=name)
                db.add(t)
                db.flush()
                team_by_norm[norm] = t
                return t

            home_team = get_or_create_team(home_name)
            away_team = get_or_create_team(away_name)

            # ── Upsert match ───────────────────────────────────────────────
            existing = (
                db.query(Match)
                .filter(
                    Match.home_team_id == home_team.id,
                    Match.away_team_id == away_team.id,
                    Match.date >= match_date - timedelta(hours=3),
                    Match.date <= match_date + timedelta(hours=3),
                )
                .first()
            )

            if existing:
                # Update status if needed
                if existing.status == "Finished":
                    existing.status = "Not Started"
                match = existing
            else:
                match = Match(
                    date=match_date,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    status="Not Started",
                )
                db.add(match)
                db.flush()
                new_count += 1

            # ── Store h2h odds ─────────────────────────────────────────────
            bookmakers = event.get("bookmakers", [])
            from etl.odds_api import pick_best_bookmaker
            bm_key, bookmaker = pick_best_bookmaker(bookmakers)
            if bookmaker:
                for mkt in bookmaker.get("markets", []):
                    if mkt["key"] != "h2h":
                        continue
                    outcomes = mkt.get("outcomes", [])
                    ho = dr = aw = 0.0
                    for o in outcomes:
                        nm = o["name"].strip().lower()
                        if nm == "draw":
                            dr = float(o["price"])
                        elif _normalize(o["name"]) in _normalize(home_name) or _normalize(home_name) in _normalize(o["name"]):
                            ho = float(o["price"])
                        else:
                            aw = float(o["price"])
                    if ho and aw:
                        existing_odds = (
                            db.query(Odds)
                            .filter(Odds.match_id == match.id, Odds.market == "h2h", Odds.bookmaker == bm_key)
                            .first()
                        )
                        if existing_odds:
                            existing_odds.home_odds = ho
                            existing_odds.draw_odds = dr
                            existing_odds.away_odds = aw
                            existing_odds.timestamp = datetime.utcnow()
                        else:
                            db.add(Odds(
                                match_id=match.id,
                                bookmaker=bm_key,
                                market="h2h",
                                home_odds=ho,
                                draw_odds=dr,
                                away_odds=aw,
                                timestamp=datetime.utcnow(),
                            ))

        db.commit()
        logger.info(f"[multi_sport_etl] {sport_key}: {new_count} new matches inserted.")

    except Exception as e:
        logger.error(f"[multi_sport_etl] {sport_key} failed: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()

    return new_count


def sync_all_sports() -> dict:
    """Sync matches for all non-Understat sports. Returns {sport_key: new_matches}."""
    results = {}
    for sport_key in SPORT_ODDS_KEY:
        results[sport_key] = sync_sport_matches(sport_key)
    return results
