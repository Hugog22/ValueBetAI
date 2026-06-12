import httpx
from core.config import settings
url = "https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds"
params = {
    "apiKey": settings.ODDS_API_KEY,
    "regions": "eu,uk",
    "markets": "h2h,totals",
    "oddsFormat": "decimal",
    "bookmakers": "pinnacle,bet365,williamhill,betway",
}
print("Testing The Odds API for World Cup...")
try:
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Requests Used: {response.headers.get('x-requests-used')}")
            print(f"Requests Remaining: {response.headers.get('x-requests-remaining')}")
            events = response.json()
            print(f"Events found: {len(events)}")
            if events:
                print(f"First event: {events[0]['home_team']} vs {events[0]['away_team']}")
        else:
            print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
