"""
fetch_nba_data.py
-----------------
Downloads historical NBA season data using the BallDontLie API
(https://api.balldontlie.io — free tier, no API key required for basic endpoints).

Features per game:
  season, game_id, date, home_team, away_team,
  home_score, away_score,
  home_win (1/0), total_points,
  rest_days_home, rest_days_away,
  home_pts_avg10, away_pts_avg10,          (rolling 10-game attack)
  home_pts_allowed_avg10, away_pts_allowed_avg10,  (rolling 10-game defense)
  home_win_pct10, away_win_pct10,          (rolling 10-game win rate)
  home_elo, away_elo                       (ELO ratings, computed in-script)

Output: data/nba_historical.csv

Usage:
  ./venv/bin/python -m scripts.fetch_nba_data
"""

import csv
import os
import sys
import time
import logging
import math
from datetime import datetime

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "nba_historical.csv")

# BallDontLie v1 (free, no key, 60 req/min)
BASE_URL = "https://api.balldontlie.io/v1"

SEASONS = list(range(2015, 2025))  # 2015-16 → 2024-25 (~9 seasons, ~12k games)

FIELDNAMES = [
    "season", "game_id", "date",
    "home_team", "away_team",
    "home_score", "away_score",
    "home_win", "total_points",
    "rest_days_home", "rest_days_away",
    "home_pts_avg10", "away_pts_avg10",
    "home_pts_allowed_avg10", "away_pts_allowed_avg10",
    "home_win_pct10", "away_win_pct10",
    "home_elo", "away_elo", "elo_diff",
]

# ELO parameters (NBA uses higher K than football — more variance per game)
ELO_BASE = 1500.0
ELO_K    = 25.0


def fetch_games_for_season(season: int) -> list[dict]:
    """Fetch all finished games for a given NBA season via BallDontLie paginated API."""
    games = []
    cursor = 0
    page = 1

    logger.info(f"  Season {season}-{season+1}…")

    while True:
        try:
            params = {
                "seasons[]": season,
                "per_page": 100,
                "postseason": "false",  # regular season only for statistical consistency
            }
            if cursor:
                params["cursor"] = cursor

            resp = httpx.get(f"{BASE_URL}/games", params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"  Season {season} page {page} error: {e}")
            break

        batch = data.get("data", [])
        for g in batch:
            # Only include finished games with scores
            if g.get("status") != "Final":
                continue
            home_score = g.get("home_team_score")
            away_score = g.get("visitor_team_score")
            if home_score is None or away_score is None:
                continue

            games.append({
                "season":     season,
                "game_id":    g["id"],
                "date":       g.get("date", "")[:10],  # YYYY-MM-DD
                "home_team":  g["home_team"]["full_name"],
                "away_team":  g["visitor_team"]["full_name"],
                "home_score": int(home_score),
                "away_score": int(away_score),
                "home_win":   1 if int(home_score) > int(away_score) else 0,
                "total_points": int(home_score) + int(away_score),
            })

        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")
        if not next_cursor or not batch:
            break
        cursor = next_cursor
        page += 1
        time.sleep(1.1)  # stay under 60 req/min

    logger.info(f"    → {len(games)} finished regular-season games")
    return games


def add_rest_days(rows: list[dict]) -> list[dict]:
    """Compute rest days between games for each team."""
    parsed = []
    for r in rows:
        try:
            r["_date"] = datetime.strptime(r["date"], "%Y-%m-%d")
        except (ValueError, TypeError):
            r["_date"] = datetime.utcnow()
        parsed.append(r)

    parsed.sort(key=lambda r: r["_date"])
    last_played: dict[str, datetime] = {}

    for r in parsed:
        for team, col in [(r["home_team"], "rest_days_home"), (r["away_team"], "rest_days_away")]:
            if team in last_played:
                delta = abs((r["_date"] - last_played[team]).total_seconds()) / 86400.0
                r[col] = min(round(delta, 1), 30.0)
            else:
                r[col] = 5.0  # default start-of-season
            last_played[team] = r["_date"]

    for r in parsed:
        r.pop("_date", None)
    return parsed


