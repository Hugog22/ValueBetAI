"""
train_model.py — Advanced Multi-Model Training Pipeline
========================================================
Trains THREE independent XGBoost models on real football data (2014–2025):
  Leagues: La Liga + EPL (Premier League) + Champions League  ← multi-league

  Model A: 1X2 Result       → models/ensemble_1x2_xgb.pkl      (3 classes)
  Model B: Over/Under 2.5   → models/ensemble_ou2.5_xgb.pkl    (binary)
  Model C: Over/Under Corners → models/xgb_corners.json (when data available)

Key advances:
  ✅ Multi-league training (more data, better generalisation)
  ✅ league_encoded feature (model learns league-specific patterns)
  ✅ Exponential time-decay sample weights
  ✅ TimeSeriesSplit cross-validation (no future leakage)
  ✅ Optuna hyperparameter search (200 trials per model)
  ✅ 17+ engineered features (rolling + ELO + rest days + league)
  ✅ Probability calibration (isotonic regression hold-out)

Run from backend/:
    ./venv/bin/python -m scripts.train_model
"""

import os
import sys
import json
import logging
import math
from datetime import datetime

import numpy as np
import pandas as pd
import xgboost as xgb
import optuna
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, log_loss
from sklearn.calibration import CalibratedClassifierCV

optuna.logging.set_verbosity(optuna.logging.WARNING)   # silence trial noise

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH_MULTI  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "football_historical.csv")
DATA_PATH_LALIGA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "laliga_historical.csv")
# Prefer multi-league file when available
DATA_PATH    = DATA_PATH_MULTI if os.path.exists(DATA_PATH_MULTI) else DATA_PATH_LALIGA
MODELS_DIR   = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
META_PATH    = os.path.join(MODELS_DIR, "training_meta.json")

WINDOW        = 5        # rolling window in matches
DECAY_RATE    = 1.5      # exponential decay; 1.5 → match from 1yr ago ≈ 22% weight
MIN_WEIGHT    = 0.05     # floor weight for very old matches
OPTUNA_TRIALS = 200      # extreme trials per model
TSCV_SPLITS   = 5        # TimeSeriesSplit folds
MIN_CORNERS_ROWS = 200   # Minimum rows with corners data to train the corners model

# ELO parameters
ELO_BASE = 1500.0        # starting ELO for all teams
ELO_K    = 20.0          # standard football K-factor
CAL_HOLDOUT = 0.20       # fraction of most-recent data used to fit calibrators

TODAY = datetime.utcnow()


# ---------------------------------------------------------------------------
# 1. ELO rating computation (pre-match, no leakage)
# ---------------------------------------------------------------------------

