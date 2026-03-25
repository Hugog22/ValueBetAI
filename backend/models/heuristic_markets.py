import math

def evaluate_secondary_markets(features: dict, pred_probs: dict, book_odds: dict, calculate_risk_fn, fractional_kelly_fn) -> list[dict]:
    """
    Heuristic sub-models for secondary markets based on core XGBoost predictions 
    and historical API-Football rolling averages.
    """
    candidates = []
    eps = 1e-6
    
    p_home = pred_probs.get("home", 0.33)
    p_draw = pred_probs.get("draw", 0.33)
    p_away = pred_probs.get("away", 0.33)
    
    # 1. Double Chance
    p_1x = p_home + p_draw
    p_x2 = p_draw + p_away
    p_12 = p_home + p_away
    
    # 2. Draw No Bet (DNB)
    # P(Home | Not Draw) = P(Home) / (P(Home) + P(Away))
    p_dnb_home = p_home / (p_home + p_away + eps)
    p_dnb_away = p_away / (p_home + p_away + eps)
    
    # 3. BTTS (Both Teams To Score)
    h_xg = features.get("home_xg_for_avg5", 1.45)
    a_xg = features.get("away_xg_for_avg5", 1.10)
    p_home_score = 1 - math.exp(-h_xg)
    p_away_score = 1 - math.exp(-a_xg)
    p_btts_yes = p_home_score * p_away_score
    p_btts_no = 1.0 - p_btts_yes
    
    market_probs = {
        "double_chance": {
            "Home/Draw": p_1x,
            "Draw/Away": p_x2,
            "Home/Away": p_12,
        },
        "draw_no_bet": {
            "Home": p_dnb_home,
            "Away": p_dnb_away,
        },
        "btts": {
            "Yes": p_btts_yes,
            "No": p_btts_no,
        }
    }
    
    for mkey, outcomes in market_probs.items():
        if mkey in book_odds:
            book_market = book_odds[mkey]
            for outcome_name, p_fair in outcomes.items():
                book_price = next((o["price"] for o in book_market["outcomes"] if o["name"] == outcome_name), 0)
                if book_price > 1.0:
                    fair_odds = 1.0 / (p_fair + eps)
                    ev = (book_price / fair_odds - 1.0) * 100
                    
                    if ev > 0:
                        candidates.append({
                            "market": mkey,
                            "outcome": outcome_name,
                            "label": f"{mkey.upper()} - {outcome_name}",
                            "probability": float(p_fair),
                            "fair_odds": round(fair_odds, 2),
                            "bookmaker_odds": float(book_price),
                            "ev": round(ev, 2),
                            "is_value": True,
                            "risk": calculate_risk_fn(float(p_fair)),
                            "stake": fractional_kelly_fn(float(p_fair), float(book_price))
                        })
    
    return sorted(candidates, key=lambda c: c["ev"], reverse=True)
