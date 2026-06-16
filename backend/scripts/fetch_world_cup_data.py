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
    "France": 1887.11, "Argentina": 1877.27, "Spain": 1856.03,
    "England": 1828.02, "Portugal": 1767.85, "Brazil": 1765.34,
    "Morocco": 1755.62, "Netherlands": 1749.20, "Germany": 1743.54,
    "Belgium": 1733.93, "Croatia": 1714.87, "Italy": 1704.73,
    "Mexico": 1700.98, "Colombia": 1698.35, "United States": 1688.53,
    "Senegal": 1667.66, "Japan": 1665.94, "Uruguay": 1661.95,
    "Switzerland": 1640.92, "Denmark": 1619.47, "South Korea": 1612.55,
    "Australia": 1605.61, "Iran": 1605.12, "Austria": 1597.40,
    "Nigeria": 1585.02, "Turkey": 1579.47, "Algeria": 1571.03,
    "Ecuador": 1570.76, "Egypt": 1570.67, "Ivory Coast": 1568.62,
    "Norway": 1552.18, "Canada": 1551.50, "Ukraine": 1549.29,
    "Panama": 1539.16, "Sweden": 1533.19, "Russia": 1529.60,
    "Poland": 1526.18, "Scotland": 1518.77, "Wales": 1516.95,
    "Hungary": 1506.39, "Serbia": 1502.13, "Paraguay": 1488.05,
    "Czechia": 1484.82, "Cameroon": 1481.24, "DR Congo": 1474.43,
    "Slovakia": 1473.66, "Greece": 1473.19, "Venezuela": 1469.18,
    "Qatar": 1459.45, "Uzbekistan": 1458.73, "Chile": 1458.20,
    "Peru": 1457.69, "Costa Rica": 1456.03, "Romania": 1455.89,
    "Mali": 1455.59, "Tunisia": 1453.00, "Iraq": 1451.53,
    "Republic of Ireland": 1441.10, "Slovenia": 1441.09, "Saudi Arabia": 1435.00,
    "South Africa": 1414.88, "Burkina Faso": 1406.99, "Bosnia and Herzegovina": 1395.19,
    "Cape Verde": 1389.79, "Jordan": 1387.74, "Honduras": 1378.97,
    "Albania": 1376.03, "United Arab Emirates": 1370.47, "North Macedonia": 1369.16,
    "Northern Ireland": 1365.30, "Jamaica": 1357.84, "Georgia": 1355.26,
    "Ghana": 1346.88, "Iceland": 1342.77, "Finland": 1341.92,
    "Israel": 1333.90, "Bolivia": 1326.00, "Kosovo": 1319.12,
    "Oman": 1306.90, "Montenegro": 1301.98, "Guinea": 1295.60,
    "New Zealand": 1290.04, "Curaçao": 1287.00, "Syria": 1283.05,
    "Haiti": 1277.67, "Gabon": 1272.51, "Bulgaria": 1271.68,
    "Angola": 1265.58, "Uganda": 1264.09, "Zambia": 1255.82,
    "China PR": 1254.81, "Bahrain": 1254.41, "Benin": 1252.17,
    "Thailand": 1250.80, "Palestine": 1243.71, "Belarus": 1242.88,
    "Guatemala": 1238.74, "Luxembourg": 1232.82, "Vietnam": 1225.68,
    "El Salvador": 1225.34, "Tajikistan": 1224.19, "Trinidad and Tobago": 1219.59,
    "Mozambique": 1218.62,
}

def download_csv(force=False) -> pd.DataFrame:
    local_path = os.path.join(DATA_DIR, "results.csv")
    if not force and os.path.exists(local_path):
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

def main(force=False):
    os.makedirs(DATA_DIR, exist_ok=True)
    df = download_csv(force=force)
    if not df.empty:
        process_data(df)
    
    squads = build_synthetic_squads()
    with open(OUT_SQUAD, "w") as f:
        json.dump(squads, f, indent=2, ensure_ascii=False)
    logger.info(f"Squad data saved to {OUT_SQUAD}")

if __name__ == "__main__":
    main()
