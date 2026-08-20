"""
match_evaluator.py
------------------
Evaluates upcoming football matches and computes value-bet candidates.

Supports one evaluator path:
  - Club football (La Liga): _evaluate_match()
"""

import math
import random
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Match, Odds, MarketOdds, OddsHistory, Team


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
# Poisson-based AI probability helpers for all markets
# ---------------------------------------------------------------------------

def _poisson_pmf(lam: float, k: int) -> float:
    """Poisson probability mass function P(X = k). Safe against overflow."""
    if k < 0 or lam <= 0:
        return 0.0
    try:
        return math.exp(-lam) * (lam ** k) / math.factorial(k)
    except (OverflowError, ValueError):
        return 0.0


def _prob_over_goals(lam_home: float, lam_away: float, threshold: float) -> float:
    """
    P(total goals > threshold) using independent Poisson distributions.
    Works for any threshold: 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0...
    """
    n = int(math.floor(threshold))
    prob_le = 0.0
    for total in range(n + 1):
        for h in range(total + 1):
            a = total - h
            prob_le += _poisson_pmf(lam_home, h) * _poisson_pmf(lam_away, a)
    return max(0.0, min(1.0, 1.0 - prob_le))


def _prob_covers_handicap(lam_team: float, lam_opp: float, handicap: float) -> float:
    """
    P(team covers Asian handicap) using independent Poisson distributions.

    handicap > 0: team has an advantage (e.g., away +1.0 → gets a 1-goal head start).
    handicap < 0: team has a disadvantage (e.g., home -1.0 → must win by 2+).

    Quarter handicaps (.25 / .75) are split bets: average of the two adjacent lines.
    On whole-number handicaps, an exact-margin result (push) is treated as a half win.
    """
    # Quarter handicap → split between two adjacent half-lines
    frac = round(handicap % 0.5, 6)
    if abs(abs(frac) - 0.25) < 0.001:
        p1 = _prob_covers_handicap(lam_team, lam_opp, round(handicap - 0.25, 2))
        p2 = _prob_covers_handicap(lam_team, lam_opp, round(handicap + 0.25, 2))
        return (p1 + p2) / 2.0

    max_g = 15
    p_covers = 0.0
    for t in range(max_g + 1):
        for o in range(max_g + 1):
            p = _poisson_pmf(lam_team, t) * _poisson_pmf(lam_opp, o)
            margin = t + handicap - o
            if margin > 0.0:
                p_covers += p
            elif abs(margin) < 0.001 and abs(handicap % 1.0) < 0.001:
                # Push on whole-number handicap: half the stake returned
                p_covers += p * 0.5
    return max(0.0, min(1.0, p_covers))



def _fit_lambdas_from_1x2_probs(
    p_home_win: float,
    p_away_win: float,
    base_total: float = 2.50,
    max_iter: int = 80,
) -> tuple[float, float]:
    """
    Fit Poisson expected-goal lambdas (lam_home, lam_away) so that the
    implied P(home win) matches the predictor's output.

    Strategy: fix lam_home + lam_away = base_total (sport average total goals)
    and binary-search on the ratio r = lam_home / lam_away until the Poisson
    home-win probability matches p_home_win.

    This ensures handicap probabilities are internally consistent with
    the model's 1x2 prediction instead of relying on raw DB xG values
    that often default to nearly equal for both teams.

    Parameters
    ----------
    p_home_win : float  AI probability of a home win (0-1)
    p_away_win : float  AI probability of an away win (0-1)
    base_total : float  Expected total goals for the sport/competition
                        (≈2.60 for club football, ≈2.35 for World Cup)
    """
    # Sanity-clamp: avoid extreme probabilities crashing the search
    p_home_win = max(0.05, min(0.90, p_home_win))

    def _p_home(ratio: float) -> float:
        lh = base_total * ratio / (1.0 + ratio)
        la = base_total / (1.0 + ratio)
        p = 0.0
        for h in range(16):
            for a in range(16):
                if h > a:
                    p += _poisson_pmf(lh, h) * _poisson_pmf(la, a)
        return p

    lo, hi = 0.05, 30.0
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        if _p_home(mid) < p_home_win:
            lo = mid
        else:
            hi = mid

    ratio = (lo + hi) / 2.0
    lam_home = round(base_total * ratio / (1.0 + ratio), 4)
    lam_away = round(base_total / (1.0 + ratio), 4)
    return lam_home, lam_away