def add_rolling_features(rows: list[dict]) -> list[dict]:
    """
    Add rolling 10-game averages (pre-match, shift(1) to avoid leakage):
      - points scored (offense)
      - points allowed (defense)
      - win rate
    """
    # Sort chronologically
    rows.sort(key=lambda r: r["date"])

    # Per-team lookback buffer (deque of last 10 games)
    from collections import deque
    team_history: dict[str, deque] = {}

    def get_rolling(team: str) -> dict:
        hist = list(team_history.get(team, deque(maxlen=10)))
        if not hist:
            return {"pts": 105.0, "pts_allowed": 105.0, "wins": 0.5}
        return {
            "pts":         sum(h["pts"] for h in hist) / len(hist),
            "pts_allowed": sum(h["pts_allowed"] for h in hist) / len(hist),
            "wins":        sum(h["win"] for h in hist) / len(hist),
        }

    def update_history(team: str, pts: int, pts_allowed: int, win: int):
        if team not in team_history:
            team_history[team] = deque(maxlen=10)
        team_history[team].append({"pts": pts, "pts_allowed": pts_allowed, "win": win})

    for r in rows:
        # Get rolling stats BEFORE updating with this game's result
        home_roll = get_rolling(r["home_team"])
        away_roll = get_rolling(r["away_team"])

        r["home_pts_avg10"]         = round(home_roll["pts"], 2)
        r["away_pts_avg10"]         = round(away_roll["pts"], 2)
        r["home_pts_allowed_avg10"] = round(home_roll["pts_allowed"], 2)
        r["away_pts_allowed_avg10"] = round(away_roll["pts_allowed"], 2)
        r["home_win_pct10"]         = round(home_roll["wins"], 4)
        r["away_win_pct10"]         = round(away_roll["wins"], 4)

        # Update after recording
        update_history(r["home_team"], r["home_score"], r["away_score"], r["home_win"])
        update_history(r["away_team"], r["away_score"], r["home_score"], 1 - r["home_win"])

    return rows


def add_elo_ratings(rows: list[dict]) -> list[dict]:
    """Compute ELO ratings (pre-match, no leakage) — K=25 for NBA."""
    rows.sort(key=lambda r: r["date"])
    elo: dict[str, float] = {}

    for r in rows:
        ht, at = r["home_team"], r["away_team"]
        eh = elo.get(ht, ELO_BASE)
        ea = elo.get(at, ELO_BASE)

        r["home_elo"] = round(eh, 1)
        r["away_elo"] = round(ea, 1)
        r["elo_diff"] = round(eh - ea, 1)

        # Update ELO based on outcome
        exp_home = 1.0 / (1.0 + 10.0 ** ((ea - eh) / 400.0))
        score_home = float(r["home_win"])
        elo[ht] = eh + ELO_K * (score_home - exp_home)
        elo[at] = ea + ELO_K * ((1 - score_home) - (1 - exp_home))

    return rows


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    all_rows: list[dict] = []
    for season in SEASONS:
        rows = fetch_games_for_season(season)
        all_rows.extend(rows)
        time.sleep(1.5)

    logger.info(f"\nTotal games fetched: {len(all_rows)}")

    # Initialize columns before rolling features
    for r in all_rows:
        r.setdefault("rest_days_home", 5.0)
        r.setdefault("rest_days_away", 5.0)
        r.setdefault("home_pts_avg10", 105.0)
        r.setdefault("away_pts_avg10", 105.0)
        r.setdefault("home_pts_allowed_avg10", 105.0)
        r.setdefault("away_pts_allowed_avg10", 105.0)
        r.setdefault("home_win_pct10", 0.5)
        r.setdefault("away_win_pct10", 0.5)
        r.setdefault("home_elo", ELO_BASE)
        r.setdefault("away_elo", ELO_BASE)
        r.setdefault("elo_diff", 0.0)

    logger.info("Computing rest days…")
    all_rows = add_rest_days(all_rows)

    logger.info("Computing rolling 10-game features…")
    all_rows = add_rolling_features(all_rows)

    logger.info("Computing ELO ratings…")
    all_rows = add_elo_ratings(all_rows)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    logger.info(f"✅  Saved {len(all_rows)} NBA games → {OUTPUT_PATH}")
    logger.info("\nNext step:")
    logger.info("  python -m scripts.train_model_nba")


if __name__ == "__main__":
    main()
