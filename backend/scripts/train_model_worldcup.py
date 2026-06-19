"""
train_model_worldcup.py
-----------------------
Trains XGBoost models for World Cup national team predictions.

Uses world_cup_historical.csv produced by fetch_world_cup_data.py.

Models:
  wc_1x2_xgb.pkl   — 1X2 match result (home/draw/away)
  wc_ou25_xgb.pkl  — Over/Under 2.5 goals

Key features:
  - FIFA ranking points (official strength signal)
  - Squad quality score (avg club level of players)
  - Head-to-head historical stats
  - Tournament stage (group vs knockout)
  - Recent form metrics

Run from backend/:
    python -m scripts.train_model_worldcup
"""

import json
import logging
import math
import os
import sys
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

from db.session import SessionLocal
from db.models import Match, WorldCupTeamStats, Team, MatchTeamStatistics

def get_db_stats():
    db = SessionLocal()
    stats = db.query(WorldCupTeamStats).all()
    teams = db.query(Team).all()
    team_map = {t.id: t.name for t in teams}
    
    wc_stats = {}
    for s in stats:
        tname = team_map.get(s.team_id)
        if tname:
            wc_stats[tname] = {
                "matches": s.matches_played,
                "goals_scored": s.goals_for,
                "goals_conceded": s.goals_against
            }
            
    xg_stats = {}
    match_stats = db.query(MatchTeamStatistics).all()
    for s in match_stats:
        tname = team_map.get(s.team_id)
        if tname:
            if tname not in xg_stats:
                xg_stats[tname] = {"xg": [], "possession": [], "shots_on_target": []}
            if s.xg is not None:
                xg_stats[tname]["xg"].append(float(s.xg))
            if s.possession_pct is not None:
                xg_stats[tname]["possession"].append(float(s.possession_pct))
            if s.shots_on_target is not None:
                xg_stats[tname]["shots_on_target"].append(float(s.shots_on_target))
                
    db.close()
    return wc_stats, xg_stats


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "world_cup_historical.csv")
SQUAD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "world_cup_squads.json")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
META_PATH  = os.path.join(MODELS_DIR, "wc_training_meta.json")

TSCV_SPLITS   = 3   # fewer splits — WC has limited data (~400 matches total)
OPTUNA_TRIALS = 20
TODAY = datetime.utcnow()  # Will be redefined locally where needed


# ---------------------------------------------------------------------------
# Feature engineering for World Cup
# ---------------------------------------------------------------------------

def _days_ago(date_str: str) -> float:
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        today = datetime.utcnow()
        return max(0, (today - dt).days)
    except Exception:
        return 365.0


def compute_sample_weights(df: pd.DataFrame, wc_stats: dict) -> np.ndarray:
    decay = 1.0
    weights = []
    today = datetime.utcnow()
    for _, row in df.iterrows():
        date_str = str(row.get("date", today))
        days   = _days_ago(date_str)
        w      = max(0.05, math.exp(-decay * days / 365.0))
        
        if row.get("is_knockout", 0) == 1:
            w *= 2.0
            
        if "2026" in date_str:
            # DYNAMIC WEIGHTING based on matches played in World Cup 2026
            ht = str(row["home_team"])
            at = str(row["away_team"])
            hm = wc_stats.get(ht, {}).get("matches", 0)
            am = wc_stats.get(at, {}).get("matches", 0)
            # The more matches they have played in this world cup, the more this 2026 form matters
            w *= 5.0 * (1.0 + 0.5 * hm) * (1.0 + 0.5 * am)
            
        weights.append(w)
    return np.array(weights)


def build_h2h_stats(df: pd.DataFrame) -> dict:
    """Build H2H cache from historical data (with temporal awareness)."""
    h2h: dict[tuple, dict] = {}
    df_sorted = df.sort_values("date")
    for _, row in df_sorted.iterrows():
        ht = str(row["home_team"])
        at = str(row["away_team"])
        hg = float(row.get("home_goals", 0))
        ag = float(row.get("away_goals", 0))
        for ta, tb, gf, ga in [(ht, at, hg, ag), (at, ht, ag, hg)]:
            key = (ta, tb)
            if key not in h2h:
                h2h[key] = {"wins": 0, "draws": 0, "total": 0, "gf": 0.0, "ga": 0.0}
            h2h[key]["total"] += 1
            h2h[key]["gf"]    += gf
            h2h[key]["ga"]    += ga
            if gf > ga:
                h2h[key]["wins"] += 1
            elif gf == ga:
                h2h[key]["draws"] += 1
    return h2h