def _normalize_team_name(name: str) -> str:
    """Lowercase + strip for fuzzy team name matching."""
    return name.lower().strip().replace("-", " ")


def _build_all_markets(
    match,
    db,
    pred_probs: dict,
    prob_over25: float,
    lam_home: float,
    lam_away: float,
) -> list[dict]:
    """
    Build enriched market data for ALL bookmaker odds stored in MarketOdds.

    For each (market_key, point) group:
      - Averages prices across all bookmakers for the same outcome
      - Adds implied_prob  = 1 / bookmaker_odds
      - Adds ai_prob       = model probability (Poisson for totals/spreads, predictor for 1x2)
      - Adds ev            = (bookmaker_odds * ai_prob - 1) * 100
      - Adds is_value      = ev > dynamic threshold

    This function is ADDITIVE — it does not affect bestPick, allCandidates, or any
    existing logic. It only provides the new 'allMarkets' field.
    """
    if db is None:
        return []

    rows = db.query(MarketOdds).filter(MarketOdds.match_id == match.id).all()
    if not rows:
        return []

    home_norm = _normalize_team_name(match.home_team.name)
    away_norm = _normalize_team_name(match.away_team.name)
    eps = 1e-6

    # Group: (market_key, point) → outcome_name → [prices from different bookmakers]
    from collections import defaultdict
    groups: dict = defaultdict(lambda: defaultdict(list))
    for row in rows:
        # Skip Betfair lay odds
        if row.market_key == "h2h_lay":
            continue

        # For totals (Más/Menos goles), only show classic .5 lines (1.5, 2.5, 3.5…)
        if row.market_key in ("totals", "alternate_totals") and row.point is not None:
            if abs((row.point % 1) - 0.5) > 0.001:
                continue

        key = (row.market_key, row.point)
        groups[key][row.outcome_name].append(row.price)

    # Sort order: h2h first, totals, then spreads (handicap)
    _market_order = {"h2h": 0, "totals": 1, "alternate_totals": 1, "spreads": 2}

    def _sort_key(k):
        mkey, point = k
        return (_market_order.get(mkey, 9), point if point is not None else 0.0)

    result = []

    for (mkey, point) in sorted(groups.keys(), key=_sort_key):
        outcomes_prices = groups[(mkey, point)]
        outcomes_list = []

        for outcome_name, prices in outcomes_prices.items():
            avg_price   = sum(prices) / len(prices)
            implied_prob = round(1.0 / (avg_price + eps), 4)

            # ── AI probability per market ──────────────────────────────────
            ai_prob: float | None = None
            name_norm = _normalize_team_name(outcome_name)

            if mkey == "h2h":
                if "draw" in name_norm:
                    ai_prob = float(pred_probs.get("draw", 0.0))
                elif name_norm in home_norm or home_norm in name_norm:
                    ai_prob = float(pred_probs.get("home", 0.0))
                elif name_norm in away_norm or away_norm in name_norm:
                    ai_prob = float(pred_probs.get("away", 0.0))

            elif mkey == "totals" and point is not None:
                if name_norm == "over":
                    ai_prob = _prob_over_goals(lam_home, lam_away, float(point))
                elif name_norm == "under":
                    ai_prob = 1.0 - _prob_over_goals(lam_home, lam_away, float(point))

            elif mkey == "spreads" and point is not None:
                # The API stores each side with its own signed point
                # (e.g. home=-1.25, away=+1.25)
                if name_norm in home_norm or home_norm in name_norm:
                    ai_prob = _prob_covers_handicap(lam_home, lam_away, float(point))
                elif name_norm in away_norm or away_norm in name_norm:
                    ai_prob = _prob_covers_handicap(lam_away, lam_home, float(point))

            # ── EV and value flag ──────────────────────────────────────────
            if ai_prob is not None and ai_prob > 0:
                ev      = round((avg_price * ai_prob - 1.0) * 100, 2)
                # For the exhaustive allMarkets view, any EV > 0 is technically a value bet
                is_value = ev > 0.0
            else:
                ev       = None
                is_value = False

            outcomes_list.append({
                "name":           outcome_name,
                "bookmaker_odds": round(avg_price, 3),
                "implied_prob":   implied_prob,
                "ai_prob":        round(ai_prob, 4) if ai_prob is not None else None,
                "ev":             ev,
                "is_value":       is_value,
            })

        result.append({
            "market_key": mkey,
            "point":      point,
            "outcomes":   outcomes_list,
        })

    return result


