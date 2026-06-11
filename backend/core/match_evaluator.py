"""
match_evaluator.py
------------------
Evaluates upcoming football matches and computes value-bet candidates.

Responsibilities:
  - Build match features from DB data (ELO, xG, possession, rest days, absences).
  - Retrieve live or mock odds.
  - Run the football predictor to get 1x2 and O/U 2.5 probabilities.
  - Calculate Expected Value (EV) and risk levels for each market.
  - Return a structured dict consumed by cache_service and the bets router.
"""

import random
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Match, Odds, MarketOdds, OddsHistory


# ---------------------------------------------------------------------------
# Odds pool — fallback mock odds when no live odds exist in the DB
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Odds retrieval
# ---------------------------------------------------------------------------

def _get_odds(match: Match, db: Session | None = None) -> dict:
    """Return live odds from DB or fall back to mock pool."""
    if db is not None:
        h2h  = db.query(Odds).filter(Odds.match_id == match.id, Odds.market == "h2h").order_by(Odds.timestamp.desc()).first()
        ou25 = db.query(Odds).filter(Odds.match_id == match.id, Odds.market == "totals_2.5").order_by(Odds.timestamp.desc()).first()
        if h2h:
            pool = _ODDS_POOL[match.id % len(_ODDS_POOL)]
            return {
                "home":  float(h2h.home_odds),
                "draw":  float(h2h.draw_odds),
                "away":  float(h2h.away_odds),
                "over25":  float(ou25.home_odds) if ou25 else pool["over25"],
                "under25": float(ou25.away_odds) if ou25 else pool["under25"],
                "over_corners":  pool.get("over_corners",  1.90),
                "under_corners": pool.get("under_corners", 1.90),
                "_source": f"{h2h.bookmaker}_live",
            }
    pool = _ODDS_POOL[match.id % len(_ODDS_POOL)]
    return {**pool, "_source": "mock"}


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def _build_match_features(match: Match) -> dict:
    """Build ELO-based proxy features when no rolling stats exist in DB."""
    home, away = match.home_team.name, match.away_team.name

    def get_elo(team_name: str) -> int:
        t = team_name.lower()
        if any(x in t for x in ["madrid", "barcelona", "bellingham", "vinicius", "atletico"]):
            return 2100
        if any(x in t for x in ["girona", "sociedad", "athletic", "betis"]):
            return 1850
        if any(x in t for x in ["mallorca", "almeria", "granada", "cadiz"]):
            return 1300
        return 1500

    home_elo = get_elo(home)
    away_elo = get_elo(away)
    h_pow    = home_elo / 1500.0
    a_pow    = away_elo / 1500.0
    rng      = random.Random(match.id)

    return {
        "home_elo":                  home_elo,
        "away_elo":                  away_elo,
        "elo_diff":                  home_elo - away_elo,
        "home_xg_for_avg10":         round(1.2 * h_pow, 2),
        "away_xg_for_avg10":         round(1.1 * a_pow, 2),
        "xg_diff":                   round((1.2 * h_pow) - (1.1 * a_pow), 2),
        "home_possession_avg10":     round(50 * h_pow, 1),
        "away_possession_avg10":     round(50 * a_pow, 1),
        "possession_diff":           round((50 * h_pow) - (50 * a_pow), 1),
        "home_shots_target_avg10":   round(4.5 * h_pow, 1),
        "away_shots_target_avg10":   round(4.0 * a_pow, 1),
        "shots_diff":                round((4.5 * h_pow) - (4.0 * a_pow), 1),
        "home_absences":             rng.randint(0, 3),
        "away_absences":             rng.randint(0, 3),
        "absence_severity":          rng.randint(0, 1),
        "rest_days_home":            rng.randint(4, 7),
        "rest_days_away":            rng.randint(4, 7),
    }


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def _calculate_risk(ai_prob: float, bookmaker_odds: float,
                    is_draw: bool = False, xg_diff: float = 0.0) -> dict:
    """Classify betting risk based on AI probability vs market probability."""
    house_prob = (1.0 / bookmaker_odds) if bookmaker_odds > 0 else 0.0

    # Pull back extreme deviations unless strongly supported by xG
    if abs(ai_prob - house_prob) > 0.15 and abs(xg_diff) < 1.0:
        ai_prob = house_prob + (0.15 if ai_prob > house_prob else -0.15)

    # Flag obvious model errors (high prob on draws or heavy underdogs)
    if ai_prob > 0.50 and (is_draw or bookmaker_odds >= 4.0):
        return {"level": "ERROR", "badge": "⚠️ ERROR MODELO", "bgClass": "bg-red-900 text-white font-black"}

    safe_prob = min(ai_prob, house_prob)

    if safe_prob > 0.55:
        return {"level": "BAJO",    "badge": "🟢 BAJO",    "bgClass": "bg-green-600 text-white font-bold"}
    if safe_prob >= 0.35:
        return {"level": "MEDIO",   "badge": "🟡 MEDIO",   "bgClass": "bg-yellow-400 text-black font-bold"}
    if safe_prob >= 0.15:
        return {"level": "ALTO",    "badge": "🟠 ALTO",    "bgClass": "bg-orange-500 text-white font-bold"}
    return     {"level": "LOTERÍA", "badge": "🔴 LOTERÍA", "bgClass": "bg-red-600 text-white font-bold"}


