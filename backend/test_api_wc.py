import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

api_keys = os.environ.get("ODDS_API_KEY", "")
if not api_keys:
    print("No ODDS_API_KEY found")
    sys.exit(1)

api_key = api_keys.split(",")[0].strip()

url = "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds"
params = {
    "apiKey": api_key,
    "regions": "eu,uk",
    "markets": "h2h,totals,spreads",
    "oddsFormat": "decimal",
}

print(f"Fetching from {url}...")
resp = httpx.get(url, params=params)
print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    import json
    data = resp.json()
    if len(data) > 0:
        totals_points = set()
        for match in data:
            for bm in match.get('bookmakers', []):
                for m in bm.get('markets', []):
                    if m['key'] == 'totals':
                        for outcome in m.get('outcomes', []):
                            if 'point' in outcome:
                                totals_points.add(outcome['point'])
        print(f"Líneas de Totales disponibles en todos los partidos: {sorted(list(totals_points))}")
else:
    print(resp.text)
