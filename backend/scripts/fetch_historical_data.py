"""
fetch_historical_data.py
------------------------
Downloads historical match data from Understat for multiple leagues:
  - La Liga (Spain)   — 2014–2025
  - EPL (England)     — 2014–2025
  - Champions League  — 2014–2025

Outputs:
  data/football_historical.csv  — combined multi-league dataset (for training)
  data/laliga_historical.csv    — LaLiga-only backward-compat file

Features per match:
  season, match_id, date, league,
  home_team, away_team, home_goals, away_goals,
  home_xg, away_xg, rest_days_home, rest_days_away, corners_home, corners_away

Usage:
  ./venv/bin/python -m scripts.fetch_historical_data [--league La_Liga EPL Champions_League]
"""

import csv
import os
import sys
import time
import logging
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from understatapi import UnderstatClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_MULTI  = os.path.join(DATA_DIR, "football_historical.csv")
OUTPUT_LALIGA = os.path.join(DATA_DIR, "laliga_historical.csv")

SEASONS = [str(y) for y in range(2014, 2026)]  # 2014/15 → 2025/26

# Understat league keys and their friendly names
UNDERSTAT_LEAGUES = {
    "La_Liga":          "laliga",
    "EPL":              "premier",
    "Champions_League": "champions",
}

FIELDNAMES = [
    "season", "match_id", "date", "league",
    "home_team", "away_team",
    "home_goals", "away_goals",
    "home_xg", "away_xg",
    "rest_days_home", "rest_days_away",
    "corners_home", "corners_away",
]


def fetch_league_season(understat_key: str, league_code: str, season: str) -> list[dict]:
    """Download all completed matches for a given Understat league+season."""
    logger.info(f"  [{understat_key}] Season {season}…")
    try:
        with UnderstatClient() as understat:
            matches = understat.league(league=understat_key).get_match_data(season=season)
    except Exception as e:
        logger.warning(f"  [{understat_key}] Season {season} failed: {e}")
        return []

    rows = []
    for m in matches:
        if not m.get("isResult", False):
            continue
        try:
            rows.append({
                "season":        season,
                "match_id":      m["id"],
                "date":          m["datetime"],
                "league":        league_code,
                "home_team":     m["h"]["title"],
                "away_team":     m["a"]["title"],
                "home_goals":    int(m["goals"]["h"]),
                "away_goals":    int(m["goals"]["a"]),
                "home_xg":       float(m["xG"]["h"]),
                "away_xg":       float(m["xG"]["a"]),
                "rest_days_home": None,
                "rest_days_away": None,
                "corners_home":  None,
                "corners_away":  None,
            })
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"  Skip match {m.get('id', '?')}: {e}")

    logger.info(f"    → {len(rows)} completed matches")
    return rows


def add_rest_days(rows: list[dict]) -> list[dict]:
    """
    Compute rest days per team per match (chronological, in-league order).
    Rest days track independently per league to avoid cross-competition artifacts.
    """
    parsed = []
    for r in rows:
        try:
            r["_date"] = datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            r["_date"] = datetime.utcnow()
        parsed.append(r)

    # Sort by league, then date so rest days are computed within-league
    parsed.sort(key=lambda r: (r["league"], r["_date"]))

    last_played: dict[str, datetime] = {}

    for r in parsed:
        home = r["league"] + "|" + r["home_team"]
        away = r["league"] + "|" + r["away_team"]
        match_dt = r["_date"]

        for team_key, col in [(home, "rest_days_home"), (away, "rest_days_away")]:
            if team_key in last_played:
                delta_days = abs((match_dt - last_played[team_key]).total_seconds()) / 86400.0
                r[col] = min(round(delta_days, 1), 60.0)
            else:
                r[col] = 14.0  # default for first match of season

        last_played[home] = match_dt
        last_played[away] = match_dt

    for r in parsed:
        r.pop("_date", None)

    return parsed


def main():
    parser = argparse.ArgumentParser(description="Fetch multi-league historical football data")
    parser.add_argument(
        "--leagues", nargs="+",
        choices=list(UNDERSTAT_LEAGUES.keys()),
        default=list(UNDERSTAT_LEAGUES.keys()),
        help="Understat league keys to download (default: all)"
    )
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    all_rows: list[dict] = []

    for understat_key in args.leagues:
        league_code = UNDERSTAT_LEAGUES[understat_key]
        logger.info(f"\n{'='*50}")
        logger.info(f"League: {understat_key} → '{league_code}'")
        logger.info(f"{'='*50}")

        for season in SEASONS:
            rows = fetch_league_season(understat_key, league_code, season)
            all_rows.extend(rows)
            time.sleep(0.8)  # polite delay

    logger.info(f"\nTotal completed matches across all leagues: {len(all_rows)}")

    logger.info("Computing rest days…")
    all_rows = add_rest_days(all_rows)

    # ── Write combined file (for multi-league training) ──────────────────────
    with open(OUTPUT_MULTI, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)
    logger.info(f"✅  Saved {len(all_rows)} rows → {OUTPUT_MULTI}")

    # ── Write LaLiga-only backward-compat file ───────────────────────────────
    laliga_rows = [r for r in all_rows if r["league"] == "laliga"]
    if laliga_rows:
        with open(OUTPUT_LALIGA, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(laliga_rows)
        logger.info(f"✅  LaLiga-only file: {len(laliga_rows)} rows → {OUTPUT_LALIGA}")

    breakdown = {}
    for r in all_rows:
        breakdown[r["league"]] = breakdown.get(r["league"], 0) + 1
    for league, count in sorted(breakdown.items()):
        logger.info(f"   {league}: {count} matches")

    logger.info("\nNext steps:")
    logger.info("  python -m scripts.fetch_nba_data")
    logger.info("  python -m scripts.train_model       (retrain football model)")
    logger.info("  python -m scripts.train_model_nba   (train NBA model)")


if __name__ == "__main__":
    main()
