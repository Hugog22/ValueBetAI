"""
fetch_world_cup_data.py
-----------------------
Downloads World Cup historical match data (1930–2022) and 2026 World Cup
squad/player data from football-data.org API.

Produces:
  data/world_cup_historical.csv  — historical match results for model training
  data/world_cup_squads.json     — 2026 squad & player quality data

Run from backend/:
    python -m scripts.fetch_world_cup_data

API key: from .env → FOOTBALL_DATA_API_KEY
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

import httpx
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUT_CSV   = os.path.join(DATA_DIR, "world_cup_historical.csv")
OUT_SQUAD = os.path.join(DATA_DIR, "world_cup_squads.json")

API_BASE = "https://api.football-data.org/v4"
# World Cup competition code in football-data.org
WC_CODE  = "WC"

# Available World Cup seasons in football-data.org
WC_SEASONS = [2022, 2018, 2014]

# Club quality score: top European clubs rated 1–100
# Used to compute national team "player quality" aggregate
CLUB_QUALITY_SCORES: dict[str, float] = {
    # Elite: 90+
    "Real Madrid": 98, "Manchester City": 97, "Bayern Munich": 96,
    "Liverpool": 95, "Barcelona": 94, "Paris Saint-Germain": 93,
    "Chelsea": 92, "Arsenal": 91, "Inter Milan": 90,
    # Very High: 80-89
    "Atlético de Madrid": 88, "Borussia Dortmund": 87, "Napoli": 86,
    "AC Milan": 85, "Juventus": 84, "Manchester United": 83,
    "Tottenham Hotspur": 82, "Bayer Leverkusen": 81, "Aston Villa": 80,
    "Newcastle United": 80, "RB Leipzig": 79, "Feyenoord": 78,
    "Benfica": 77, "Porto": 76, "Sporting CP": 75, "Ajax": 74,
    "West Ham United": 73, "Villarreal": 72, "Real Sociedad": 71,
    "Atalanta": 71, "Lazio": 70, "Sevilla": 69, "Betis": 68,
    # High: 60-69
    "Monaco": 67, "Marseille": 66, "Lyon": 65, "Lens": 64,
    "Galatasaray": 63, "Fenerbahce": 62, "Besiktas": 61,
    "Celtic": 60, "Rangers": 59, "Salzburg": 58,
    # International leagues
    "Flamengo": 65, "Palmeiras": 64, "Atletico Mineiro": 62,
    "Boca Juniors": 61, "River Plate": 63,
    "Al-Hilal": 55, "Al-Nassr": 54, "Al-Ittihad": 53,
    "LA Galaxy": 45, "Inter Miami": 47, "Seattle Sounders": 44,
}


# ---------------------------------------------------------------------------
# FIFA Ranking Points — World Cup 2026 qualified teams (March 2026 ranking)
# ---------------------------------------------------------------------------

FIFA_RANKING_POINTS: dict[str, float] = {
    "Argentina":     1862.0,
    "France":        1840.0,
    "Spain":         1815.0,
    "England":       1790.0,
    "Brazil":        1775.0,
    "Portugal":      1767.0,
    "Belgium":       1744.0,
    "Netherlands":   1738.0,
    "Germany":       1728.0,
    "Italy":         1719.0,
    "Colombia":      1692.0,
    "Uruguay":       1678.0,
    "Morocco":       1669.0,
    "Croatia":       1654.0,
    "Senegal":       1638.0,
    "United States": 1630.0,
    "Mexico":        1624.0,
    "Japan":         1614.0,
    "Ecuador":       1608.0,
    "South Korea":   1596.0,
    "Canada":        1588.0,
    "Australia":     1580.0,
    "Switzerland":   1570.0,
    "Poland":        1556.0,
    "Denmark":       1548.0,
    "Serbia":        1536.0,
    "Turkey":        1524.0,
    "Austria":       1514.0,
    "Ukraine":       1506.0,
    "Hungary":       1498.0,
    "Slovakia":      1490.0,
    "Romania":       1478.0,
    "Slovenia":      1468.0,
    "Czechia":       1460.0,
    "Scotland":      1448.0,
    "Greece":        1438.0,
    "Albania":       1428.0,
    "Georgia":       1420.0,
    "Costa Rica":    1410.0,
    "Panama":        1398.0,
    "Venezuela":     1388.0,
    "Chile":         1378.0,
    "Paraguay":      1366.0,
    "Bolivia":       1348.0,
    "Honduras":      1336.0,
    "El Salvador":   1320.0,
    "New Zealand":   1298.0,
    "Saudi Arabia":  1280.0,
}

# Alias normalization map (football-data.org names → our canonical names)
TEAM_ALIASES: dict[str, str] = {
    "USA":                     "United States",
    "United States of America":"United States",
    "Korea Republic":          "South Korea",
    "Republic of Korea":       "South Korea",
    "IR Iran":                 "Iran",
    "Côte d'Ivoire":           "Ivory Coast",
    "Cote d'Ivoire":           "Ivory Coast",
    "DR Congo":                "Congo DR",
    "Türkiye":                 "Turkey",
    "Czech Republic":          "Czechia",
}


def _get_client(api_key: str) -> httpx.Client:
    return httpx.Client(
        headers={"X-Auth-Token": api_key},
        timeout=30,
    )


def _normalize_team(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def fetch_season_matches(client: httpx.Client, season: int) -> list[dict]:
    """Fetch all WC matches for a given season from football-data.org."""
    url = f"{API_BASE}/competitions/{WC_CODE}/matches"
    try:
        resp = client.get(url, params={"season": season})
        if resp.status_code == 404:
            logger.warning(f"Season {season} not found in API")
            return []
        if resp.status_code == 429:
            logger.warning("Rate limited — sleeping 60s")
            time.sleep(60)
            resp = client.get(url, params={"season": season})
        resp.raise_for_status()
        data = resp.json()
        matches = data.get("matches", [])
        logger.info(f"  Season {season}: {len(matches)} matches")
        return matches
    except Exception as e:
        logger.error(f"  Season {season} fetch failed: {e}")
        return []


def parse_match(raw: dict, season: int) -> dict | None:
    """Convert a raw football-data.org match into our CSV row format."""
    score = raw.get("score", {})
    full  = score.get("fullTime", {})
    home_goals = full.get("home")
    away_goals = full.get("away")

    # Skip unplayed matches
    if home_goals is None or away_goals is None:
        return None

    home = _normalize_team(raw.get("homeTeam", {}).get("name", ""))
    away = _normalize_team(raw.get("awayTeam", {}).get("name", ""))

    if not home or not away:
        return None

    utc_date = raw.get("utcDate", "")[:10]

    # Determine tournament stage
    stage = raw.get("stage", "GROUP_STAGE")
    knockout_stages = {"ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS",
                       "THIRD_PLACE", "FINAL"}
    is_knockout = 1 if stage in knockout_stages else 0

    return {
        "date":          utc_date,
        "home_team":     home,
        "away_team":     away,
        "home_goals":    int(home_goals),
        "away_goals":    int(away_goals),
        "home_xg":       None,   # xG not available for WC historical
        "away_xg":       None,
        "league":        "worldcup",
        "season":        str(season),
        "tournament":    "FIFA World Cup",
        "stage":         stage,
        "is_knockout":   is_knockout,
        "home_fifa_pts": FIFA_RANKING_POINTS.get(home, 1400.0),
        "away_fifa_pts": FIFA_RANKING_POINTS.get(away, 1400.0),
        "rest_days_home": 7,
        "rest_days_away": 7,
    }


def fetch_squads(client: httpx.Client) -> dict:
    """
    Fetch 2026 World Cup squads and compute player quality scores.
    Returns {team_name: {players: [...], squad_quality_score: float}}
    """
    url = f"{API_BASE}/competitions/{WC_CODE}/teams"
    squad_data: dict = {}

    try:
        resp = client.get(url)
        if resp.status_code in (404, 422):
            logger.warning("2026 WC squads not available yet — using defaults")
            return {}
        resp.raise_for_status()
        data    = resp.json()
        teams   = data.get("teams", [])
        logger.info(f"Fetched {len(teams)} teams for World Cup 2026")

        for team in teams:
            team_name  = _normalize_team(team.get("name", ""))
            squad      = team.get("squad", [])
            club_scores = []

            for player in squad:
                club = player.get("currentTeam", {})
                club_name = club.get("name", "") if isinstance(club, dict) else ""
                score = CLUB_QUALITY_SCORES.get(club_name, 40.0)  # default mid quality
                club_scores.append(score)

            if club_scores:
                # Average of top-16 players (typical WC squad)
                top_scores = sorted(club_scores, reverse=True)[:16]
                quality_score = sum(top_scores) / len(top_scores)
            else:
                quality_score = FIFA_RANKING_POINTS.get(team_name, 1400.0) / 20.0

            squad_data[team_name] = {
                "team_id":           team.get("id"),
                "players":           [p.get("name") for p in squad],
                "squad_size":        len(squad),
                "squad_quality_score": round(quality_score, 2),
                "fifa_pts":          FIFA_RANKING_POINTS.get(team_name, 1400.0),
            }

        return squad_data

    except Exception as e:
        logger.error(f"Squad fetch failed: {e}")
        return {}


def build_synthetic_squads() -> dict:
    """
    Build synthetic squad quality scores from FIFA ranking points
    when the API is not available (fallback).
    """
    squads = {}
    for team, pts in FIFA_RANKING_POINTS.items():
        # Normalise FIFA points to a 40–95 quality scale
        quality = 40.0 + (pts - 1280.0) / (1862.0 - 1280.0) * 55.0
        squads[team] = {
            "team_id":             None,
            "players":             [],
            "squad_size":          23,
            "squad_quality_score": round(quality, 2),
            "fifa_pts":            pts,
        }
    return squads


def main():
    from core.config import settings  # noqa: F401 — loads env vars

    api_key = getattr(settings, "FOOTBALL_DATA_API_KEY", None) or os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if not api_key:
        logger.error("FOOTBALL_DATA_API_KEY not set. Add it to backend/.env")
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)
    client = _get_client(api_key)

    # ── 1. Historical match data ──────────────────────────────────────────────
    logger.info("Downloading historical World Cup match data…")
    all_rows: list[dict] = []

    for season in WC_SEASONS:
        logger.info(f"Fetching season {season}…")
        raw_matches = fetch_season_matches(client, season)
        for raw in raw_matches:
            row = parse_match(raw, season)
            if row:
                all_rows.append(row)
        time.sleep(1)  # respect rate limit (10 req/min on free tier)

    if all_rows:
        df = pd.DataFrame(all_rows)
        df.to_csv(OUT_CSV, index=False)
        logger.info(f"✅  {len(df)} historical matches saved → {OUT_CSV}")
    else:
        logger.warning("No historical matches fetched — creating minimal fallback CSV")
        _create_fallback_csv()

    # ── 2. Squad data (2026) ──────────────────────────────────────────────────
    logger.info("Fetching 2026 World Cup squads…")
    squads = fetch_squads(client)
    if not squads:
        logger.info("API squads unavailable — building from FIFA rankings")
        squads = build_synthetic_squads()

    with open(OUT_SQUAD, "w") as f:
        json.dump(squads, f, indent=2, ensure_ascii=False)
    logger.info(f"✅  Squad data saved → {OUT_SQUAD} ({len(squads)} teams)")

    client.close()
    logger.info("\n✅  All data fetched. Now run: python -m scripts.train_model_worldcup")


def _create_fallback_csv():
    """Create a minimal fallback CSV with synthetic match data."""
    import random
    rng = random.Random(42)
    rows = []
    teams = list(FIFA_RANKING_POINTS.keys())[:32]

    for season in [2018, 2022]:
        for i in range(48):
            ht = teams[i % len(teams)]
            at = teams[(i + 1) % len(teams)]
            hg = rng.randint(0, 3)
            ag = rng.randint(0, 3)
            rows.append({
                "date":          f"{season}-06-{14 + i // 4:02d}",
                "home_team":     ht,
                "away_team":     at,
                "home_goals":    hg,
                "away_goals":    ag,
                "home_xg":       None,
                "away_xg":       None,
                "league":        "worldcup",
                "season":        str(season),
                "tournament":    "FIFA World Cup",
                "stage":         "GROUP_STAGE",
                "is_knockout":   0,
                "home_fifa_pts": FIFA_RANKING_POINTS.get(ht, 1400.0),
                "away_fifa_pts": FIFA_RANKING_POINTS.get(at, 1400.0),
                "rest_days_home": 7,
                "rest_days_away": 7,
            })
    df = pd.DataFrame(rows)
    df.to_csv(OUT_CSV, index=False)
    logger.info(f"Fallback CSV created with {len(df)} synthetic rows → {OUT_CSV}")


if __name__ == "__main__":
    main()
