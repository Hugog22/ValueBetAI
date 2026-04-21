"""
train_model_nba.py
==================
Trains two XGBoost models for NBA game prediction:

  Model A: Win/Loss     → models/nba_1x2_xgb.pkl      (binary: home team wins)
  Model B: Over/Under   → models/nba_ou_xgb.pkl        (binary: total pts > threshold)

Features:
  - Rolling 10-game: pts_avg, pts_allowed_avg, win_pct
  - ELO ratings (K=25, NBA calibrated)
  - Rest days (recovery time between games heavily matters in NBA)
  - Home/Away advantage is implicit (home team always in "home" columns)

Run from backend/:
    ./venv/bin/python -m scripts.train_model_nba
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

optuna.logging.set_verbosity(optuna.logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "nba_historical.csv")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
META_PATH  = os.path.join(MODELS_DIR, "nba_training_meta.json")

DECAY_RATE    = 1.2      # NBA seasons more homogeneous; slightly less decay
MIN_WEIGHT    = 0.05
OPTUNA_TRIALS = 150
TSCV_SPLITS   = 5
CAL_HOLDOUT   = 0.20
TODAY = datetime.utcnow()

FEATURES_NBA = [
    "home_pts_avg10", "away_pts_avg10",
    "home_pts_allowed_avg10", "away_pts_allowed_avg10",
    "home_win_pct10", "away_win_pct10",
    "rest_days_home", "rest_days_away",
    "home_elo", "away_elo", "elo_diff",
]


# ---------------------------------------------------------------------------
# Time-decay weights
# ---------------------------------------------------------------------------

def compute_sample_weights(df: pd.DataFrame) -> np.ndarray:
    def _w(date_str: str) -> float:
        try:
            dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        except ValueError:
            dt = TODAY
        days_ago = max(0, (TODAY - dt).days)
        return max(MIN_WEIGHT, math.exp(-DECAY_RATE * days_ago / 365.0))
    return np.array([_w(d) for d in df["date"]])


# ---------------------------------------------------------------------------
# Optuna objectives (shared from football pattern)
# ---------------------------------------------------------------------------

def make_objective_binary(X, y, weights, tscv):
    def objective(trial):
        params = {
            "objective": "binary:logistic", "eval_metric": "logloss",
            "n_estimators": 2000, "early_stopping_rounds": 50,
            "max_depth":        trial.suggest_int("max_depth", 3, 8),
            "learning_rate":    trial.suggest_float("learning_rate", 0.005, 0.1, log=True),
            "subsample":        trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma":            trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha":        trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda":       trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "use_label_encoder": False, "random_state": 42,
        }
        lls = []
        for tr, va in tscv.split(X):
            clf = xgb.XGBClassifier(**params)
            clf.fit(X.iloc[tr], y.iloc[tr], sample_weight=weights[tr],
                    eval_set=[(X.iloc[va], y.iloc[va])], verbose=False)
            probs = clf.predict_proba(X.iloc[va])[:, 1]
            lls.append(log_loss(y.iloc[va], probs))
        return np.mean(lls)
    return objective


def train_and_save(X, y, weights, model_path: str, label: str) -> dict:
    logger.info(f"[{label}] Optuna search ({OPTUNA_TRIALS} trials)…")
    tscv = TimeSeriesSplit(n_splits=TSCV_SPLITS)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(make_objective_binary(X, y, weights, tscv),
                   n_trials=OPTUNA_TRIALS, show_progress_bar=False)

    best = study.best_params
    logger.info(f"[{label}] Best CV LogLoss: {study.best_value:.4f}")

    final_params = {
        "objective": "binary:logistic", "eval_metric": "logloss",
        "use_label_encoder": False, "random_state": 42,
        "n_estimators": 2000, "early_stopping_rounds": 50, **best,
    }

    cv_accs, cv_lls, best_iters = [], [], []
    for tr, va in tscv.split(X):
        clf = xgb.XGBClassifier(**final_params)
        clf.fit(X.iloc[tr], y.iloc[tr], sample_weight=weights[tr],
                eval_set=[(X.iloc[va], y.iloc[va])], verbose=False)
        preds = clf.predict(X.iloc[va])
        probs = clf.predict_proba(X.iloc[va])
        probs2 = np.column_stack([1 - probs[:, 1], probs[:, 1]])
        cv_accs.append(accuracy_score(y.iloc[va], preds))
        cv_lls.append(log_loss(y.iloc[va], probs2))
        if hasattr(clf, "best_iteration"):
            best_iters.append(clf.best_iteration)

    mean_acc = float(np.mean(cv_accs))
    mean_ll  = float(np.mean(cv_lls))
    optimal_iters = int(np.mean(best_iters)) if best_iters else 400
    logger.info(f"[{label}] CV Accuracy: {mean_acc:.4f}  CV LogLoss: {mean_ll:.4f}  Trees: {optimal_iters}")

    # Final model on all data
    clean_params = {**final_params, "n_estimators": optimal_iters}
    clean_params.pop("early_stopping_rounds", None)
    final_model = xgb.XGBClassifier(**clean_params)
    final_model.fit(X, y, sample_weight=weights, verbose=False)

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(final_model, model_path)
    logger.info(f"[{label}] ✅  Saved → {model_path}")

    # Calibration
    cal_path = model_path.replace(".pkl", "_cal.pkl")
    split_idx = max(1, int(len(X) * (1.0 - CAL_HOLDOUT)))
    X_cal, y_cal = X.iloc[split_idx:].copy(), y.iloc[split_idx:].copy()
    if len(X_cal) >= 50:
        calibrated = CalibratedClassifierCV(xgb.XGBClassifier(**clean_params), cv=5, method="isotonic")
        calibrated.fit(X_cal, y_cal)
        joblib.dump(calibrated, cal_path)
        logger.info(f"[{label}] ✅  Calibrator → {cal_path} (n_cal={len(X_cal)})")

    return {
        "cv_mean_accuracy": round(mean_acc, 4),
        "cv_mean_logloss":  round(mean_ll,  4),
        "best_params": best,
        "training_rows": len(X),
        "calibrated": len(X_cal) >= 50,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def train():
    if not os.path.exists(DATA_PATH):
        logger.error(f"NBA data not found: {DATA_PATH}. Run scripts/fetch_nba_data.py first.")
        sys.exit(1)

    logger.info(f"Loading NBA data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    logger.info(f"Raw rows: {len(df)}")

    # Drop rows with any missing features
    df = df.dropna(subset=FEATURES_NBA).copy()
    logger.info(f"Clean rows (no NaN in features): {len(df)}")

    weights = compute_sample_weights(df)

    # =========================================================================
    # MODEL A — Win/Loss (Home team wins?)
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("MODEL A (NBA): Home Team Win/Loss")
    logger.info("="*60)

    df_a = df.copy()
    X_a  = df_a[FEATURES_NBA].astype(float)
    y_a  = df_a["home_win"].astype(int)
    w_a  = weights[df_a.index]

    dist_a = y_a.value_counts().sort_index()
    logger.info(f"Class dist — Loss:{dist_a.get(0, 0)} Win:{dist_a.get(1, 0)}")

    path_a = os.path.join(MODELS_DIR, "nba_1x2_xgb.pkl")
    meta_a = train_and_save(X_a, y_a, w_a, path_a, "NBA-Win")

    # =========================================================================
    # MODEL B — Over/Under Total Points
    # =========================================================================
    logger.info("\n" + "="*60)
    logger.info("MODEL B (NBA): Over/Under Total Points")
    logger.info("="*60)

    # Use median total points as threshold (league evolves over seasons)
    ou_threshold = float(df["total_points"].median())
    logger.info(f"O/U threshold (median): {ou_threshold:.1f} total points")

    df_b = df.copy()
    df_b["target_ou"] = (df_b["total_points"] > ou_threshold).astype(int)
    X_b  = df_b[FEATURES_NBA].astype(float)
    y_b  = df_b["target_ou"].astype(int)
    w_b  = weights[df_b.index]

    dist_b = y_b.value_counts().sort_index()
    logger.info(f"Class dist — Under:{dist_b.get(0, 0)} Over:{dist_b.get(1, 0)}")

    path_b = os.path.join(MODELS_DIR, "nba_ou_xgb.pkl")
    meta_b = train_and_save(X_b, y_b, w_b, path_b, "NBA-O/U")

    # =========================================================================
    # Save metadata
    # =========================================================================
    meta = {
        "trained_at":     TODAY.isoformat(),
        "seasons":        sorted(df["season"].unique().tolist()),
        "total_rows":     len(df),
        "ou_threshold":   ou_threshold,
        "features":       FEATURES_NBA,
        "model_win":      meta_a,
        "model_ou":       meta_b,
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"\n✅  NBA models trained. Metadata → {META_PATH}")
    logger.info("Restart backend to load the new models.")


if __name__ == "__main__":
    train()
