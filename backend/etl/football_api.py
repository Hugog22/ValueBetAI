import httpx
from core.config import settings, get_current_season

API_SPORTS_BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    "x-rapidapi-host": "v3.football.api-sports.io",
    "x-apisports-key": settings.API_SPORTS_KEY
}

def get_laliga_fixtures(season: int | None = None, next_matches: int = 10):
    """Fetch upcoming LaLiga fixtures (League ID for LaLiga is 140)"""
    if season is None:
        season = get_current_season()
    url = f"{API_SPORTS_BASE_URL}/fixtures"
    params = {
        "league": 140, # LaLiga ID is generally 140 in API-Sports
        "season": season,
        "next": next_matches
    }
    with httpx.Client() as client:
        response = client.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json().get('response', [])

def get_match_statistics(fixture_id: int):
    """Fetch detailed statistics for a specific fixture"""
    url = f"{API_SPORTS_BASE_URL}/fixtures/statistics"
    params = {"fixture": fixture_id}
    with httpx.Client() as client:
        response = client.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json().get('response', [])
