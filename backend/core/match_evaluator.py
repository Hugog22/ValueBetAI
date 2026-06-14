"""
match_evaluator.py
------------------
Evaluates upcoming football matches and computes value-bet candidates.

Supports two evaluator paths:
  - Club football (La Liga, Premier, Champions): _evaluate_match()
  - World Cup national teams               : _evaluate_world_cup_match()

The correct evaluator is selected by cache_service based on sport key.
"""

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

    # Pull back extreme deviations unless strongly supported
    if abs(ai_prob - house_prob) > 0.15 and abs(xg_diff) < 1.0:
        ai_prob = house_prob + (0.15 if ai_prob > house_prob else -0.15)

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
    return 0.0       # Any positive EV is fine


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

    candidates.sort(key=lambda x: x["ev"], reverse=True)
    best = candidates[0]

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
    is_knockout = False
    
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

    candidates.sort(key=lambda x: x["ev"], reverse=True)
    best = candidates[0]

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
    }
