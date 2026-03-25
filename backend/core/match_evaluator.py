import random
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Match, Odds, MarketOdds, OddsHistory

# We will need the predictor. To avoid circularity with main.py, 
# we'll expect it to be passed or we'll define a way to get it.
# For now, let's assume it's passed or imported from a neutral place.

_ODDS_POOL = [
    {"home": 1.55, "draw": 3.90, "away": 5.50, "over25": 2.05, "under25": 1.75, "over_corners": 1.85, "under_corners": 1.95},
    {"home": 2.10, "draw": 3.40, "away": 3.20, "over25": 1.70, "under25": 2.15, "over_corners": 1.90, "under_corners": 1.90},
    {"home": 2.30, "draw": 3.10, "away": 3.25, "over25": 1.90, "under25": 1.90, "over_corners": 1.80, "under_corners": 2.00},
    {"home": 1.80, "draw": 3.50, "away": 4.20, "over25": 1.80, "under25": 2.00, "over_corners": 1.95, "under_corners": 1.85},
    {"home": 2.00, "draw": 3.50, "away": 3.60, "over25": 1.72, "under25": 2.10, "over_corners": 2.05, "under_corners": 1.75},
    {"home": 3.80, "draw": 3.50, "away": 1.95, "over25": 1.85, "under25": 1.95, "over_corners": 1.88, "under_corners": 1.92},
    {"home": 2.20, "draw": 3.20, "away": 3.40, "over25": 2.10, "under25": 1.72, "over_corners": 2.10, "under_corners": 1.72},
    {"home": 2.15, "draw": 3.00, "away": 3.80, "over25": 2.50, "under25": 1.52, "over_corners": 1.95, "under_corners": 1.85},
    {"home": 1.85, "draw": 3.40, "away": 4.50, "over25": 2.20, "under25": 1.65, "over_corners": 1.83, "under_corners": 1.97},
    {"home": 2.25, "draw": 3.10, "away": 3.40, "over25": 2.40, "under25": 1.55, "over_corners": 1.90, "under_corners": 1.90},
    {"home": 2.70, "draw": 3.10, "away": 2.70, "over25": 2.35, "under25": 1.58, "over_corners": 1.77, "under_corners": 2.03},
    {"home": 1.70, "draw": 3.60, "away": 5.00, "over25": 1.95, "under25": 1.85, "over_corners": 1.92, "under_corners": 1.88},
]

def _get_odds(match: Match, db: Session | None = None) -> dict:
    if db is not None:
        h2h = db.query(Odds).filter(Odds.match_id == match.id, Odds.market == "h2h").order_by(Odds.timestamp.desc()).first()
        ou25 = db.query(Odds).filter(Odds.match_id == match.id, Odds.market == "totals_2.5").order_by(Odds.timestamp.desc()).first()
        if h2h:
            pool = _ODDS_POOL[match.id % len(_ODDS_POOL)]
            return {
                "home": float(h2h.home_odds), "draw": float(h2h.draw_odds), "away": float(h2h.away_odds),
                "over25": float(ou25.home_odds) if ou25 else pool["over25"],
                "under25": float(ou25.away_odds) if ou25 else pool["under25"],
                "over_corners": pool.get("over_corners", 1.90), "under_corners": pool.get("under_corners", 1.90),
                "_source": f"{h2h.bookmaker}_live",
            }
    pool = _ODDS_POOL[match.id % len(_ODDS_POOL)]
    return {**pool, "_source": "mock"}

def _build_match_features(match: Match) -> dict:
    rng = random.Random(match.id)
    archetype = match.id % 3
    if archetype == 0:
        hxf, hxa, hg, hp = 2.0, 1.0, 2.1, 2.3
        axf, axa, ag, ap = 0.9, 1.8, 1.0, 1.1
        h_opp_pts, h_opp_xgag = 1.1, 1.7
        a_opp_pts, a_opp_xgag = 2.3, 1.0
    elif archetype == 1:
        hxf, hxa, hg, hp = 1.3, 1.3, 1.3, 1.5
        axf, axa, ag, ap = 1.3, 1.3, 1.3, 1.4
        h_opp_pts, h_opp_xgag = 1.5, 1.3
        a_opp_pts, a_opp_xgag = 1.5, 1.2
    else:
        hxf, hxa, hg, hp = 0.9, 1.8, 1.0, 1.1
        axf, axa, ag, ap = 2.0, 1.0, 2.1, 2.3
        h_opp_pts, h_opp_xgag = 2.3, 1.0
        a_opp_pts, a_opp_xgag = 1.1, 1.7
    eps = 1e-3
    return {
        "home_xg_for_avg5": hxf, "home_xg_ag_avg5": hxa, "home_goals_avg5": hg, "home_pts_avg5": hp,
        "away_xg_for_avg5": axf, "away_xg_ag_avg5": axa, "away_goals_avg5": ag, "away_pts_avg5": ap,
        "home_opp_pts_avg5": h_opp_pts, "home_opp_xgag_avg5": h_opp_xgag,
        "away_opp_pts_avg5": a_opp_pts, "away_opp_xgag_avg5": a_opp_xgag,
        "home_xg_adj": round(hxf / (h_opp_xgag + eps), 2), "away_xg_adj": round(axf / (a_opp_xgag + eps), 2),
        "xg_diff": round(hxf - axf, 2), "form_diff": round(hp - ap, 2),
        "opp_diff": round(h_opp_pts - a_opp_pts, 2),
        "xg_adj_diff": round(hxf / (h_opp_xgag + eps) - axf / (a_opp_xgag + eps), 2),
        "rest_days_home": rng.randint(3, 7), "rest_days_away": rng.randint(3, 7),
        "home_corners_avg5": 5.0, "away_corners_avg5": 4.5, "home_corners_ag5": 4.5, "away_corners_ag5": 5.0,
        "_home_xg_avg5": hxf, "_away_xg_avg5": axf, "_home_goals_avg5": hg, "_away_goals_avg5": ag,
        "_home_conceded_avg5": hxa, "_away_conceded_avg5": axa,
        "_rest_days_home": rng.randint(4, 7), "_rest_days_away": rng.randint(4, 7),
        "_h2h_last5": "2W-1D-2L", "_home_opp_pts": h_opp_pts, "_away_opp_pts": a_opp_pts,
        "_home_xg_adj": round(hxf / (h_opp_xgag + eps), 2), "_away_xg_adj": round(axf / (a_opp_xgag + eps), 2),
    }

