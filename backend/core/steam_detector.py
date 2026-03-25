def detect_steam(db, match_id: int, bookmaker: str, current_home_odds: float, current_away_odds: float, market: str = "h2h") -> bool:
    """
    Checks if there's been a significant drop (>5%) in odds from the opening line
    for a given match and bookmaker.
    
    Returns True if steam is detected.
    """
    from db.models import OddsHistory
    
    # Get the earliest recorded odds for this match and bookmaker (the "opening line")
    opening_odds = (
        db.query(OddsHistory)
        .filter(OddsHistory.match_id == match_id)
        .filter(OddsHistory.bookmaker == bookmaker)
        .filter(OddsHistory.market == market)
        .order_by(OddsHistory.timestamp.asc())
        .first()
    )
    
    if not opening_odds:
        return False
        
    # Check for > 5% drop in Home or Away odds
    if current_home_odds and current_home_odds > 0 and opening_odds.home_odds and opening_odds.home_odds > 0:
        home_drop = (opening_odds.home_odds - current_home_odds) / opening_odds.home_odds
        if home_drop > 0.05:
            return True
            
    if current_away_odds and current_away_odds > 0 and opening_odds.away_odds and opening_odds.away_odds > 0:
        away_drop = (opening_odds.away_odds - current_away_odds) / opening_odds.away_odds
        if away_drop > 0.05:
            return True
            
    return False
