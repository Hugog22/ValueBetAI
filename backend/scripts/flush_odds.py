"""
flush_odds.py
-------------
Clears all existing odds from the database and re-downloads fresh odds
for the current La Liga matches using a bookmaker priority fallback:
  bet365 → pinnacle → williamhill → bwin → unibet → betfair → first available

Run from backend/:
    ./venv/bin/python -m scripts.flush_odds
"""

import sys
import os
import logging
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from db.session import engine, SessionLocal
from db.models import Odds, OddsHistory, Match, Team, Base
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Name normalization helpers
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    """
    Strips accents, lowercases, removes common Spanish football prefixes.
    'Atlético Madrid' → 'atletico madrid', 'CA Osasuna' → 'osasuna'
    """
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    lower = ascii_name.lower().strip()
    for prefix in ["ca ", "cf ", "sd ", "ud ", "rcd ", "rc ", "fc ", "ssc ", "ac ", "as "]:
        if lower.startswith(prefix):
            lower = lower[len(prefix):]
            break
    return lower


def _name_matches(outcome_name: str, *candidates: str) -> bool:
    """
    Returns True if outcome_name fuzzy-matches ANY candidate (normalized token overlap).
    Core fix: we NEVER rely on index order when assigning home/draw/away.
    """
    norm_o = _normalize(outcome_name)
    
    aliases = {
        "athletic bilbao": "athletic club",
        "celta vigo": "celta",
        "betis": "real betis",
    }
    for k, v in aliases.items():
        if k in norm_o:
            norm_o = norm_o.replace(k, v)
            
    o_tokens = set(norm_o.split()) - {"de", "la", "el", "los", "las"}
    
    for c in candidates:
        if not c:
            continue
        norm_c = _normalize(c)
        c_tokens = set(norm_c.split()) - {"de", "la", "el", "los", "las"}
        
        overlap = o_tokens & c_tokens
        
        if overlap == {"real"} or overlap == {"club"}:
            continue
            
        if len(overlap) > 0:
            return True
            
    return False