def h2h_win_rate(h2h: dict, team_a: str, team_b: str) -> float:
    key = (team_a, team_b)
    entry = h2h.get(key, {})
    total = entry.get("total", 0)
    return entry["wins"] / total if total > 0 else 0.35


def h2h_goals(h2h: dict, team_a: str, team_b: str) -> tuple[float, float]:
    key = (team_a, team_b)
    entry = h2h.get(key, {})
    total = entry.get("total", 0)
    if total == 0:
        return 1.5, 1.2
    return entry["gf"] / total, entry["ga"] / total


def build_rolling_form(df: pd.DataFrame) -> dict:
    """Build rolling 5-match form (pts, goals) per team."""
    df_sorted = df.sort_values("date")
    records: list[tuple] = []
    for _, row in df_sorted.iterrows():
        ht, at = str(row["home_team"]), str(row["away_team"])
        hg, ag = float(row.get("home_goals", 0)), float(row.get("away_goals", 0))
        # home: pts, goals_for, goals_against
        hp = 3 if hg > ag else (1 if hg == ag else 0)
        ap = 3 if ag > hg else (1 if ag == hg else 0)
        records.append((str(row.get("date", ""))[:10], ht, hp, hg, ag))
        records.append((str(row.get("date", ""))[:10], at, ap, ag, hg))

    form_df = pd.DataFrame(records, columns=["date", "team", "pts", "gf", "ga"])
    form_df = form_df.sort_values("date")
    form: dict[str, dict] = {}
    for _, row in form_df.iterrows():
        t = row["team"]
        if t not in form:
            form[t] = {"pts": [], "gf": [], "ga": []}
        form[t]["pts"].append(float(row["pts"]))
        form[t]["gf"].append(float(row["gf"]))
        form[t]["ga"].append(float(row["ga"]))

    # Compute rolling averages from last 5 matches
    form_stats: dict[str, dict] = {}
    for team, data in form.items():
        pts5 = sum(data["pts"][-5:])
        gf5  = sum(data["gf"][-5:]) / min(5, len(data["gf"]))
        ga5  = sum(data["ga"][-5:]) / min(5, len(data["ga"]))
        form_stats[team] = {"pts5": pts5, "gf5": gf5, "ga5": ga5}
    return form_stats


def load_squad_quality() -> dict[str, float]:
    """Load squad quality scores from JSON."""
    if not os.path.exists(SQUAD_PATH):
        return {}
    try:
        with open(SQUAD_PATH) as f:
            raw = json.load(f)
        return {k: float(v.get("squad_quality_score", 60.0)) for k, v in raw.items()}
    except Exception:
        return {}