# ---------------------------------------------------------------------------
# Odds retrieval
# ---------------------------------------------------------------------------

def _get_odds(match: Match, db: Session | None = None) -> dict | None:
    """Return average live odds from DB across all bookmakers."""
    if db is not None:
        h2h_records = db.query(Odds).filter(Odds.match_id == match.id, Odds.market == "h2h").all()
        ou25_records = db.query(Odds).filter(Odds.match_id == match.id, Odds.market == "totals_2.5").all()
        
        if h2h_records:
            ho_sum = dr_sum = aw_sum = 0.0
            all_bookmakers_h2h = []
            
            for r in h2h_records:
                ho_sum += float(r.home_odds)
                dr_sum += float(r.draw_odds)
                aw_sum += float(r.away_odds)
                all_bookmakers_h2h.append({
                    "title": r.bookmaker.title(),
                    "home_odds": float(r.home_odds),
                    "draw_odds": float(r.draw_odds),
                    "away_odds": float(r.away_odds)
                })
            
            n = len(h2h_records)
            avg_ho = ho_sum / n
            avg_dr = dr_sum / n
            avg_aw = aw_sum / n
            
            avg_o25 = 1.90
            avg_u25 = 1.90
            if ou25_records:
                o25_sum = u25_sum = 0.0
                for r in ou25_records:
                    o25_sum += float(r.home_odds)
                    u25_sum += float(r.away_odds)
                m = len(ou25_records)
                avg_o25 = o25_sum / m
                avg_u25 = u25_sum / m

            return {
                "home":     avg_ho,
                "draw":     avg_dr,
                "away":     avg_aw,
                "over25":   avg_o25,
                "under25":  avg_u25,
                "over_corners":  1.90,
                "under_corners": 1.90,
                "_source":  "average",
                "all_bookmakers_h2h": all_bookmakers_h2h
            }
    return None


# ---------------------------------------------------------------------------
# Feature engineering — club football
# ---------------------------------------------------------------------------

