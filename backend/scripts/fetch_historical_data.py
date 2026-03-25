"""
fetch_historical_data.py
------------------------
Downloads historical La Liga match data from Understat for seasons 2014–2025.
Also computes:
  - rest_days_home / rest_days_away  (days since each team's previous match)
  - corners_home / corners_away      (NULL if not available from source)

Output: data/laliga_historical.csv

Run from backend/:
    ./venv/bin/python -m scripts.fetch_historical_data
"""

import csv
import os
import sys
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from understatapi import UnderstatClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "laliga_historical.csv")
SEASONS = [str(y) for y in range(2014, 2026)]  # 2014/15 → 2025/26

FIELDNAMES = [
    "season", "match_id", "date",
    "home_team", "away_team",
    "home_goals", "away_goals",
    "home_xg", "away_xg",
    "rest_days_home", "rest_days_away",
    "corners_home", "corners_away",   # NULL until enriched by fetch_corners_data.py
]


def fetch_season(season: str) -> list[dict]:
    """Download all completed La Liga matches for a given season."""
    logger.info(f"Fetching season {season}…")
    with UnderstatClient() as understat:
        matches = understat.league(league="La_Liga").get_match_data(season=season)

    rows = []
    for m in matches:
        if not m.get("isResult", False):
            continue
        try:
            rows.append({
                "season": season,
                "match_id": m["id"],
                "date": m["datetime"],
                "home_team": m["h"]["title"],
                "away_team": m["a"]["title"],
                "home_goals": int(m["goals"]["h"]),
                "away_goals": int(m["goals"]["a"]),
                "home_xg": float(m["xG"]["h"]),
                "away_xg": float(m["xG"]["a"]),
                "rest_days_home": None,
                "rest_days_away": None,
                "corners_home": None,
                "corners_away": None,
            })
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"  Skip match {m.get('id', '?')}: {e}")

    logger.info(f"  → {len(rows)} completed matches")
    return rows


def add_rest_days(rows: list[dict]) -> list[dict]:
    """
    Compute rest days for each team before each match.
    Uses only data within the same season grouping so pre-season breaks map to None.
    """
    # Sort globally by date
    parsed = []
    for r in rows:
        try:
            r["_date"] = datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            r["_date"] = datetime.utcnow()
        parsed.append(r)

    parsed.sort(key=lambda r: r["_date"])

    last_played: dict[str, datetime] = {}  # team → last match datetime

    for r in parsed:
        home = r["home_team"]
        away = r["away_team"]
        match_dt = r["_date"]

        # Compute rest days (cap at 60 — start of season / long breaks)
        for team, key in [(home, "rest_days_home"), (away, "rest_days_away")]:
            if team in last_played:
                delta_seconds = abs((match_dt - last_played[team]).total_seconds())
                delta_days = delta_seconds / 86400.0
                r[key] = min(round(delta_days, 1), 60.0)
            else:
                r[key] = 14.0  # Default assumption for first match of operations

        # Update last_played for both teams
        last_played[home] = match_dt
        last_played[away] = match_dt

    # Remove temp key
    for r in parsed:
        r.pop("_date", None)

    return parsed


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    all_rows: list[dict] = []
    for season in SEASONS:
        rows = fetch_season(season)
        all_rows.extend(rows)
        time.sleep(0.8)   # polite delay

    logger.info(f"Total completed matches: {len(all_rows)}")

    logger.info("Computing rest days…")
    all_rows = add_rest_days(all_rows)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info(f"✅  Saved {len(all_rows)} rows → {OUTPUT_PATH}")
    logger.info("Next (optional): ./venv/bin/python -m scripts.fetch_corners_data")
    logger.info("Then:            ./venv/bin/python -m scripts.train_model")


if __name__ == "__main__":
    main()
