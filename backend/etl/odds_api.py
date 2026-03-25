import httpx
from core.config import settings
from datetime import datetime

ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4/sports"
LALIGA_SPORT = "soccer_spain_la_liga"

# Priority order for bookmaker fallback
BOOKMAKER_PRIORITY = ["bet365", "pinnacle", "williamhill", "bwin", "unibet", "betfair"]


def get_laliga_odds():
    """Fetch h2h odds for LaLiga — legacy single-market call."""
    return get_laliga_odds_all_markets(markets=["h2h"])


def get_laliga_odds_all_markets(markets: list[str] | None = None) -> list[dict]:
    """
    Fetch odds for multiple markets from The Odds API for La Liga.

    - Uses regions=eu,uk so Bet365 UK odds are also captured.
    - Does NOT filter by bookmaker — we fetch all available bookmakers
      and apply priority fallback (bet365 → pinnacle → williamhill → bwin)
      in the flush_odds pipeline.
    - markets: ["h2h", "totals"] by default. btts excluded (422 on free tier).

    Returns the raw API response list (one entry per event).
    """
    if markets is None:
        markets = ["h2h", "totals", "spreads"]

    url = f"{ODDS_API_BASE_URL}/{LALIGA_SPORT}/odds"
    params = {
        "apiKey":     settings.ODDS_API_KEY,
        "regions":    "eu,uk",          # eu + uk to catch Bet365 UK listings
        "markets":    ",".join(markets),
        "bookmakers": "pinnacle,bet365,williamhill,betway",
        "oddsFormat": "decimal",
    }
    with httpx.Client(timeout=30) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def pick_best_bookmaker(bookmakers: list[dict]) -> tuple[str, dict] | tuple[None, None]:
    """
    From a list of bookmaker dicts (from the API response), return the
    (bookmaker_key, bookmaker_dict) with the highest priority.

    Priority: bet365 → pinnacle → williamhill → bwin → unibet → betfair → first available
    """
    bm_by_key = {bm["key"]: bm for bm in bookmakers}

    for preferred in BOOKMAKER_PRIORITY:
        if preferred in bm_by_key:
            return preferred, bm_by_key[preferred]

    # Fallback: first available
    if bm_by_key:
        key = next(iter(bm_by_key))
        return key, bm_by_key[key]

    return None, None


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
                    1.0 / outcome["price"]
                    for outcome in market["outcomes"]
                    if outcome["price"] > 0
                )
                if implied_prob < 1.0:
                    boosts.append({
                        "match":        match["home_team"] + " vs " + match["away_team"],
                        "bookmaker":    bm_key,
                        "implied_prob": round(implied_prob, 4),
                        "raw":          market,
                    })
    return boosts