def compute_elo_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Elo ratings for every team, match by match, in chronological order.
    Adds columns: home_elo, away_elo, elo_diff (home − away, pre-match).
    K=20, base=1500. The Elo is recorded BEFORE updating — no leakage.
    """
    df = df.sort_values("date").reset_index(drop=True)
    elo: dict[str, float] = {}

    home_elos, away_elos = [], []

    for _, row in df.iterrows():
        ht = row["home_team"]
        at = row["away_team"]
        eh = elo.get(ht, ELO_BASE)
        ea = elo.get(at, ELO_BASE)

        # Record pre-match ELO (no leakage)
        home_elos.append(eh)
        away_elos.append(ea)

        # Determine match outcome score (1=home win, 0.5=draw, 0=away win)
        try:
            hg = float(row["home_goals"])
            ag = float(row["away_goals"])
        except (ValueError, TypeError):
            continue   # Skip rows without goal data

        if hg > ag:
            score_home, score_away = 1.0, 0.0
        elif hg == ag:
            score_home = score_away = 0.5
        else:
            score_home, score_away = 0.0, 1.0

        # Expected score via logistic ELO formula
        exp_home = 1.0 / (1.0 + 10.0 ** ((ea - eh) / 400.0))
        exp_away = 1.0 - exp_home

        # Update ratings
        elo[ht] = eh + ELO_K * (score_home - exp_home)
        elo[at] = ea + ELO_K * (score_away - exp_away)

    df["home_elo"] = home_elos
    df["away_elo"] = away_elos
    df["elo_diff"] = df["home_elo"] - df["away_elo"]
    return df


# ---------------------------------------------------------------------------
# 2. Time-decay weights
# ---------------------------------------------------------------------------

def compute_sample_weights(dates: pd.Series) -> np.ndarray:
    """
    Exponential decay: w = exp(-λ * days_ago / 365)
    Floored at MIN_WEIGHT so very old data has marginal (not zero) influence.
    """
    def _w(date_str: str) -> float:
        try:
            dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = TODAY
        days_ago = max(0, (TODAY - dt).days)
        return max(MIN_WEIGHT, math.exp(-DECAY_RATE * days_ago / 365.0))

    return np.array([_w(d) for d in dates])


# ---------------------------------------------------------------------------
# 2. Rolling feature engineering
# ---------------------------------------------------------------------------

def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build rolling-average features without leakage (shift(1) before rolling)."""
    df = df.sort_values("date").reset_index(drop=True)

    # ---- Home-perspective records ----
    home_rec = df[["date", "home_team", "home_xg", "away_xg", "home_goals", "away_goals"]].copy()
    home_rec.columns = ["date", "team", "xg_for", "xg_ag", "goals_for", "goals_ag"]
    home_rec["pts"] = (home_rec["goals_for"] > home_rec["goals_ag"]).astype(int) * 3 + \
                      (home_rec["goals_for"] == home_rec["goals_ag"]).astype(int)

    # ---- Away-perspective records ----
    away_rec = df[["date", "away_team", "away_xg", "home_xg", "away_goals", "home_goals"]].copy()
    away_rec.columns = ["date", "team", "xg_for", "xg_ag", "goals_for", "goals_ag"]
    away_rec["pts"] = (away_rec["goals_for"] > away_rec["goals_ag"]).astype(int) * 3 + \
                      (away_rec["goals_for"] == away_rec["goals_ag"]).astype(int)

    ledger = pd.concat([home_rec, away_rec], ignore_index=True).sort_values("date").reset_index(drop=True)

    roll_cols = ["xg_for", "xg_ag", "goals_for", "pts"]
    for col in roll_cols:
        ledger[f"{col}_roll"] = (
            ledger.groupby("team")[col]
            .transform(lambda s: s.shift(1).rolling(WINDOW, min_periods=1).mean())
        )

    # ---- Corners rolling (only if available) ----
    has_corners = "corners_home" in df.columns
    if has_corners:
        home_c = df[["date", "home_team", "corners_home", "corners_away"]].copy()
        home_c.columns = ["date", "team", "corners_for", "corners_ag"]
        away_c = df[["date", "away_team", "corners_away", "corners_home"]].copy()
        away_c.columns = ["date", "team", "corners_for", "corners_ag"]
        corner_ledger = pd.concat([home_c, away_c], ignore_index=True).sort_values("date").reset_index(drop=True)
        corner_ledger = corner_ledger.dropna(subset=["corners_for"])
        if not corner_ledger.empty:
            for col in ["corners_for", "corners_ag"]:
                corner_ledger[f"{col}_roll"] = (
                    corner_ledger.groupby("team")[col]
                    .transform(lambda s: s.shift(1).rolling(WINDOW, min_periods=1).mean())
                )
            home_c_roll = corner_ledger.rename(columns={"team": "home_team"})[[
                "date", "home_team", "corners_for_roll", "corners_ag_roll"
            ]].rename(columns={"corners_for_roll": "home_corners_avg5", "corners_ag_roll": "home_corners_ag5"})
            away_c_roll = corner_ledger.rename(columns={"team": "away_team"})[[
                "date", "away_team", "corners_for_roll", "corners_ag_roll"
            ]].rename(columns={"corners_for_roll": "away_corners_avg5", "corners_ag_roll": "away_corners_ag5"})
            home_c_roll = home_c_roll.drop_duplicates(subset=["date", "home_team"])
            away_c_roll = away_c_roll.drop_duplicates(subset=["date", "away_team"])
            df = df.merge(home_c_roll, on=["date", "home_team"], how="left")
            df = df.merge(away_c_roll, on=["date", "away_team"], how="left")

    # ---- Build home/away own-form feature tables ----
    home_roll = ledger.rename(columns={"team": "home_team"})[[
        "date", "home_team", "xg_for_roll", "xg_ag_roll", "goals_for_roll", "pts_roll"
    ]].rename(columns={
        "xg_for_roll":   "home_xg_for_avg5",
        "xg_ag_roll":    "home_xg_ag_avg5",
        "goals_for_roll":"home_goals_avg5",
        "pts_roll":      "home_pts_avg5",
    }).drop_duplicates(subset=["date", "home_team"])

    away_roll = ledger.rename(columns={"team": "away_team"})[[
        "date", "away_team", "xg_for_roll", "xg_ag_roll", "goals_for_roll", "pts_roll"
    ]].rename(columns={
        "xg_for_roll":   "away_xg_for_avg5",
        "xg_ag_roll":    "away_xg_ag_avg5",
        "goals_for_roll":"away_goals_avg5",
        "pts_roll":      "away_pts_avg5",
    }).drop_duplicates(subset=["date", "away_team"])

    df = df.merge(home_roll, on=["date", "home_team"], how="left")
    df = df.merge(away_roll, on=["date", "away_team"], how="left")

    # ---- OPPONENT QUALITY features (Fase 1: Ajuste por Nivel del Oponente) ----
    # For each match, cross-join the rolling opponent form onto both sides.
    # home_opp_pts_avg5 = the AWAY team's rolling points (difficulty for home team)
    # away_opp_pts_avg5 = the HOME team's rolling points (difficulty for away team)
    opp_quality = ledger.rename(columns={"team": "away_team"})[[
        "date", "away_team", "pts_roll", "xg_ag_roll"
    ]].rename(columns={
        "pts_roll":   "home_opp_pts_avg5",   # away team's pts = difficulty for home
        "xg_ag_roll": "home_opp_xgag_avg5",  # how much the opponent concedes
    }).drop_duplicates(subset=["date", "away_team"])

    opp_quality_home = ledger.rename(columns={"team": "home_team"})[[
        "date", "home_team", "pts_roll", "xg_ag_roll"
    ]].rename(columns={
        "pts_roll":   "away_opp_pts_avg5",
        "xg_ag_roll": "away_opp_xgag_avg5",
    }).drop_duplicates(subset=["date", "home_team"])

    df = df.merge(opp_quality,      on=["date", "away_team"], how="left")
    df = df.merge(opp_quality_home, on=["date", "home_team"], how="left")

    # ---- xG Ajustado por defensa del rival ----
    # xg_adj = team xG / opponent's average xG conceded (their defensive strength)
    # Higher value = scored against a tough defense → more valuable
    eps = 1e-3
    df["home_xg_adj"] = df["home_xg_for_avg5"] / (df["home_opp_xgag_avg5"] + eps)
    df["away_xg_adj"] = df["away_xg_for_avg5"] / (df["away_opp_xgag_avg5"] + eps)

    # ---- Rest-days feature ----
    for col in ["rest_days_home", "rest_days_away"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---- Derived differentials ----
    df["xg_diff"]      = df["home_xg_for_avg5"] - df["away_xg_for_avg5"]
    df["form_diff"]    = df["home_pts_avg5"]     - df["away_pts_avg5"]
    df["opp_diff"]     = df["home_opp_pts_avg5"] - df["away_opp_pts_avg5"]  # SoS diff
    df["xg_adj_diff"]  = df["home_xg_adj"]       - df["away_xg_adj"]        # quality-adjusted xG

    return df


# ---------------------------------------------------------------------------
# 3. Feature sets
# ---------------------------------------------------------------------------

FEATURES_CORE = [
    # Own form
    "home_xg_for_avg5", "home_xg_ag_avg5", "home_goals_avg5", "home_pts_avg5",
    "away_xg_for_avg5", "away_xg_ag_avg5", "away_goals_avg5", "away_pts_avg5",
    # Opponent-adjusted
    "home_opp_pts_avg5", "home_opp_xgag_avg5",
    "away_opp_pts_avg5", "away_opp_xgag_avg5",
    "home_xg_adj", "away_xg_adj",
    # Differential signals
    "xg_diff", "form_diff", "opp_diff", "xg_adj_diff",
    # Fatigue
    "rest_days_home", "rest_days_away",
    # ELO — absolute team strength
    "home_elo", "away_elo", "elo_diff",
    # League encoding — model learns league-specific patterns
    "league_encoded",
]

FEATURES_CORNERS = FEATURES_CORE + ["home_corners_avg5", "away_corners_avg5", "home_corners_ag5", "away_corners_ag5"]



# ---------------------------------------------------------------------------
# 4. Optuna objective factories
# ---------------------------------------------------------------------------

def make_objective_multiclass(X: pd.DataFrame, y: pd.Series, weights: np.ndarray, n_classes: int, tscv):
    def objective(trial):
        params = {
            "objective":        "multi:softprob",
            "num_class":        n_classes,
            "eval_metric":      "mlogloss",
            "n_estimators":     3000,
            "early_stopping_rounds": 50,
            "max_depth":        trial.suggest_int("max_depth", 3, 10),
            "learning_rate":    trial.suggest_float("learning_rate", 0.001, 0.1, log=True),
            "subsample":        trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma":            trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha":        trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda":       trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "use_label_encoder": False,
            "random_state":     42,
        }
        lls = []
        for tr, va in tscv.split(X):
            w_tr = weights[tr]
            clf = xgb.XGBClassifier(**params)
            clf.fit(X.iloc[tr], y.iloc[tr], sample_weight=w_tr, 
                    eval_set=[(X.iloc[va], y.iloc[va])], verbose=False)
            probs = clf.predict_proba(X.iloc[va])
            lls.append(log_loss(y.iloc[va], probs))
        return np.mean(lls)
    return objective


def make_objective_binary(X: pd.DataFrame, y: pd.Series, weights: np.ndarray, tscv):
    def objective(trial):
        params = {
            "objective":        "binary:logistic",
            "eval_metric":      "logloss",
            "n_estimators":     3000,
            "early_stopping_rounds": 50,
            "max_depth":        trial.suggest_int("max_depth", 3, 10),
            "learning_rate":    trial.suggest_float("learning_rate", 0.001, 0.1, log=True),
            "subsample":        trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma":            trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha":        trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda":       trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "use_label_encoder": False,
            "random_state":     42,
        }
        lls = []
        for tr, va in tscv.split(X):
            w_tr = weights[tr]
            clf = xgb.XGBClassifier(**params)
            clf.fit(X.iloc[tr], y.iloc[tr], sample_weight=w_tr,
                    eval_set=[(X.iloc[va], y.iloc[va])], verbose=False)
            probs = clf.predict_proba(X.iloc[va])[:, 1]
            lls.append(log_loss(y.iloc[va], probs))
        return np.mean(lls)
    return objective


# ---------------------------------------------------------------------------
# 5. Train one model with Optuna + final fit + CV metrics
# ---------------------------------------------------------------------------

def train_and_save(
    X: pd.DataFrame,
    y: pd.Series,
    weights: np.ndarray,
    model_type: str,       # "multiclass" | "binary"
    n_classes: int,
    model_path: str,
    label: str,
) -> dict:
    logger.info(f"[{label}] Starting Optuna search ({OPTUNA_TRIALS} trials, {TSCV_SPLITS}-fold TimeSeriesSplit)…")
    tscv = TimeSeriesSplit(n_splits=TSCV_SPLITS)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))

    if model_type == "multiclass":
        study.optimize(make_objective_multiclass(X, y, weights, n_classes, tscv),
                       n_trials=OPTUNA_TRIALS, show_progress_bar=False)
    else:
        study.optimize(make_objective_binary(X, y, weights, tscv),
                       n_trials=OPTUNA_TRIALS, show_progress_bar=False)

    best = study.best_params
    logger.info(f"[{label}] Best params: {best}")
    logger.info(f"[{label}] Best CV LogLoss: {study.best_value:.4f}")

    # ---- CV accuracy with best params ----
    cv_accs = []
    cv_lls  = []
    if model_type == "multiclass":
        final_params = {
            "objective": "multi:softprob", "num_class": n_classes,
            "eval_metric": "mlogloss", "use_label_encoder": False, "random_state": 42,
            "n_estimators": 3000, "early_stopping_rounds": 50, **best,
        }
    else:
        final_params = {
            "objective": "binary:logistic",
            "eval_metric": "logloss", "use_label_encoder": False, "random_state": 42,
            "n_estimators": 3000, "early_stopping_rounds": 50, **best,
        }

    best_iters = []

    for tr, va in tscv.split(X):
        clf = xgb.XGBClassifier(**final_params)
        clf.fit(X.iloc[tr], y.iloc[tr], sample_weight=weights[tr], 
                eval_set=[(X.iloc[va], y.iloc[va])], verbose=False)
        preds = clf.predict(X.iloc[va])
        probs = clf.predict_proba(X.iloc[va])
        if model_type == "binary":
            probs = np.column_stack([1 - probs[:, 1], probs[:, 1]])
        cv_accs.append(accuracy_score(y.iloc[va], preds))
        cv_lls.append(log_loss(y.iloc[va], probs))
        if hasattr(clf, "best_iteration"):
            best_iters.append(clf.best_iteration)

    mean_acc = float(np.mean(cv_accs))
    mean_ll  = float(np.mean(cv_lls))
    optimal_iters = int(np.mean(best_iters)) if best_iters else 400
    
    logger.info(f"[{label}] CV Accuracy: {mean_acc:.4f}  CV LogLoss: {mean_ll:.4f}  Optimal Trees: {optimal_iters}")

    # ---- Final model on ALL data ----
    clean_params = final_params.copy()
    clean_params["n_estimators"] = optimal_iters
    clean_params.pop("early_stopping_rounds", None)
    
    final = xgb.XGBClassifier(**clean_params)
    final.fit(X, y, sample_weight=weights, verbose=False)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    final.save_model(model_path)
    logger.info(f"[{label}] ✅  Saved → {model_path}")

    # ---- Calibration (isotonic regression on temporal hold-out) ----
    # Use the most-recent CAL_HOLDOUT fraction — no random shuffle to avoid time-leakage.
    cal_path = model_path.replace(".json", "_cal.pkl")
    split_idx = max(1, int(len(X) * (1.0 - CAL_HOLDOUT)))
    X_cal = X.iloc[split_idx:].copy()
    y_cal = y.iloc[split_idx:].copy()

    if len(X_cal) >= 30:
        # CalibratedClassifierCV with cv=5 fits isotonic regression on the hold-out set
        # using cross-validation internally — compatible with all sklearn >= 1.0.
        calibrated = CalibratedClassifierCV(
            xgb.XGBClassifier(**clean_params), cv=5, method="isotonic"
        )
        calibrated.fit(X_cal, y_cal)
        joblib.dump(calibrated, cal_path)
        logger.info(f"[{label}] ✅  Calibrator saved → {cal_path} (n_cal={len(X_cal)})")
    else:
        logger.warning(f"[{label}] ⚠  Too few rows for calibration ({len(X_cal)}), skipping.")

    return {
        "cv_mean_accuracy": round(mean_acc, 4),
        "cv_mean_logloss":  round(mean_ll,  4),
        "best_params":      best,
        "training_rows":    len(X),
        "calibrated":       len(X_cal) >= 30,
    }


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------