def _calculate_risk(prob: float) -> dict:
    if prob > 0.55:
        return {"level": "BAJO", "badge": "🟢 BAJO", "bgClass": "bg-green-600 text-white font-bold"}
    elif prob >= 0.35:
        return {"level": "MEDIO", "badge": "🟡 MEDIO", "bgClass": "bg-yellow-400 text-black font-bold"}
    elif prob >= 0.15:
        return {"level": "ALTO", "badge": "🟠 ALTO", "bgClass": "bg-orange-500 text-white font-bold"}
    else:
        return {"level": "LOTERÍA", "badge": "🔴 LOTERÍA", "bgClass": "bg-red-600 text-white font-bold"}

def _fractional_kelly(prob: float, odds: float, fraction: float = 0.25) -> int:
    if odds <= 1.0 or prob <= 0: return 1
    b = odds - 1.0
    kelly_pct = (b * prob - (1.0 - prob)) / b
    if kelly_pct <= 0: return 1
    return max(1, min(10, int((kelly_pct * fraction) * 200)))

def _evaluate_match(match: Match, predictor, db: Session | None = None) -> dict:
    home, away = match.home_team.name, match.away_team.name
    all_f = _build_match_features(match)
    odds = _get_odds(match, db)
    source = odds.pop("_source", "mock")
    predict_f = {k: v for k, v in all_f.items() if not k.startswith("_")}
    ctx = {k[1:]: v for k, v in all_f.items() if k.startswith("_")}
    pred = predictor.predict_match(predict_f)
    
    candidates = []
    eps = 1e-6
    for outcome, label in [("home", "Victoria Local"), ("draw", "Empate"), ("away", "Victoria Visitante")]:
        book, fair = float(odds[outcome]), float(pred["fair_odds_1x2"][outcome])
        ev = (book / (fair + eps) - 1) * 100
        candidates.append({
            "market": "1x2", "outcome": outcome, "label": label,
            "probability": float(pred["probabilities"][outcome]),
            "bookmaker_odds": book, "fair_odds": round(fair, 2), "ev": round(ev, 2), "is_value": ev > 0,
            "bookmaker_implied_prob": round(1.0 / book, 4) if book > 0 else 0
        })
    
    # Simple O/U
    prob_o = pred["prob_over25"]
    for side, p, label, key in [("over", prob_o, "Más de 2.5", "over25"), ("under", 1-prob_o, "Menos de 2.5", "under25")]:
        book, fair = float(odds[key]), float(pred["fair_odds_ou25"][side])
        ev = (book / (fair + eps) - 1) * 100
        candidates.append({
            "market": "ou25", "outcome": side, "label": label, "probability": round(p, 4), 
            "bookmaker_odds": book, "fair_odds": round(fair, 2), "ev": round(ev, 2), "is_value": ev > 0,
            "bookmaker_implied_prob": round(1.0 / book, 4) if book > 0 else 0
        })

    for c in candidates:
        c["risk"] = _calculate_risk(c["probability"])
        c["stake"] = _fractional_kelly(c["probability"], c["bookmaker_odds"])
    
    candidates.sort(key=lambda x: x["ev"], reverse=True)
    best = candidates[0]
    
    return {
        "id": match.id, "homeTeam": home, "awayTeam": away, "date": match.date.isoformat() + "Z" if match.date else None,
        "status": match.status, "oddsSource": source, "bestPick": {
            "label": best["label"], "market": best["market"], "outcome": best["outcome"],
            "bookmakerOdds": best["bookmaker_odds"], "fairOdds": best["fair_odds"], "ev": best["ev"],
            "probability": round(best["probability"] * 100, 1), "isValueBet": best["is_value"],
            "risk": best["risk"], "stake": best["stake"]
        },
        "allCandidates": candidates,
        "topPicks": candidates[:3],
        "justification": f"{home} vs {away} match evaluation.",
        "rivalContext": {"homeOppPts": all_f.get("_home_opp_pts"), "awayOppPts": all_f.get("_away_opp_pts")}
    }
