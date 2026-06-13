import logging
import httpx
from core.config import settings
from datetime import datetime

logger = logging.getLogger(__name__)

ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4/sports"
LALIGA_SPORT = "soccer_spain_la_liga"

def fetch_with_rotation(url: str, params: dict, timeout: int = 30) -> httpx.Response:
    """
    Wrapper around httpx.get that rotates through available ODDS_API_KEYS
    if it encounters a 429 (Too Many Requests) or 401 (Unauthorized).
    """
    keys = [k.strip() for k in getattr(settings, "ODDS_API_KEY", "").split(",") if k.strip()]
    if not keys:
        raise ValueError("No API keys found in ODDS_API_KEY")
        
    last_response = None
    for key in keys:
        params["apiKey"] = key
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params)
                if response.status_code in (429, 401):
                    logger.warning(f"API Key starting with {key[:4]}... failed with {response.status_code}. Rotating to next key.")
                    last_response = response
                    continue
                # For any other status code, we return the response
                # (even if it's 422 or 500, we let the caller handle it)
                return response
        except httpx.RequestError as e:
            logger.warning(f"Request failed with key {key[:4]}... error: {e}. Rotating...")
            continue
            
    # If all keys failed (or exhausted), return the last response to let the caller raise/handle
    if last_response is not None:
        return last_response
    raise RuntimeError("fetch_with_rotation failed: No valid keys or all requests failed.")
def get_laliga_odds():
    """Fetch h2h odds for LaLiga — legacy single-market call."""
    return get_laliga_odds_all_markets(markets=["h2h"])


def get_laliga_odds_all_markets(markets: list[str] | None = None) -> list[dict]:
    """
    Fetch odds for multiple markets from The Odds API for La Liga.

    - Uses regions=eu,uk so Bet365 UK odds are also captured.
    - Filters STRICTLY by bet365.
    - markets: ["h2h", "totals"] by default. btts excluded (422 on free tier).

    Returns the raw API response list (one entry per event).
    """
    if markets is None:
        markets = ["h2h", "totals", "spreads"]

    url = f"{ODDS_API_BASE_URL}/{LALIGA_SPORT}/odds"
    params = {
        "apiKey":     "",  # Injected by fetch_with_rotation
        "regions":    "eu,uk",
        "markets":    ",".join(markets),
        "oddsFormat": "decimal",
    }
    response = fetch_with_rotation(url, params=params)
    response.raise_for_status()
    return response.json()




def pick_best_bookmaker(bookmakers: list[dict]) -> tuple[str, dict]:
    if not bookmakers:
        return "", {}
    for b in bookmakers:
        if b.get("key") == "pinnacle":
            return "pinnacle", b
    return bookmakers[0].get("key", ""), bookmakers[0]

def detect_super_boosts(odds_data: list[dict]) -> list[dict]:
    """
    Detect value boosts: events where the best bookmaker's h2h implied
    probability < 1.0 (positive-EV signal before margin extraction).
    """
    boosts = []
    for match in odds_data:
        bm_key, bookmaker = pick_best_bookmaker(match.get("bookmakers", []))
        if not bookmaker:
            continue
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                implied_prob = sum(
                    1.0 / float(outcome["price"])
                    for outcome in market["outcomes"]
                    if float(outcome["price"]) > 0
                )
                if implied_prob < 1.0:
                    boosts.append({
                        "match":        match["home_team"] + " vs " + match["away_team"],
                        "bookmaker":    bm_key,
                        "implied_prob": round(implied_prob, 4),
                        "raw":          market,
                    })
    return boosts