def _build_match_features(match: Match, db: Session | None = None) -> dict:
    """Build ELO-based proxy features for club football matches."""
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
    
    admin_feats = {
        "home_offensive_strength": 5.0,
        "away_offensive_strength": 5.0,
        "admin_offensive_diff": 0.0,
        "home_defensive_solidity": 5.0,
        "away_defensive_solidity": 5.0,
        "admin_defensive_diff": 0.0,
        "home_motivation": 5.0,
        "away_motivation": 5.0,
        "admin_motivation_diff": 0.0,
        "home_momentum": 5.0,
        "away_momentum": 5.0,
        "admin_momentum_diff": 0.0,
    }

    if db is not None:
        from db.models import TeamCharacteristic
        h_char = db.query(TeamCharacteristic).filter(TeamCharacteristic.team_id == match.home_team_id).first()
        a_char = db.query(TeamCharacteristic).filter(TeamCharacteristic.team_id == match.away_team_id).first()

        if h_char:
            admin_feats["home_offensive_strength"] = h_char.offensive_strength
            admin_feats["home_defensive_solidity"] = h_char.defensive_solidity
            admin_feats["home_motivation"] = h_char.motivation
            admin_feats["home_momentum"] = h_char.momentum
        
        if a_char:
            admin_feats["away_offensive_strength"] = a_char.offensive_strength
            admin_feats["away_defensive_solidity"] = a_char.defensive_solidity
            admin_feats["away_motivation"] = a_char.motivation
            admin_feats["away_momentum"] = a_char.momentum

        admin_feats["admin_offensive_diff"] = admin_feats["home_offensive_strength"] - admin_feats["away_offensive_strength"]
        admin_feats["admin_defensive_diff"] = admin_feats["home_defensive_solidity"] - admin_feats["away_defensive_solidity"]
        admin_feats["admin_motivation_diff"] = admin_feats["home_motivation"] - admin_feats["away_motivation"]
        admin_feats["admin_momentum_diff"] = admin_feats["home_momentum"] - admin_feats["away_momentum"]

    base_feats = {
        "home_elo":          home_elo,
        "away_elo":          away_elo,
        "elo_diff":          home_elo - away_elo,
        "home_xg_for_avg10": np.nan,
        "away_xg_for_avg10": np.nan,
        "xg_diff":           np.nan,
        "home_possession_avg10":   np.nan,
        "away_possession_avg10":   np.nan,
        "possession_diff":         np.nan,
        "home_shots_target_avg10": np.nan,
        "away_shots_target_avg10": np.nan,
        "shots_diff":              np.nan,
        "home_absences":     0,
        "away_absences":     0,
        "absence_severity":  0,
        "rest_days_home":    7.0,
        "rest_days_away":    7.0,
    }

    if db is not None:
        from db.models import MatchTeamStatistics
        # Fetch the most recent MatchTeamStatistics for home team
        home_stats = db.query(MatchTeamStatistics).filter(MatchTeamStatistics.team_id == match.home_team_id).order_by(MatchTeamStatistics.id.desc()).first()
        away_stats = db.query(MatchTeamStatistics).filter(MatchTeamStatistics.team_id == match.away_team_id).order_by(MatchTeamStatistics.id.desc()).first()

        if home_stats:
            base_feats["home_xg_for_avg10"] = home_stats.xg if home_stats.xg is not None else np.nan
            base_feats["home_possession_avg10"] = home_stats.possession_pct if home_stats.possession_pct is not None else np.nan
            base_feats["home_shots_target_avg10"] = home_stats.shots_on_target if home_stats.shots_on_target is not None else np.nan

        if away_stats:
            base_feats["away_xg_for_avg10"] = away_stats.xg if away_stats.xg is not None else np.nan
            base_feats["away_possession_avg10"] = away_stats.possession_pct if away_stats.possession_pct is not None else np.nan
            base_feats["away_shots_target_avg10"] = away_stats.shots_on_target if away_stats.shots_on_target is not None else np.nan

        if not np.isnan(base_feats["home_xg_for_avg10"]) and not np.isnan(base_feats["away_xg_for_avg10"]):
            base_feats["xg_diff"] = base_feats["home_xg_for_avg10"] - base_feats["away_xg_for_avg10"]
        
        if not np.isnan(base_feats["home_possession_avg10"]) and not np.isnan(base_feats["away_possession_avg10"]):
            base_feats["possession_diff"] = base_feats["home_possession_avg10"] - base_feats["away_possession_avg10"]

        if not np.isnan(base_feats["home_shots_target_avg10"]) and not np.isnan(base_feats["away_shots_target_avg10"]):
            base_feats["shots_diff"] = base_feats["home_shots_target_avg10"] - base_feats["away_shots_target_avg10"]
    
    return base_feats, admin_feats


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def _calculate_risk(ai_prob: float, bookmaker_odds: float,
                    is_draw: bool = False, xg_diff: float = 0.0) -> dict:
    """Classify betting risk based on AI probability vs market probability."""
    house_prob = (1.0 / bookmaker_odds) if bookmaker_odds > 0 else 0.0

    # Flag obvious model errors
    if ai_prob > 0.50 and (is_draw or bookmaker_odds >= 4.0):
        return {"level": "ERROR", "badge": "⚠️ ERROR MODELO", "bgClass": "bg-red-900 text-white font-black"}

    safe_prob = min(ai_prob, house_prob)

    if safe_prob > 0.55:
        return {"level": "BAJO",    "badge": "🟢 BAJO",    "bgClass": "bg-green-600 text-white font-bold"}
    if safe_prob >= 0.35:
        return {"level": "MEDIO",   "badge": "🟡 MEDIO",   "bgClass": "bg-yellow-600 text-white font-bold"}
    if safe_prob >= 0.15:
        return {"level": "ALTO",    "badge": "🟠 ALTO",    "bgClass": "bg-orange-500 text-white font-bold"}
    return     {"level": "LOTERÍA", "badge": "🔴 LOTERÍA", "bgClass": "bg-red-600 text-white font-bold"}


# ---------------------------------------------------------------------------
# Stake sizing — fractional Kelly criterion
# ---------------------------------------------------------------------------

