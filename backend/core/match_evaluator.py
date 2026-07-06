"""
match_evaluator.py
------------------
Evaluates upcoming football matches and computes value-bet candidates.

Supports two evaluator paths:
  - Club football (La Liga, Premier, Champions): _evaluate_match()
  - World Cup national teams               : _evaluate_world_cup_match()

The correct evaluator is selected by cache_service based on sport key.
"""

import math
import random
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import Match, Odds, MarketOdds, OddsHistory, Team, WorldCupTeamStats


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

# World Cup odds pool (slightly tighter markets — bookies price WC carefully)
_WC_ODDS_POOL = [
    {"home": 1.60, "draw": 3.80, "away": 5.00, "over25": 2.10, "under25": 1.72},
    {"home": 2.00, "draw": 3.40, "away": 3.50, "over25": 1.85, "under25": 1.95},
    {"home": 2.40, "draw": 3.20, "away": 3.00, "over25": 1.95, "under25": 1.85},
    {"home": 1.75, "draw": 3.60, "away": 4.50, "over25": 2.20, "under25": 1.65},
    {"home": 3.00, "draw": 3.30, "away": 2.30, "over25": 2.00, "under25": 1.80},
    {"home": 2.20, "draw": 3.10, "away": 3.30, "over25": 1.90, "under25": 1.90},
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

def _build_match_features(match: Match) -> dict:
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

    return {
        "home_elo":          home_elo,
        "away_elo":          away_elo,
        "elo_diff":          home_elo - away_elo,
        "home_xg_for_avg10": round(1.2 * h_pow, 2),
        "away_xg_for_avg10": round(1.1 * a_pow, 2),
        "xg_diff":           round((1.2 * h_pow) - (1.1 * a_pow), 2),
        "home_possession_avg10":   round(50 * h_pow, 1),
        "away_possession_avg10":   round(50 * a_pow, 1),
        "possession_diff":         round((50 * h_pow) - (50 * a_pow), 1),
        "home_shots_target_avg10": round(4.5 * h_pow, 1),
        "away_shots_target_avg10": round(4.0 * a_pow, 1),
        "shots_diff":              round((4.5 * h_pow) - (4.0 * a_pow), 1),
        "home_absences":     rng.randint(0, 3),
        "away_absences":     rng.randint(0, 3),
        "absence_severity":  rng.randint(0, 1),
        "rest_days_home":    rng.randint(4, 7),
        "rest_days_away":    rng.randint(4, 7),
    }


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
    features   = _build_match_features(match)
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

    return {
        "id":         match.id,
        "homeTeam":   home,
        "awayTeam":   away,
        "date":       match.date.isoformat() + "Z" if match.date else None,
        "status":     match.status,
        "oddsSource": source,
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
        "justification": f"{home} vs {away} — evaluación de fútbol.",
        "all_bookmakers": all_bookmakers_h2h,
        "allMarkets":    all_markets,
    }


# ---------------------------------------------------------------------------
# World Cup evaluator
# ---------------------------------------------------------------------------

def _evaluate_world_cup_match(match: Match, wc_predictor,
                               db: Session | None = None) -> dict:
    """
    Evaluate a World Cup national team match.
    Uses WorldCupPredictor with FIFA rankings, squad quality, and H2H stats.
    """
    from models.world_cup_predictor import FIFA_POINTS, TEAM_ALIASES

    home, away = match.home_team.name, match.away_team.name

    # Detect knockout stage
    # football-data.org returns plural forms: 'quarter_finals', 'semi_finals', 'round_of_16'
    # We normalise by stripping a trailing 's' to match both singular and plural variants
    _raw_stage = getattr(match, 'stage', '') or ''
    _stage_norm = _raw_stage.lower().rstrip('s')  # 'quarter_finals' -> 'quarter_final'
    
    # Matches 'round_of_16', 'last_16', 'last_32', 'quarter_final', 'semi_final', 'final'
    is_knockout = any(k in _stage_norm for k in ('round_of_', 'last_', 'quarter_final', 'semi_final', 'final')) and 'group' not in _stage_norm
    
    local_db_created = False
    if db is None:
        from db.session import SessionLocal
        db = SessionLocal()
        local_db_created = True
        
    from db.models import WorldCupTeamStats, MatchTeamStatistics
    h_team = db.query(Team).filter(Team.name == home).first()
    a_team = db.query(Team).filter(Team.name == away).first()
    
    h_stat = db.query(WorldCupTeamStats).filter(WorldCupTeamStats.team_id == h_team.id).first() if h_team else None
    a_stat = db.query(WorldCupTeamStats).filter(WorldCupTeamStats.team_id == a_team.id).first() if a_team else None
    
    from sqlalchemy.sql import func
    avg_h_xg = db.query(func.avg(MatchTeamStatistics.xg)).filter(MatchTeamStatistics.team_id == h_team.id).scalar() if h_team else None
    avg_a_xg = db.query(func.avg(MatchTeamStatistics.xg)).filter(MatchTeamStatistics.team_id == a_team.id).scalar() if a_team else None

    avg_h_poss = db.query(func.avg(MatchTeamStatistics.possession_pct)).filter(MatchTeamStatistics.team_id == h_team.id).scalar() if h_team else None
    avg_a_poss = db.query(func.avg(MatchTeamStatistics.possession_pct)).filter(MatchTeamStatistics.team_id == a_team.id).scalar() if a_team else None

    avg_h_shots = db.query(func.avg(MatchTeamStatistics.shots_on_target)).filter(MatchTeamStatistics.team_id == h_team.id).scalar() if h_team else None
    avg_a_shots = db.query(func.avg(MatchTeamStatistics.shots_on_target)).filter(MatchTeamStatistics.team_id == a_team.id).scalar() if a_team else None
    
    extra_features = {
        "home_wc_matches": h_stat.matches_played if h_stat else 0,
        "away_wc_matches": a_stat.matches_played if a_stat else 0,
        "home_wc_goals": (h_stat.goals_for + h_stat.goals_against) if h_stat else 0,
        "away_wc_goals": (a_stat.goals_for + a_stat.goals_against) if a_stat else 0,
    }
    if avg_h_xg is not None: extra_features["home_avg_xg"] = float(avg_h_xg)
    if avg_a_xg is not None: extra_features["away_avg_xg"] = float(avg_a_xg)
    if avg_h_poss is not None: extra_features["home_avg_possession"] = float(avg_h_poss)
    if avg_a_poss is not None: extra_features["away_avg_possession"] = float(avg_a_poss)
    if avg_h_shots is not None: extra_features["home_avg_shots"] = float(avg_h_shots)
    if avg_a_shots is not None: extra_features["away_avg_shots"] = float(avg_a_shots)


    # Get prediction from World Cup specialist model
    pred = wc_predictor.predict_match(home, away, is_knockout=is_knockout, extra_features=extra_features)

    # Get odds (real only)
    odds   = _get_odds(match, db)
    if odds is None:
        return None

    source = odds.pop("_source", "mock")
    all_bookmakers_h2h = odds.pop("all_bookmakers_h2h", [])

    # Expected goals for Poisson-based allMarkets evaluation.
    # Derive lambdas from the predictor's 1x2 probabilities so that
    # handicap probabilities are consistent with the model's win-probability.
    # World Cup average: ~2.35 total goals/match.
    lam_home, lam_away = _fit_lambdas_from_1x2_probs(
        pred["probabilities"]["home"],
        pred["probabilities"]["away"],
        base_total=2.35,
    )

    eps        = 1e-6
    candidates = []

    # 1x2 markets
    for outcome, label in [("home", "Victoria Local"), ("draw", "Empate"), ("away", "Victoria Visitante")]:
        book = float(odds[outcome])
        fair = float(pred["fair_odds_1x2"][outcome])
        ev   = (book / (fair + eps) - 1) * 100
        prob = float(pred["probabilities"][outcome])
        min_ev = _dynamic_ev_threshold(book)
        candidates.append({
            "market":                 "1x2",
            "outcome":                outcome,
            "label":                  label,
            "probability":            prob,
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

    # Annotate with risk and stake
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

    # Build rich justification with FIFA context and Live 2026 DB stats
    home_pts    = pred.get("home_fifa_pts", 0)
    away_pts    = pred.get("away_fifa_pts", 0)
    home_qual   = pred.get("home_squad_quality", 0)
    away_qual   = pred.get("away_squad_quality", 0)
    h2h_n       = pred.get("h2h_matches", 0)
    h2h_note    = f"H2H: {h2h_n} partidos históricos." if h2h_n > 0 else "Primer enfrentamiento en un Mundial."

    # DB info already fetched above
    
    h_stats_str = ""
    a_stats_str = ""

    if h_team:
        h_stat = db.query(WorldCupTeamStats).filter(WorldCupTeamStats.team_id == h_team.id).first()
        if h_stat and h_stat.matches_played > 0:
            h_stats_str = f" {home} lleva {h_stat.matches_played} partidos en el Mundial 2026 ({h_stat.goals_for} GF, {h_stat.goals_against} GC)."

    if a_team:
        a_stat = db.query(WorldCupTeamStats).filter(WorldCupTeamStats.team_id == a_team.id).first()
        if a_stat and a_stat.matches_played > 0:
            a_stats_str = f" {away} lleva {a_stat.matches_played} partidos en el Mundial 2026 ({a_stat.goals_for} GF, {a_stat.goals_against} GC)."
        
    if local_db_created:
        db.close()

    justification = (
        f"FIFA Rankings: {home} ({home_pts:.0f} pts) vs {away} ({away_pts:.0f} pts). "
        f"Calidad de plantilla: {home_qual:.0f} vs {away_qual:.0f}/100. {h2h_note}"
        f"{h_stats_str}{a_stats_str}"
    )

    return {
        "id":         match.id,
        "homeTeam":   home,
        "awayTeam":   away,
        "date":       match.date.isoformat() + "Z" if match.date else None,
        "status":     match.status,
        "oddsSource": source,
        "sport":      "worldcup",
        # Extra World Cup context for the frontend
        "homeFifaPts":    home_pts,
        "awayFifaPts":    away_pts,
        "homeSquadQuality": home_qual,
        "awaySquadQuality": away_qual,
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
        "justification": justification,
        "all_bookmakers": all_bookmakers_h2h,
        "allMarkets":    all_markets,
    }
