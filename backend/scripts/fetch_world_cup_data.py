"""
fetch_world_cup_data.py (Updated to fetch ALL international data)
-----------------------
Downloads complete international match data from martj42/international_results
and builds the dataset for AI training (World Cup, Euro, Copa America, etc.).

Run from backend/:
    python -m scripts.fetch_world_cup_data
"""

import json
import logging
import os
import sys
import httpx
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUT_CSV   = os.path.join(DATA_DIR, "world_cup_historical.csv")
OUT_SQUAD = os.path.join(DATA_DIR, "world_cup_squads.json")
RESULTS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"

# Competitions to include in our AI training
TARGET_TOURNAMENTS = {
    "FIFA World Cup",
    "UEFA Euro",
    "Copa América",
    "African Cup of Nations",
    "AFC Asian Cup",
    "Gold Cup",
    "UEFA Nations League",
    "CONCACAF Nations League",
}

# ---------------------------------------------------------------------------
# FIFA Ranking Points
# ---------------------------------------------------------------------------
FIFA_RANKING_POINTS: dict[str, float] = {
    "Argentina":     1862.0, "France":        1840.0, "Spain":         1815.0,
    "England":       1790.0, "Brazil":        1775.0, "Portugal":      1767.0,
    "Belgium":       1744.0, "Netherlands":   1738.0, "Germany":       1728.0,
    "Italy":         1719.0, "Colombia":      1692.0, "Uruguay":       1678.0,
    "Morocco":       1669.0, "Croatia":       1654.0, "Senegal":       1638.0,
    "United States": 1630.0, "Mexico":        1624.0, "Japan":         1614.0,
    "Ecuador":       1608.0, "South Korea":   1596.0, "Canada":        1588.0,
    "Australia":     1580.0, "Switzerland":   1570.0, "Poland":        1556.0,
    "Denmark":       1548.0, "Serbia":        1536.0, "Turkey":        1524.0,
    "Austria":       1514.0, "Ukraine":       1506.0, "Hungary":       1498.0,
    "Slovakia":      1490.0, "Romania":       1478.0, "Slovenia":      1468.0,
    "Czechia":       1460.0, "Scotland":      1448.0, "Greece":        1438.0,
    "Albania":       1428.0, "Georgia":       1420.0, "Costa Rica":    1410.0,
    "Panama":        1398.0, "Venezuela":     1388.0, "Chile":         1378.0,
    "Paraguay":      1366.0, "Bolivia":       1348.0, "Honduras":      1336.0,
    "El Salvador":   1320.0, "New Zealand":   1298.0, "Saudi Arabia":  1280.0,
}

def download_csv() -> pd.DataFrame:
    local_path = os.path.join(DATA_DIR, "results.csv")
    if os.path.exists(local_path):
        logger.info(f"Reading local {local_path}...")
        df = pd.read_csv(local_path)
        logger.info(f"Loaded {len(df)} total historical matches.")
        return df
    
    logger.info(f"Downloading international matches from {RESULTS_URL}...")
    try:
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        df = pd.read_csv(RESULTS_URL)
        df.to_csv(local_path, index=False)
        logger.info(f"Downloaded {len(df)} total historical matches.")
        return df
    except Exception as e:
        logger.error(f"Failed to download: {e}")
        return pd.DataFrame()

def build_synthetic_squads() -> dict:
    squads = {}
    for team, pts in FIFA_RANKING_POINTS.items():
        quality = 40.0 + (pts - 1280.0) / (1862.0 - 1280.0) * 55.0
        squads[team] = {
            "team_id":             None,
            "players":             [],
            "squad_size":          23,
            "squad_quality_score": round(quality, 2),
            "fifa_pts":            pts,
        }
    return squads

def process_data(df: pd.DataFrame):
    # Filter by date (e.g. >= 2010 to have modern football style)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df[df['date'].dt.year >= 2010].copy()
    
    # Filter tournaments
    df = df[df['tournament'].isin(TARGET_TOURNAMENTS)].copy()
    
    rows = []
    for _, row in df.iterrows():
        ht = row['home_team']
        at = row['away_team']
        
        # Determine if knockout (heuristic: if not 'group' it might be knockout, but results.csv doesn't specify stage clearly, so we will set it to 0 and let the model learn from tournament and quality)
        rows.append({
            "date":          row['date'].strftime('%Y-%m-%d'),
            "home_team":     ht,
            "away_team":     at,
            "home_goals":    row['home_score'],
            "away_goals":    row['away_score'],
            "home_xg":       None,
            "away_xg":       None,
            "league":        "international",
            "season":        str(row['date'].year),
            "tournament":    row['tournament'],
            "stage":         "UNKNOWN",
            "is_knockout":   0,
            "home_fifa_pts": FIFA_RANKING_POINTS.get(ht, 1400.0),
            "away_fifa_pts": FIFA_RANKING_POINTS.get(at, 1400.0),
            "rest_days_home": 7,
            "rest_days_away": 7,
        })
    
    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_CSV, index=False)
    logger.info(f"Saved {len(out_df)} official international matches to {OUT_CSV}")

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    df = download_csv()
    if not df.empty:
        process_data(df)
    
    squads = build_synthetic_squads()
    with open(OUT_SQUAD, "w") as f:
        json.dump(squads, f, indent=2, ensure_ascii=False)
    logger.info(f"Squad data saved to {OUT_SQUAD}")

if __name__ == "__main__":
    main()