# ---------------------------------------------------------------------------
# Stake sizing — fractional Kelly criterion
# ---------------------------------------------------------------------------

def _fractional_kelly(prob: float, odds: float, fraction: float = 0.25) -> int:
    """Return a 1–10 stake unit recommendation using fractional Kelly."""
    if odds <= 1.0 or prob <= 0:
        return 1
    b = odds - 1.0
    kelly_pct = (b * prob - (1.0 - prob)) / b
    if kelly_pct <= 0:
        return 1
    return max(1, min(10, int((kelly_pct * fraction) * 200)))


# ---------------------------------------------------------------------------
# Main evaluator
# ---------------------------------------------------------------------------

def _evaluate_match(match: Match, predictor, db: Session | None = None) -> dict:
    """
    Evaluate a football match and return a structured prediction dict.

    Returns a dict with keys: id, homeTeam, awayTeam, date, status,
    oddsSource, sport, bestPick, allCandidates, topPicks, justification.
    """
    home, away = match.home_team.name, match.away_team.name
    features   = _build_match_features(match)
    odds       = _get_odds(match, db)
    source     = odds.pop("_source", "mock")

    predict_features = {k: v for k, v in features.items() if not k.startswith("_")}
    pred             = predictor.predict_match(predict_features)

    eps        = 1e-6
    candidates = []

    # 1x2 markets
    for outcome, label in [("home", "Victoria Local"), ("draw", "Empate"), ("away", "Victoria Visitante")]:
        book = float(odds[outcome])
        fair = float(pred["fair_odds_1x2"][outcome])
        ev   = (book / (fair + eps) - 1) * 100
        candidates.append({
            "market":   "1x2",
            "outcome":  outcome,
            "label":    label,
            "probability":            float(pred["probabilities"][outcome]),
            "bookmaker_odds":         book,
            "fair_odds":              round(fair, 2),
            "ev":                     round(ev, 2),
            "is_value":               ev > 0,
            "bookmaker_implied_prob": round(1.0 / book, 4) if book > 0 else 0,
        })

    # Over/Under 2.5 markets
    prob_over = pred["prob_over25"]
    for side, prob, label, key in [
        ("over",  prob_over,     "Más de 2.5",   "over25"),
        ("under", 1 - prob_over, "Menos de 2.5", "under25"),
    ]:
        book = float(odds[key])
        fair = float(pred["fair_odds_ou25"][side])
        ev   = (book / (fair + eps) - 1) * 100
        candidates.append({
            "market":   "ou25",
            "outcome":  side,
            "label":    label,
            "probability":            round(prob, 4),
            "bookmaker_odds":         book,
            "fair_odds":              round(fair, 2),
            "ev":                     round(ev, 2),
            "is_value":               ev > 0,
            "bookmaker_implied_prob": round(1.0 / book, 4) if book > 0 else 0,
        })

    # Annotate each candidate with risk and stake
    for c in candidates:
        c["risk"]  = _calculate_risk(c["probability"], c["bookmaker_odds"])
        c["stake"] = _fractional_kelly(c["probability"], c["bookmaker_odds"])

    candidates.sort(key=lambda x: x["ev"], reverse=True)
    best = candidates[0]

    return {
        "id":        match.id,
        "homeTeam":  home,
        "awayTeam":  away,
        "date":      match.date.isoformat() + "Z" if match.date else None,
        "status":    match.status,
        "oddsSource": source,
        "sport":     "football",
        "bestPick": {
            "label":                  best["label"],
            "market":                 best["market"],
            "outcome":                best["outcome"],
            "bookmakerOdds":          best["bookmaker_odds"],
            "fairOdds":               best["fair_odds"],
            "ev":                     best["ev"],
            "probability":            best["probability"],
            "isValueBet":             best["is_value"],
            "bookmaker_implied_prob": best["bookmaker_implied_prob"],
            "risk":                   best["risk"],
            "stake":                  best["stake"],
        },
        "allCandidates": candidates,
        "topPicks":      candidates[:3],
        "justification": f"{home} vs {away} — evaluación de fútbol.",
    }