def build_features(df: pd.DataFrame, wc_stats: dict, xg_stats: dict) -> pd.DataFrame:
    """Construct all feature columns for training."""
    from models.world_cup_predictor import FIFA_POINTS, DEFAULT_FIFA_POINTS
    h2h      = build_h2h_stats(df)
    form     = build_rolling_form(df)
    sq_qual  = load_squad_quality()

    rows = []
    df_sorted = df.sort_values("date").reset_index(drop=True)

    for i, row in df_sorted.iterrows():
        ht = str(row["home_team"])
        at = str(row["away_team"])
        hg = float(row.get("home_goals", 0))
        ag = float(row.get("away_goals", 0))

        if pd.isna(hg) or pd.isna(ag):
            continue

        home_pts = float(row.get("home_fifa_pts", FIFA_POINTS.get(ht, DEFAULT_FIFA_POINTS)))
        


        away_pts = float(row.get("away_fifa_pts", FIFA_POINTS.get(at, DEFAULT_FIFA_POINTS)))
        home_q   = sq_qual.get(ht, 40.0 + (home_pts - 1280) / 580 * 55)
        away_q   = sq_qual.get(at, 40.0 + (away_pts - 1280) / 580 * 55)

        h_wc = wc_stats.get(ht, {"matches": 0, "goals_scored": 0, "goals_conceded": 0})
        a_wc = wc_stats.get(at, {"matches": 0, "goals_scored": 0, "goals_conceded": 0})
        
        h_xg = xg_stats.get(ht, {"xg": [], "possession": [], "shots_on_target": []})
        a_xg = xg_stats.get(at, {"xg": [], "possession": [], "shots_on_target": []})
        
        h_xg_avg = sum(h_xg["xg"])/len(h_xg["xg"]) if h_xg["xg"] else 1.5
        a_xg_avg = sum(a_xg["xg"])/len(a_xg["xg"]) if a_xg["xg"] else 1.5
        
        h_poss_avg = sum(h_xg["possession"])/len(h_xg["possession"]) if h_xg["possession"] else 50.0
        a_poss_avg = sum(a_xg["possession"])/len(a_xg["possession"]) if a_xg["possession"] else 50.0
        
        h_shots_avg = sum(h_xg["shots_on_target"])/len(h_xg["shots_on_target"]) if h_xg["shots_on_target"] else 4.0
        a_shots_avg = sum(a_xg["shots_on_target"])/len(a_xg["shots_on_target"]) if a_xg["shots_on_target"] else 4.0

        h_form = form.get(ht, {"pts5": 7.5, "gf5": 1.5, "ga5": 1.2})
        a_form = form.get(at, {"pts5": 7.5, "gf5": 1.2, "ga5": 1.5})

        rows.append({
            "home_fifa_pts":      home_pts,
            "away_fifa_pts":      away_pts,
            "fifa_pts_diff":      home_pts - away_pts,
            "home_squad_quality": home_q,
            "away_squad_quality": away_q,
            "squad_quality_diff": home_q - away_q,
            "home_form_pts5":     h_form["pts5"],
            "away_form_pts5":     a_form["pts5"],
            "form_diff":          h_form["pts5"] - a_form["pts5"],
            "home_h2h_win_rate":  h2h_win_rate(h2h, ht, at),
            "away_h2h_win_rate":  h2h_win_rate(h2h, at, ht),
            "is_knockout":        float(row.get("is_knockout", 0)),
            "home_goals_avg5":    h_form["gf5"],
            "away_goals_avg5":    a_form["gf5"],
            "home_conceded_avg5": h_form["ga5"],
            "away_conceded_avg5": a_form["ga5"],
            "home_avg_xg": h_xg_avg,
            "away_avg_xg": a_xg_avg,
            "home_avg_possession": h_poss_avg,
            "away_avg_possession": a_poss_avg,
            "home_avg_shots": h_shots_avg,
            "away_avg_shots": a_shots_avg,
            "home_wc_matches": h_wc["matches"],
            "away_wc_matches": a_wc["matches"],
            "home_wc_goals": h_wc["goals_scored"],
            "away_wc_goals": a_wc["goals_scored"],
            # targets
            "_home_goals": hg,
            "_away_goals": ag,
        })

    return pd.DataFrame(rows)

FEATURES = [
    "home_fifa_pts", "away_fifa_pts", "fifa_pts_diff",
    "home_squad_quality", "away_squad_quality", "squad_quality_diff",
    "home_form_pts5", "away_form_pts5", "form_diff",
    "home_h2h_win_rate", "away_h2h_win_rate",
    "is_knockout",
    "home_goals_avg5", "away_goals_avg5",
    "home_conceded_avg5", "away_conceded_avg5",
    "home_avg_xg", "away_avg_xg",
    "home_avg_possession", "away_avg_possession",
    "home_avg_shots", "away_avg_shots",
    "home_wc_matches", "away_wc_matches",
    "home_wc_goals", "away_wc_goals"
]