def _find_team(api_name: str, all_teams: list):
    """
    Best-effort match of an API team name to a DB Team object.
    Returns Team or None.
    """
    norm_api = _normalize(api_name)
    api_tokens = set(norm_api.split())
    best_team, best_score = None, 0
    for team in all_teams:
        db_tokens = set(_normalize(team.name).split())
        overlap = len(api_tokens & db_tokens)
        if overlap > best_score:
            best_score = overlap
            best_team = team
    return best_team if best_score >= 1 else None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def flush_and_reload():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Step 1: No longer deleting odds! We are tracking historical movements now.
        # We will just append to OddsHistory.
        
        logger.info(f"Skipping stale odds deletion to build OddsHistory.")

        # Step 2: Fetch odds (all bookmakers, eu+uk regions)
        from etl.odds_api import get_laliga_odds_all_markets, pick_best_bookmaker
        logger.info("Fetching odds from The Odds API (regions=eu,uk, all bookmakers)…")
        odds_data = get_laliga_odds_all_markets()
        logger.info(f"Received data for {len(odds_data)} events from the API.")

        # Pre-load all DB teams once
        all_teams = db.query(Team).all()

        # Step 3: Match to DB records and store with bookmaker fallback
        stored = 0
        skipped = 0

        for event in odds_data:
            home_name = event.get("home_team", "")
            away_name = event.get("away_team", "")

            home_team = _find_team(home_name, all_teams)
            away_team = _find_team(away_name, all_teams)

            if not home_team or not away_team:
                logger.warning(f"  ⚠ No DB teams for: {home_name} vs {away_name} — skipping")
                skipped += 1
                continue

            # Find DB match (try both home/away orders)
            match = (
                db.query(Match)
                .filter(Match.home_team_id == home_team.id, Match.away_team_id == away_team.id)
                .filter(Match.status == "Not Started")
                .first()
            )
            if not match:
                match = (
                    db.query(Match)
                    .filter(Match.home_team_id == away_team.id, Match.away_team_id == home_team.id)
                    .filter(Match.status == "Not Started")
                    .first()
                )
            if not match:
                logger.warning(
                    f"  ⚠ No upcoming match for: {home_team.name} vs {away_team.name} "
                    f"(API: {home_name} vs {away_name})"
                )
                skipped += 1
                continue

            # Resolve DB home/away from the match record (not from API field order)
            db_home = db.query(Team).filter(Team.id == match.home_team_id).first()
            db_away = db.query(Team).filter(Team.id == match.away_team_id).first()

            # ---- Bookmaker priority fallback ----
            bm_key, bookmaker = pick_best_bookmaker(event.get("bookmakers", []))
            if not bookmaker:
                logger.warning(f"  ⚠ No bookmakers for: {home_name} vs {away_name} — skipping")
                skipped += 1
                continue

            odds_label = f"{bm_key}_live"
            logger.info(
                f"  ✓  [{bm_key}] {home_name} / {away_name} "
                f"→ {db_home.name} vs {db_away.name}"
            )

            for market in bookmaker.get("markets", []):
                mkey = market["key"]
                all_outcomes = market.get("outcomes", [])
                
                # Dynamic insert for ALL markets into MarketOdds table
                from db.models import MarketOdds
                for outcome in all_outcomes:
                    db.add(MarketOdds(
                        match_id=match.id,
                        bookmaker=bm_key,
                        market_key=mkey,
                        outcome_name=outcome.get("name", "Unknown"),
                        price=float(outcome.get("price", 0)),
                        point=outcome.get("point"),
                        timestamp=datetime.utcnow(),
                    ))

                if mkey == "h2h":
                    # ---- EXPLICIT name-based mapping (never rely on index order) ----
                    ho, dr, aw = 0.0, 0.0, 0.0
                    for outcome in all_outcomes:
                        oname  = outcome["name"]
                        oprice = float(outcome["price"])
                        if oname.strip().lower() == "draw":
                            dr = oprice
                        elif _name_matches(oname, db_home.name):
                            ho = oprice
                        elif _name_matches(oname, db_away.name):
                            aw = oprice
                        else:
                            logger.warning(
                                f"    ⚠ Unmatched outcome: {oname!r} "
                                f"(home={db_home.name!r}, away={db_away.name!r})"
                            )

                    if not ho or not aw:
                        logger.warning(
                            f"    ⚠ Could not assign home/away for "
                            f"{db_home.name} vs {db_away.name} — "
                            f"outcomes: {[o['name'] for o in all_outcomes]}"
                        )
                        continue

                    from core.steam_detector import detect_steam
                    is_steam = detect_steam(db, match.id, bm_key, ho, aw, market="h2h")

                    if is_steam:
                        logger.warning(
                            f"    🔥 STEAM DETECTED for {db_home.name} vs {db_away.name} on {bm_key}!"
                        )

                    logger.info(
                        f"    h2h [{bm_key}] → home={ho:.2f}, draw={dr:.2f}, away={aw:.2f}"
                    )
                    
                    # Instead of overwriting Odds, we add to OddsHistory for Line Shopping
                    db.add(OddsHistory(
                        match_id=match.id,
                        bookmaker=bm_key,
                        market="h2h",
                        home_odds=ho,
                        draw_odds=dr,
                        away_odds=aw,
                        timestamp=datetime.utcnow(),
                    ))
                    stored += 1

                elif mkey == "totals":
                    over  = next(
                        (float(o["price"]) for o in all_outcomes
                         if o["name"] == "Over"  and abs(o.get("point", 0) - 2.5) < 0.01),
                        None
                    )
                    under = next(
                        (float(o["price"]) for o in all_outcomes
                         if o["name"] == "Under" and abs(o.get("point", 0) - 2.5) < 0.01),
                        None
                    )
                    if over and under:
                        logger.info(
                            f"    totals [{bm_key}] O/U 2.5 → over={over:.2f}, under={under:.2f}"
                        )
                        db.add(OddsHistory(
                            match_id=match.id,
                            bookmaker=bm_key,
                            market="totals_2.5",
                            home_odds=over,
                            draw_odds=0.0,
                            away_odds=under,
                            timestamp=datetime.utcnow(),
                        ))
                        stored += 1

        db.commit()
        logger.info(f"✅  Stored {stored} odds records. Skipped {skipped} events.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    flush_and_reload()
