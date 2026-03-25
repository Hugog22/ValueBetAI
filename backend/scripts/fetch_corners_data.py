"""
fetch_corners_data.py
---------------------
Enriches data/laliga_historical.csv with real corner kick counts for
seasons 2022–2025 from API-Football (fixture statistics endpoint).

Works within the free-tier rate limit (100 req/day) by:
  1. Only fetching rows where corners_home IS NULL
  2. Getting fixture IDs from API-Football for the LaLiga seasons
  3. Writing results back to the CSV incrementally (can be re-run safely)

Run from backend/:
    ./venv/bin/python -m scripts.fetch_corners_data

NOTE: with 100 calls/day and ~1140 fixtures across 3 seasons, this script
      is designed to be run on multiple days. Progress is saved after each call.
"""

import csv
import os
import sys
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "-q"])
    import httpx

from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "laliga_historical.csv")
API_BASE  = "https://v3.football.api-sports.io"
HEADERS   = {"x-apisports-key": settings.API_SPORTS_KEY}
LALIGA_ID = 140
CORNER_SEASONS = ["2022", "2023", "2024", "2025"]
MAX_CALLS_PER_RUN = 80  # Leave 20 as safety margin per day


def get_fixtures_for_season(season: str) -> list[dict]:
    """Get all fixture IDs and match metadata for a LaLiga season."""
    resp = httpx.get(
        f"{API_BASE}/fixtures",
        headers=HEADERS,
        params={"league": LALIGA_ID, "season": season, "status": "FT"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("response", [])


def get_corners_for_fixture(fixture_id: int) -> dict | None:
    """Return corners {home, away} for a given fixture, or None on failure."""
    resp = httpx.get(
        f"{API_BASE}/fixtures/statistics",
        headers=HEADERS,
        params={"fixture": fixture_id, "type": "Corner Kicks"},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    data = resp.json().get("response", [])
    result: dict[str, int | None] = {"home": None, "away": None}
    for i, team_data in enumerate(data):
        for stat in team_data.get("statistics", []):
            if "corner" in stat["type"].lower():
                side = "home" if i == 0 else "away"
                try:
                    result[side] = int(stat["value"]) if stat["value"] is not None else None
                except (TypeError, ValueError):
                    pass
    return result


def main():
    if not os.path.exists(DATA_PATH):
        logger.error(f"CSV not found: {DATA_PATH}. Run fetch_historical_data.py first.")
        sys.exit(1)

    # Load current CSV
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fieldnames = list(rows[0].keys()) if rows else []

    # Build lookup: (season, home_team, away_team) → row index
    # Also note which rows need enrichment (corners_home is None/empty)
    needs_enrichment = {
        (r["season"], r["home_team"], r["away_team"]): i
        for i, r in enumerate(rows)
        if r["season"] in CORNER_SEASONS and (not r.get("corners_home") or r["corners_home"] in ("None", ""))
    }

    logger.info(f"Rows needing corner enrichment: {len(needs_enrichment)}")
    if not needs_enrichment:
        logger.info("Nothing to enrich. All done!")
        return

    calls_made = 0
    enriched = 0

    for season in CORNER_SEASONS:
        if calls_made >= MAX_CALLS_PER_RUN:
            break

        logger.info(f"Fetching fixture list for season {season}…")
        fixtures = get_fixtures_for_season(season)
        calls_made += 1
        time.sleep(0.5)

        for fix in fixtures:
            if calls_made >= MAX_CALLS_PER_RUN:
                logger.warning(f"Daily call limit reached ({MAX_CALLS_PER_RUN}). Re-run tomorrow.")
                break

            home = fix["teams"]["home"]["name"]
            away = fix["teams"]["away"]["name"]
            fixture_id = fix["fixture"]["id"]
            key = (season, home, away)

            if key not in needs_enrichment:
                continue

            corners = get_corners_for_fixture(fixture_id)
            calls_made += 1
            time.sleep(0.4)

            if corners and corners.get("home") is not None:
                idx = needs_enrichment[key]
                rows[idx]["corners_home"] = corners["home"]
                rows[idx]["corners_away"] = corners["away"]
                enriched += 1
                logger.info(f"  ✓ {home} vs {away} ({season}): {corners['home']}-{corners['away']} corners")

    logger.info(f"Enriched {enriched} matches. API calls made: {calls_made}")

    # Save back to CSV
    with open(DATA_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"✅  Saved enriched CSV → {DATA_PATH}")


if __name__ == "__main__":
    main()
