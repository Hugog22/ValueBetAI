"""
fix_duplicate_teams.py
----------------------
One-time script to merge duplicate Team records caused by different API name
variants for the same team (e.g. 'Bosnia-Herzegovina' vs 'Bosnia and Herzegovina').

Run from backend/ directory:
    python scripts/fix_duplicate_teams.py

What it does:
  1. Finds Teams whose normalized names resolve to the same canonical name.
  2. Picks the canonical Team (the one matching the alias target, or lowest id).
  3. Reassigns all Match.home_team_id and Match.away_team_id from duplicates → canonical.
  4. Reassigns all Odds.match_id and OddsHistory.match_id for affected matches.
  5. Deletes the duplicate Team records.
  6. Also deduplicates Match records: if two matches have the same
     (home_team_id, away_team_id) and dates within 3 hours, keeps the one
     with more data (odds/goals) and deletes the other.
"""

import sys
import os
import unicodedata
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.session import SessionLocal
from db.models import Team, Match, Odds, OddsHistory, Bet

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Same aliases as world_cup_etl.py
TEAM_ALIASES: dict[str, str] = {
    "USA":                          "United States",
    "Korea Republic":               "South Korea",
    "Republic of Korea":            "South Korea",
    "Türkiye":                      "Turkey",
    "Czech Republic":               "Czechia",
    "IR Iran":                      "Iran",
    "Côte d'Ivoire":                "Ivory Coast",
    "Bosnia-Herzegovina":           "Bosnia and Herzegovina",
    "Bosnia & Herzegovina":         "Bosnia and Herzegovina",
    "Guinea-Bissau":                "Guinea Bissau",
    "Equatorial-Guinea":            "Equatorial Guinea",
    "DR Congo":                     "Democratic Republic of Congo",
    "Congo DR":                     "Democratic Republic of Congo",
    "Cape Verde Islands":           "Cape Verde",
}


def _normalize(name: str) -> str:
    name = TEAM_ALIASES.get(name, name)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    ascii_name = ascii_name.replace("-", " ")
    return ascii_name.lower().strip()


def fix_duplicate_teams():
    db = SessionLocal()
    try:
        all_teams = db.query(Team).all()
        logger.info(f"Found {len(all_teams)} total teams in DB.")

        # Group teams by normalized name
        groups: dict[str, list[Team]] = {}
        for team in all_teams:
            norm = _normalize(team.name)
            groups.setdefault(norm, []).append(team)

        merged_teams = 0
        for norm_name, team_list in groups.items():
            if len(team_list) <= 1:
                continue

            logger.info(f"\n🔀 Duplicate group [{norm_name}]:")
            for t in team_list:
                logger.info(f"   id={t.id} name='{t.name}'")

            # Pick canonical: prefer the team whose name matches a canonical alias target,
            # or the one with the lowest id as tiebreaker.
            canonical_names = set(TEAM_ALIASES.values())
            canonical = next(
                (t for t in sorted(team_list, key=lambda x: x.id) if t.name in canonical_names),
                sorted(team_list, key=lambda x: x.id)[0]
            )
            duplicates = [t for t in team_list if t.id != canonical.id]

            logger.info(f"   → Canonical: id={canonical.id} name='{canonical.name}'")
            logger.info(f"   → Duplicates to merge: {[t.id for t in duplicates]}")

            for dup in duplicates:
                # Reassign Matches that reference the duplicate team
                home_matches = db.query(Match).filter(Match.home_team_id == dup.id).all()
                away_matches = db.query(Match).filter(Match.away_team_id == dup.id).all()

                for m in home_matches:
                    logger.info(f"     Match id={m.id}: home_team_id {dup.id} → {canonical.id}")
                    m.home_team_id = canonical.id
                for m in away_matches:
                    logger.info(f"     Match id={m.id}: away_team_id {dup.id} → {canonical.id}")
                    m.away_team_id = canonical.id

                db.flush()

                # Delete the duplicate team
                db.delete(dup)
                merged_teams += 1

        db.commit()
        logger.info(f"\n✅ Merged {merged_teams} duplicate team(s).")

        # Now deduplicate Matches with same (home_team_id, away_team_id, date ±3h)
        logger.info("\n🔍 Checking for duplicate Match records...")
        all_matches = db.query(Match).order_by(Match.home_team_id, Match.away_team_id, Match.date).all()

        from datetime import timedelta
        seen: list[Match] = []
        duplicate_match_ids: list[int] = []

        for m in all_matches:
            is_dup = False
            for canonical_m in seen:
                if (canonical_m.home_team_id == m.home_team_id
                        and canonical_m.away_team_id == m.away_team_id
                        and abs((canonical_m.date - m.date).total_seconds()) <= 10800):  # 3h
                    # This is a duplicate — merge into the canonical match
                    logger.info(
                        f"  Duplicate match: id={m.id} "
                        f"(home={m.home_team_id}, away={m.away_team_id}, date={m.date}) "
                        f"→ merging into id={canonical_m.id}"
                    )
                    # If canonical doesn't have goals but dup does, copy them
                    if canonical_m.home_goals is None and m.home_goals is not None:
                        canonical_m.home_goals = m.home_goals
                        canonical_m.away_goals = m.away_goals
                        canonical_m.status = m.status
                    # Reassign Odds, OddsHistory, Bets, MarketOdds, Prediction to canonical match
                    db.query(Odds).filter(Odds.match_id == m.id).update(
                        {"match_id": canonical_m.id}, synchronize_session=False
                    )
                    db.query(OddsHistory).filter(OddsHistory.match_id == m.id).update(
                        {"match_id": canonical_m.id}, synchronize_session=False
                    )
                    db.query(Bet).filter(Bet.match_id == m.id).update(
                        {"match_id": canonical_m.id}, synchronize_session=False
                    )
                    from db.models import MarketOdds, Prediction
                    db.query(MarketOdds).filter(MarketOdds.match_id == m.id).update(
                        {"match_id": canonical_m.id}, synchronize_session=False
                    )
                    db.query(Prediction).filter(Prediction.match_id == m.id).update(
                        {"match_id": canonical_m.id}, synchronize_session=False
                    )
                    duplicate_match_ids.append(m.id)
                    is_dup = True
                    break
            if not is_dup:
                seen.append(m)

        db.flush()

        for mid in duplicate_match_ids:
            m = db.query(Match).filter(Match.id == mid).first()
            if m:
                db.delete(m)

        db.commit()
        logger.info(f"✅ Removed {len(duplicate_match_ids)} duplicate Match record(s).")
        logger.info("\n🎉 Database cleanup complete!")

    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_duplicate_teams()