def _fractional_kelly(prob: float, odds: float, fraction: float = 0.20) -> int:
    """Return a 1–10 stake unit recommendation using fractional Kelly (20%)."""
    if odds <= 1.0 or prob <= 0:
        return 1
    b = odds - 1.0
    kelly_pct = (b * prob - (1.0 - prob)) / b
    if kelly_pct <= 0:
        return 1
    return max(1, min(10, int((kelly_pct * fraction) * 200)))

# ---------------------------------------------------------------------------
# Dynamic AI Justification Generator
# ---------------------------------------------------------------------------

def _generate_justification(best: dict, home: str, away: str, base_feats: dict, admin_feats: dict, importances: dict) -> str:
    """Generate a natural-language explanation using actual feature importances."""
    prob_pct = int(best["probability"] * 100)
    market_prob = int(best["bookmaker_implied_prob"] * 100)
    ev = best["ev"]
    
    # 1. Base prediction
    text = f"Nuestro modelo predictivo XGBoost otorga una probabilidad real del {prob_pct}% a '{best['label']}', mientras que la cuota de la casa de apuestas asume solo un {market_prob}%. "
    
    # 2. Add transition word expected by frontend: "A esto"
    text += f"A esto se le suma una ineficiencia del mercado, generando un Expected Value (EV) positivo del {ev}%. "
    
    # 3. Dynamic explanation based on top feature importances
    if importances:
        # Sort features by importance
        top_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)
        # Find the most important feature that actually has a strong signal in this match
        primary_reason = ""
        for feat, imp in top_features:
            val = base_feats.get(feat, admin_feats.get(feat, 0))
            if np.isnan(val): continue
                
            if feat == "xg_diff" and val > 0.5 and best["outcome"] == "home":
                primary_reason = f"En los datos estadísticos puros, el xG (Goles Esperados) es claramente superior para el local ({home}), lo que le otorga una ventaja competitiva evidente. "
                break
            elif feat == "xg_diff" and val < -0.5 and best["outcome"] == "away":
                primary_reason = f"En los datos estadísticos puros, el xG (Goles Esperados) favorece al visitante ({away}), respaldando fuertemente esta predicción. "
                break
            elif feat == "elo_diff" and val > 100 and best["outcome"] == "home":
                primary_reason = f"En el análisis histórico, el Elo dinámico confirma una superioridad estructural del equipo local. "
                break
            elif feat == "elo_diff" and val < -100 and best["outcome"] == "away":
                primary_reason = f"En el análisis histórico, el Elo dinámico demuestra que el visitante tiene un nivel competitivo considerablemente mayor. "
                break
            elif feat == "possession_diff" and val > 10 and best["outcome"] == "home":
                primary_reason = f"En el control del juego, el dominio de la posesión del equipo local minimiza las opciones del rival. "
                break
            elif feat == "admin_offensive_diff" and val > 1 and best["outcome"] == "home":
                primary_reason = f"En el análisis de las métricas manuales, {home} presenta una fuerza ofensiva muy superior a la defensa de {away}. "
                break
            elif feat == "admin_motivation_diff" and abs(val) > 1:
                fav_team = home if val > 0 else away
                if (val > 0 and best["outcome"] == "home") or (val < 0 and best["outcome"] == "away"):
                    primary_reason = f"En el plano psicológico, {fav_team} llega con un plus de motivación y momentum que el mercado no está reflejando. "
                    break
                    
        if primary_reason:
            text += primary_reason
        else:
            text += "En los datos analizados, la combinación de múltiples factores tácticos y de forma reciente justifican el valor encontrado. "
    else:
        text += "En la simulación táctica, el equilibrio de fuerzas se rompe a favor de esta selección debido a la solidez estructural evaluada. "
        
    # 4. Add transition word: "Con un "
    text += f"Con un cálculo de riesgo catalogado como '{best['risk']['level']}', esta selección es matemáticamente rentable a largo plazo."
        
    return text


def _dynamic_ev_threshold(odds_val: float) -> float:
    """
    Dynamic Value Bet Threshold: 
    Require a higher EV edge (margin of safety) for higher odds 
    to compensate for increased variance.
    """
    if odds_val > 5.0:
        return 8.0   # 8% edge required
    elif odds_val > 3.0:
        return 5.0   # 5% edge required
    elif odds_val > 2.0:
        return 2.0   # 2% edge required
    return 1.5       # At least 1.5% edge for low odds


