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

def get_worldcup_odds_api_football(season: int | None = None):
    """
    Fetch odds for the World Cup using API-Football instead of The Odds API.
    Uses league_id=1 which is World Cup in API-Football.
    """
    if season is None:
        season = get_current_season()
        
    url = f"{API_SPORTS_BASE_URL}/odds"
    params = {
        "league": 1,
        "season": season,
        "bookmaker": 8 # Bet365
    }
    with httpx.Client() as client:
        response = client.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json().get('response', [])

def get_worldcup_fixtures_api_football(season: int | None = None):
    """Fetch upcoming World Cup fixtures to get fixture IDs and team names."""
    if season is None:
        season = 2026 # Force 2026 since we only care about World Cup 2026
    url = f"{API_SPORTS_BASE_URL}/fixtures"
    params = {
        "league": 1,
        "season": season
    }
    with httpx.Client() as client:
        response = client.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        return response.json().get('response', [])