def make_objective_1x2(X: pd.DataFrame, y: np.ndarray, tscv):
    import xgboost as xgb
    from sklearn.metrics import log_loss
    def objective(trial):
        params = {
            "objective": "multi:softprob", "num_class": 3,
            "eval_metric": "mlogloss", "use_label_encoder": False,
            "random_state": 42, "n_estimators": 100,
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        }
        lls = []
        for tr, va in tscv.split(X):
            clf = xgb.XGBClassifier(**params)
            clf.fit(X.iloc[tr], y[tr], eval_set=[(X.iloc[va], y[va])], verbose=False)
            probs = clf.predict_proba(X.iloc[va])
            lls.append(log_loss(y[va], probs))
        return np.mean(lls)
    return objective

def make_objective_ou25(X: pd.DataFrame, y: np.ndarray, tscv):
    import xgboost as xgb
    from sklearn.metrics import log_loss
    def objective(trial):
        params = {
            "objective": "binary:logistic", "eval_metric": "logloss", 
            "use_label_encoder": False, "random_state": 42, "n_estimators": 100,
            "max_depth": trial.suggest_int("max_depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        }
        lls = []
        for tr, va in tscv.split(X):
            clf = xgb.XGBClassifier(**params)
            clf.fit(X.iloc[tr], y[tr], eval_set=[(X.iloc[va], y[va])], verbose=False)
            probs = clf.predict_proba(X.iloc[va])[:, 1]
            lls.append(log_loss(y[va], probs))
        return np.mean(lls)
    return objective

def train(is_auto=True):
    """Run full training pipeline for World Cup models with Optuna."""
    import xgboost as xgb
    import lightgbm as lgb
    import optuna
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import accuracy_score, log_loss

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    if not os.path.exists(DATA_PATH):
        logger.error(f"No data found at {DATA_PATH}. Run fetch_world_cup_data.py first.")
        raise ValueError(f"No data found at {DATA_PATH}. Run fetch_world_cup_data.py first.")

    logger.info(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    wc_stats, xg_stats = get_db_stats()
    
    # Merge finished matches from DB into df
    db = SessionLocal()
    db_matches = db.query(Match).filter(Match.status == 'Finished').all()
    teams = db.query(Team).all()
    team_map = {t.id: t.name for t in teams}
    
    # Load WC squads to filter out non-WC matches (like La Liga)
    import json
    squads_path = os.path.join(os.path.dirname(__file__), "..", "data", "world_cup_squads.json")
    wc_teams = []
    if os.path.exists(squads_path):
        with open(squads_path, 'r') as f:
            wc_teams = list(json.load(f).keys())

    new_rows = []
    for m in db_matches:
        h_name = team_map.get(m.home_team_id, "")
        a_name = team_map.get(m.away_team_id, "")
        
        # Only add if it's a World Cup team
        if h_name in wc_teams and a_name in wc_teams:
            if m.home_goals is not None and m.away_goals is not None:
                new_rows.append({
                    "date": m.date.strftime("%Y-%m-%d"),
                    "home_team": h_name,
                    "away_team": a_name,
                    "home_goals": m.home_goals,
                    "away_goals": m.away_goals,
                    "is_knockout": 0 # We assume groups for now in early stage
                })
    db.close()
    
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        logger.info(f"Appended {len(new_rows)} finished 2026 matches from DB.")
        
    logger.info("Building features…")
    feat_df = build_features(df, wc_stats, xg_stats)
    
    # Mirror features to eliminate home bias for neutral ground
    mirrored_feat = feat_df.copy()
    rename_cols = {
        "_home_goals": "_away_goals",
        "_away_goals": "_home_goals"
    }
    for col in FEATURES:
        if col.startswith("home_"):
            rename_cols[col] = col.replace("home_", "away_")
        elif col.startswith("away_"):
            rename_cols[col] = col.replace("away_", "home_")
    
    mirrored_feat.rename(columns=rename_cols, inplace=True)
    mirrored_feat["fifa_pts_diff"] = -mirrored_feat["fifa_pts_diff"]
    mirrored_feat["squad_quality_diff"] = -mirrored_feat["squad_quality_diff"]
    mirrored_feat["form_diff"] = -mirrored_feat["form_diff"]

    feat_df = pd.concat([feat_df, mirrored_feat], ignore_index=True)
    df = pd.concat([df, df.copy()], ignore_index=True)
    
    if len(feat_df) < 30:
        logger.error("Not enough data to train. Need at least 30 matches.")
        raise ValueError("Not enough data to train. Need at least 30 matches.")

    X = feat_df[FEATURES].astype(float)
    tscv = TimeSeriesSplit(n_splits=TSCV_SPLITS)

    # ── MODEL A: 1X2 ─────────────────────────────────────────────────────────
    logger.info("Training 1X2 model with Optuna…")
    y_1x2 = np.select(
        [feat_df["_home_goals"] > feat_df["_away_goals"],
         feat_df["_home_goals"] == feat_df["_away_goals"]],
        [0, 1], default=2
    )

    study_1x2 = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study_1x2.optimize(make_objective_1x2(X, y_1x2, tscv), n_trials=OPTUNA_TRIALS, show_progress_bar=False)
    best_1x2 = study_1x2.best_params
    logger.info(f"Best XGBoost 1X2 params: {best_1x2}")

    xgb_1x2 = xgb.XGBClassifier(
        objective="multi:softprob", num_class=3, n_estimators=300,
        use_label_encoder=False, random_state=42, eval_metric="mlogloss", **best_1x2
    )
    # Ensure sklearn's is_classifier() returns True for XGBClassifier,
    # which is required by VotingClassifier._validate_estimators() in newer sklearn.
    xgb_1x2._estimator_type = "classifier"
    lgb_1x2 = lgb.LGBMClassifier(
        objective="multiclass", num_class=3, n_estimators=300, 
        learning_rate=0.05, max_depth=4, random_state=42, verbose=-1,
    )
    rf_1x2 = RandomForestClassifier(n_estimators=300, max_depth=6, random_state=42)
    
    ensemble_1x2 = VotingClassifier(estimators=[('xgb', xgb_1x2), ('lgb', lgb_1x2), ('rf', rf_1x2)], voting='soft')

    cv_scores = []
    for tr, va in tscv.split(X):
        w_tr = compute_sample_weights(df.iloc[tr], wc_stats)
        # VotingClassifier supports sample_weight via fit()
        ensemble_1x2.fit(X.iloc[tr], y_1x2[tr], sample_weight=w_tr)
        preds = ensemble_1x2.predict(X.iloc[va])
        cv_scores.append(accuracy_score(y_1x2[va], preds))
    logger.info(f"1X2 Ensemble CV accuracy: {np.mean(cv_scores):.4f}")

    # Train the final ensemble on the full training split, then calibrate with
    # cv="prefit" so CalibratedClassifierCV only fits the sigmoid layer on the
    # held-out 20% — this avoids the XGBClassifier is_classifier() check that
    # fires when sklearn tries to clone/re-fit sub-estimators internally.
    split_idx = max(1, int(len(X) * 0.80))
    w_full = compute_sample_weights(df.iloc[:split_idx], wc_stats)
    try:
        ensemble_1x2.fit(X.iloc[:split_idx], y_1x2[:split_idx], sample_weight=w_full)
    except TypeError:
        ensemble_1x2.fit(X.iloc[:split_idx], y_1x2[:split_idx])

    # Calibrate on the held-out 20% using the already-fitted ensemble
    cal_1x2 = CalibratedClassifierCV(ensemble_1x2, cv="prefit", method="sigmoid")
    cal_1x2.fit(X.iloc[split_idx:], y_1x2[split_idx:])
    joblib.dump(cal_1x2, os.path.join(MODELS_DIR, "wc_1x2_xgb.pkl"))

    # ── MODEL B: O/U 2.5 ─────────────────────────────────────────────────────
    logger.info("Training O/U 2.5 model with Optuna…")
    y_ou25 = ((feat_df["_home_goals"] + feat_df["_away_goals"]) > 2.5).astype(int).values

    study_ou25 = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study_ou25.optimize(make_objective_ou25(X, y_ou25, tscv), n_trials=OPTUNA_TRIALS, show_progress_bar=False)
    best_ou25 = study_ou25.best_params
    logger.info(f"Best XGBoost O/U 2.5 params: {best_ou25}")

    xgb_ou = xgb.XGBClassifier(
        objective="binary:logistic", n_estimators=300,
        use_label_encoder=False, random_state=42, eval_metric="logloss", **best_ou25
    )
    # Same fix as 1X2: ensure sklearn sees XGBClassifier as a classifier.
    xgb_ou._estimator_type = "classifier"
    lgb_ou = lgb.LGBMClassifier(
        objective="binary", n_estimators=300, learning_rate=0.05, 
        max_depth=4, random_state=42, verbose=-1,
    )
    rf_ou = RandomForestClassifier(n_estimators=300, max_depth=6, random_state=42)
    
    ensemble_ou25 = VotingClassifier(estimators=[('xgb', xgb_ou), ('lgb', lgb_ou), ('rf', rf_ou)], voting='soft')

    cv_ou25 = []
    for tr, va in tscv.split(X):
        w_tr = compute_sample_weights(df.iloc[tr], wc_stats)
        ensemble_ou25.fit(X.iloc[tr], y_ou25[tr], sample_weight=w_tr)
        probs = ensemble_ou25.predict_proba(X.iloc[va])[:, 1]
        cv_ou25.append(log_loss(y_ou25[va], probs))
    logger.info(f"O/U 2.5 Ensemble CV LogLoss: {np.mean(cv_ou25):.4f}")

    # Same prefit calibration pattern as 1X2 — avoids XGBClassifier classifier check
    try:
        ensemble_ou25.fit(X.iloc[:split_idx], y_ou25[:split_idx], sample_weight=w_full)
    except TypeError:
        ensemble_ou25.fit(X.iloc[:split_idx], y_ou25[:split_idx])

    cal_ou25 = CalibratedClassifierCV(ensemble_ou25, cv="prefit", method="sigmoid")
    cal_ou25.fit(X.iloc[split_idx:], y_ou25[split_idx:])
    joblib.dump(cal_ou25, os.path.join(MODELS_DIR, "wc_ou25_xgb.pkl"))

    wc_matches_used = sum(s["matches"] for s in wc_stats.values()) // 2
    xg_data_points = sum(len(xgs["xg"]) for xgs in xg_stats.values())

    # ── Save metadata ─────────────────────────────────────────────────────────
    meta = {
        "trained_at":    datetime.utcnow().isoformat(),
        "training_rows": len(feat_df),
        "wc_matches_used": wc_matches_used,
        "xg_data_points": xg_data_points,
        "features":      FEATURES,
        "cv_1x2_acc":    round(float(np.mean(cv_scores)), 4),
        "cv_ou25_logloss": round(float(np.mean(cv_ou25)), 4),
        "best_xgb_1x2":  best_1x2,
        "best_xgb_ou25": best_ou25,
        "model_1x2": {
            "cv_mean_accuracy": round(float(np.mean(cv_scores)), 4),
            "best_params": best_1x2,
        },
        "model_ou25": {
            "cv_mean_logloss": round(float(np.mean(cv_ou25)), 4),
            "best_params": best_ou25,
        }
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    try:
        from core.training_reporter import write_training_report
        write_training_report(
            model_name="World Cup — XGBoost Ensemble",
            success=True,
            meta=meta,
            is_auto=is_auto,
        )
    except Exception as e:
        logger.error(f"Failed to write training report: {e}")
    
    # Logging Training Report
    logger.info(f"==== REPORTE DE ENTRENAMIENTO IA ====")
    logger.info(f"Partidos del Mundial 2026 usados: {len(new_rows) if new_rows else 0}")
    
    xg_points = sum(len(x["xg"]) for x in xg_stats.values())
    logger.info(f"Estadísticas xG de equipos activadas. {xg_points} partidos evaluados.")
        
    cv_acc_percent = np.mean(cv_scores) * 100
    logger.info(f"Precisión (Accuracy) alcanzada: {cv_acc_percent:.2f}%")
    logger.info(f"=======================================")

    logger.info(f"✅  Metadata saved → {META_PATH}")
    logger.info("\nRestart the backend to load new models.")


if __name__ == "__main__":
    train(is_auto=False)