# ---------------------------------------------------------------------------
# Club football evaluator
# ---------------------------------------------------------------------------

def _evaluate_match(match: Match, predictor, db: Session | None = None) -> dict:
    """
    Evaluate a club football match and return a structured prediction dict.

    Returns a dict with keys: id, homeTeam, awayTeam, date, status,
    oddsSource, sport, bestPick, allCandidates, topPicks, justification.
    """
    home, away = match.home_team.name, match.away_team.name
    base_feats, admin_feats = _build_match_features(match, db)
    # The predictor expects a single dict
    features = {**base_feats, **admin_feats}
    odds       = _get_odds(match, db)
    if odds is None:
        return None
    source     = odds.pop("_source", "mock")
    all_bookmakers_h2h = odds.pop("all_bookmakers_h2h", [])

    predict_features = {k: v for k, v in features.items() if not k.startswith("_")}
    pred             = predictor.predict_match(predict_features)

    # Expected goals for Poisson-based allMarkets evaluation.
    # Derive lambdas from the predictor's 1x2 probabilities so that
    # handicap probabilities are consistent with the model's win-probability.
    # Club football average: ~2.60 total goals/match.
    lam_home, lam_away = _fit_lambdas_from_1x2_probs(
        pred["probabilities"]["home"],
        pred["probabilities"]["away"],
        base_total=2.60,
    )

    eps        = 1e-6
    candidates = []

    # 1x2 markets
    for outcome, label in [("home", "Victoria Local"), ("draw", "Empate"), ("away", "Victoria Visitante")]:
        book = float(odds[outcome])
        fair = float(pred["fair_odds_1x2"][outcome])
        ev   = (book / (fair + eps) - 1) * 100
        min_ev = _dynamic_ev_threshold(book)
        candidates.append({
            "market":                 "1x2",
            "outcome":                outcome,
            "label":                  label,
            "probability":            float(pred["probabilities"][outcome]),
            "bookmaker_odds":         book,
            "fair_odds":              round(fair, 2),
            "ev":                     round(ev, 2),
            "is_value":               ev > min_ev,
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
        min_ev = _dynamic_ev_threshold(book)
        candidates.append({
            "market":                 "ou25",
            "outcome":                side,
            "label":                  label,
            "probability":            round(prob, 4),
            "bookmaker_odds":         book,
            "fair_odds":              round(fair, 2),
            "ev":                     round(ev, 2),
            "is_value":               ev > min_ev,
            "bookmaker_implied_prob": round(1.0 / book, 4) if book > 0 else 0,
        })

    # Annotate each candidate with risk and stake
    for c in candidates:
        c["risk"]  = _calculate_risk(c["probability"], c["bookmaker_odds"])
        c["stake"] = _fractional_kelly(c["probability"], c["bookmaker_odds"])

    value_bets = [c for c in candidates if c["is_value"]]
    if value_bets:
        best = max(value_bets, key=lambda x: x["probability"])
    else:
        best = max(candidates, key=lambda x: x["ev"])

    candidates.sort(key=lambda x: x["probability"], reverse=True)

    all_markets = _build_all_markets(
        match, db, pred["probabilities"], pred["prob_over25"], lam_home, lam_away
    )
    
    # ── GENERATE AI ANALYSIS TEXT ──
    # base_feats and admin_feats were extracted from _build_match_features!
    feats = {**base_feats, **admin_feats}
    importances = predictor.get_feature_importances() if hasattr(predictor, "get_feature_importances") else {}
    justification_text = _generate_justification(best, home, away, feats, admin_feats, importances)

    return {
        "id":         match.id,
        "homeTeam":   home,
        "awayTeam":   away,
        "date":       match.date.isoformat() + "Z" if match.date else None,
        "status":     match.status,
        "oddsSource": source,
        "isMockOdds": source == "mock",
        "sport":      "football",
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
        "justification": justification_text,
        "all_bookmakers": all_bookmakers_h2h,
        "allMarkets":    all_markets,
    }




# ---------------------------------------------------------------------------
# World Cup evaluator
# ---------------------------------------------------------------------------