def train():
    if not os.path.exists(DATA_PATH):
        logger.error(f"Data not found: {DATA_PATH}. Run fetch_historical_data.py first.")
        sys.exit(1)

    logger.info(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    logger.info(f"Raw rows: {len(df)}")

    # ---- League encoding (new feature for multi-league datasets) ----
    league_map = {"laliga": 0, "premier": 1, "champions": 2}
    if "league" in df.columns:
        df["league_encoded"] = df["league"].map(league_map).fillna(0).astype(int)
        breakdown = df["league"].value_counts().to_dict()
        logger.info(f"League distribution: {breakdown}")
    else:
        df["league_encoded"] = 0  # single-league backward compat

    logger.info("Building rolling features (rest days, xG, goals, form)…")
    df = add_rolling_features(df)

    # ---- ELO ratings (pre-match, chronological, no leakage) ----
    logger.info("Computing ELO ratings (K=20, base=1500)…")
    df = compute_elo_ratings(df)
    logger.info(f"ELO range: {df['home_elo'].min():.0f} – {df['home_elo'].max():.0f}")

    # ---- Fill rest_days NaN with median (first match of season etc.) ----
    for col in ["rest_days_home", "rest_days_away"]:
        median_val = df[col].median()
        df[col] = df[col].fillna(median_val if not np.isnan(median_val) else 14.0)

    # ---- Compute sample weights ----
    weights = compute_sample_weights(df["date"])

    # =====================================================================
    # MODEL A — 1X2 Result
    # =====================================================================
    logger.info("\n" + "="*60)
    logger.info("MODEL A: 1X2 Match Result")
    logger.info("="*60)

    features_a = FEATURES_CORE
    df_a = df.dropna(subset=features_a).copy()
    df_a["target"] = np.select(
        [df_a["home_goals"] > df_a["away_goals"],
         df_a["home_goals"] == df_a["away_goals"]],
        [0, 1],
        default=2,
    )
    X_a = df_a[features_a].astype(float)
    y_a = df_a["target"].astype(int)
    w_a = weights[df_a.index]

    dist_a = y_a.value_counts().sort_index()
    logger.info(f"Class dist — Home:{dist_a.get(0,0)} Draw:{dist_a.get(1,0)} Away:{dist_a.get(2,0)}")

    meta_a = train_and_save(X_a, y_a, w_a, "multiclass", 3,
                             os.path.join(MODELS_DIR, "xgb_1x2.json"), "1X2")

    # =====================================================================
    # MODEL B — Over/Under 2.5 Goals
    # =====================================================================
    logger.info("\n" + "="*60)
    logger.info("MODEL B: Over/Under 2.5 Goals")
    logger.info("="*60)

    df_b = df.dropna(subset=FEATURES_CORE).copy()
    df_b["target"] = ((df_b["home_goals"] + df_b["away_goals"]) > 2.5).astype(int)
    X_b = df_b[FEATURES_CORE].astype(float)
    y_b = df_b["target"].astype(int)
    w_b = weights[df_b.index]

    dist_b = y_b.value_counts().sort_index()
    logger.info(f"Class dist — Under:{dist_b.get(0,0)} Over:{dist_b.get(1,0)}")

    meta_b = train_and_save(X_b, y_b, w_b, "binary", 2,
                             os.path.join(MODELS_DIR, "xgb_ou25.json"), "O/U 2.5")

    # =====================================================================
    # MODEL C — Over/Under Corners (if data available)
    # =====================================================================
    meta_c = None
    corners_cols = ["home_corners_avg5", "away_corners_avg5", "home_corners_ag5", "away_corners_ag5"]
    has_corners_features = all(c in df.columns for c in corners_cols)

    if has_corners_features:
        df_c = df.dropna(subset=FEATURES_CORNERS).copy()
        # Also need actual corner totals to build the target
        if "corners_home" in df_c.columns and "corners_away" in df_c.columns:
            df_c = df_c.dropna(subset=["corners_home", "corners_away"])
            df_c["corners_home"] = pd.to_numeric(df_c["corners_home"], errors="coerce")
            df_c["corners_away"] = pd.to_numeric(df_c["corners_away"], errors="coerce")
            df_c = df_c.dropna(subset=["corners_home", "corners_away"])

        if len(df_c) >= MIN_CORNERS_ROWS:
            logger.info("\n" + "="*60)
            logger.info("MODEL C: Over/Under Corners")
            logger.info("="*60)

            # Compute threshold: median total corners in the dataset
            total_corners = df_c["corners_home"] + df_c["corners_away"]
            threshold = float(total_corners.median())
            logger.info(f"Corners threshold (median): {threshold:.1f}")

            df_c["target"] = (total_corners > threshold).astype(int)
            X_c = df_c[FEATURES_CORNERS].astype(float)
            y_c = df_c["target"].astype(int)
            w_c = weights[df_c.index]

            dist_c = y_c.value_counts().sort_index()
            logger.info(f"Class dist — Under:{dist_c.get(0,0)} Over:{dist_c.get(1,0)}")

            meta_c = train_and_save(X_c, y_c, w_c, "binary", 2,
                                     os.path.join(MODELS_DIR, "xgb_corners.json"), "Corners")
            meta_c["corners_threshold"] = threshold
        else:
            logger.info(f"⚠  Corners data: only {len(df_c)} rows (need ≥{MIN_CORNERS_ROWS}). Skipping Model C.")
            logger.info("   Run fetch_corners_data.py to enrich the dataset.")
    else:
        logger.info("⚠  No corner features in dataset. Skipping Model C.")
        logger.info("   Run fetch_corners_data.py first.")

    # =====================================================================
    # Save metadata
    # =====================================================================
    meta = {
        "trained_at":   TODAY.isoformat(),
        "seasons":      sorted(df["season"].unique().tolist()),
        "leagues":      sorted(df["league"].unique().tolist()) if "league" in df.columns else ["laliga"],
        "total_rows":   len(df),
        "decay_rate":   DECAY_RATE,
        "rolling_window": WINDOW,
        "features_core":  FEATURES_CORE,
        "model_1x2":    meta_a,
        "model_ou25":   meta_b,
        "model_corners": meta_c,
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"\n✅  All models trained. Metadata → {META_PATH}")
    logger.info("\nRestart the backend to load the new models:")
    logger.info("  ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload")


if __name__ == "__main__":
    train()
