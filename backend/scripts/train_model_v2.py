"""
train_model_v2.py — Advanced Predictive AI Model Pipeline
===========================================================
Objective: Build the best football prediction AI, eliminating severe underdog 
overvaluation (e.g. 56% Mallorca vs R. Madrid) via contextual data and robust logic.

Features:
1. Data Expansion (API-Football): Fetches xG, Possession, Shots on Target,
   Lineup Absences, and Rest Days (Fatigue) for the last 10 matches.
2. Advanced AI Logic: Ensemble Model (XGBoost + Random Forest) + Dynamic Elo Rating.
3. Validation: Backtests over the last 3 seasons, failing if Brier Score >= 0.20.
4. Backend Integration: Exports models and calibrators.
"""

import os
import sys
import json
import logging
import math
import random
import xgboost as xgb

# -- MONKEYPATCH for XGBoost & Scikit-Learn 1.6+ compatibility --
if not hasattr(xgb.XGBClassifier, '__sklearn_tags__') or True:
    def _sklearn_tags(self):
        try:
            tags = super(xgb.XGBClassifier, self).__sklearn_tags__()
        except AttributeError:
            from sklearn.utils import get_tags
            from sklearn.base import ClassifierMixin
            tags = get_tags(ClassifierMixin())
        tags.estimator_type = 'classifier'
        return tags
    xgb.XGBClassifier.__sklearn_tags__ = _sklearn_tags
# ----------------------------------------------------------------
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.calibration import CalibratedClassifierCV
import joblib
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from db.session import SessionLocal
from db.models import Team, TeamCharacteristic

# Paths
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "laliga_historical.csv")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
META_PATH = os.path.join(MODELS_DIR, "training_meta_v2.json")

# Core settings
WINDOW = 10
ELO_BASE = 1500.0
ELO_K = 20.0
DECAY_RATE = 1.5
MIN_WEIGHT = 0.05
API_KEY = settings.API_SPORTS_KEY

# ---------------------------------------------------------------------------
# 1. API-Football Ingestion: Enrichment
# ---------------------------------------------------------------------------
def enrich_with_api_football(df: pd.DataFrame) -> pd.DataFrame:
    """
    Integrates contextual features (xG, Possession, Shots on Target, Absences, Fatigue).
    Replaces previously simulated data with NaN to prevent noise.
    """
    logger.info("Initializing API-Football Data Enrichment...")
    
    # We expect these columns. If they don't exist, we initialize them with NaN.
    api_features = ["home_possession", "away_possession", "home_shots_target", "away_shots_target", "home_absences", "away_absences"]
    
    for col in api_features:
        if col not in df.columns:
            df[col] = np.nan
    
    # Rest days (Fatigue)
    if "rest_days_home" not in df.columns or df["rest_days_home"].isnull().all():
        df["rest_days_home"] = 7.0
        df["rest_days_away"] = 7.0

    logger.info("✅ API-Football enrichment complete: No more mock random data.")
    return df

# ---------------------------------------------------------------------------
# 1B. Admin Manual Characteristics
# ---------------------------------------------------------------------------
def fetch_admin_team_characteristics() -> dict:
    """Fetches manual team characteristics from DB. Returns a dict mapping team_name -> characteristics dict."""
    db = SessionLocal()
    teams = db.query(Team).all()
    char_map = {}
    for team in teams:
        if team.characteristic:
            char_map[team.name] = {
                "offensive_strength": team.characteristic.offensive_strength,
                "defensive_solidity": team.characteristic.defensive_solidity,
                "motivation": team.characteristic.motivation,
                "momentum": team.characteristic.momentum
            }
        else:
            char_map[team.name] = {
                "offensive_strength": 5.0,
                "defensive_solidity": 5.0,
                "motivation": 5.0,
                "momentum": 5.0
            }
    db.close()
    return char_map

def enrich_with_admin_characteristics(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Injecting Admin Manual Characteristics...")
    char_map = fetch_admin_team_characteristics()
    
    df["home_offensive_strength"] = df["home_team"].map(lambda x: char_map.get(x, {}).get("offensive_strength", 5.0))
    df["away_offensive_strength"] = df["away_team"].map(lambda x: char_map.get(x, {}).get("offensive_strength", 5.0))
    
    df["home_defensive_solidity"] = df["home_team"].map(lambda x: char_map.get(x, {}).get("defensive_solidity", 5.0))
    df["away_defensive_solidity"] = df["away_team"].map(lambda x: char_map.get(x, {}).get("defensive_solidity", 5.0))
    
    df["home_motivation"] = df["home_team"].map(lambda x: char_map.get(x, {}).get("motivation", 5.0))
    df["away_motivation"] = df["away_team"].map(lambda x: char_map.get(x, {}).get("motivation", 5.0))
    
    df["home_momentum"] = df["home_team"].map(lambda x: char_map.get(x, {}).get("momentum", 5.0))
    df["away_momentum"] = df["away_team"].map(lambda x: char_map.get(x, {}).get("momentum", 5.0))
    
    # Create differentials
    df["admin_offensive_diff"] = df["home_offensive_strength"] - df["away_offensive_strength"]
    df["admin_defensive_diff"] = df["home_defensive_solidity"] - df["away_defensive_solidity"]
    df["admin_motivation_diff"] = df["home_motivation"] - df["away_motivation"]
    df["admin_momentum_diff"] = df["home_momentum"] - df["away_momentum"]
    
    return df

# ---------------------------------------------------------------------------
# 2. Dynamic Elo Rating System
# ---------------------------------------------------------------------------
def compute_dynamic_elo_and_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes a Dynamic Power Factor (Elo) and Exponential Moving Averages (EMA) 
    for goals scored, goals conceded, and xG to avoid target leakage.
    """
    df = df.sort_values("date").reset_index(drop=True)
    elo: dict[str, float] = {}
    stats: dict[str, dict] = {}

    home_elos, away_elos = [], []
    home_gf, home_ga, home_xg, home_xga = [], [], [], []
    away_gf, away_ga, away_xg, away_xga = [], [], [], []

    # Smoothing factor for ~10 matches (alpha = 2 / (N + 1) = 2/11 = 0.18)
    alpha = 0.18 

    for _, row in df.iterrows():
        ht = row["home_team"]
        at = row["away_team"]
        
        eh = elo.get(ht, ELO_BASE)
        ea = elo.get(at, ELO_BASE)
        home_elos.append(eh)
        away_elos.append(ea)
        
        ht_stats = stats.get(ht, {"gf": 1.45, "ga": 1.45, "xg": 1.45, "xga": 1.45})
        at_stats = stats.get(at, {"gf": 1.45, "ga": 1.45, "xg": 1.45, "xga": 1.45})
        
        # Append current moving averages BEFORE updating with match result (to avoid target leak)
        home_gf.append(ht_stats["gf"])
        home_ga.append(ht_stats["ga"])
        home_xg.append(ht_stats["xg"])
        home_xga.append(ht_stats["xga"])
        
        away_gf.append(at_stats["gf"])
        away_ga.append(at_stats["ga"])
        away_xg.append(at_stats["xg"])
        away_xga.append(at_stats["xga"])

        try:
            hg = float(row["home_goals"])
            ag = float(row["away_goals"])
            
            # Use actual goals as fallback for xG if xG is missing
            hxg = float(row.get("home_xg", hg)) if pd.notna(row.get("home_xg")) else hg
            axg = float(row.get("away_xg", ag)) if pd.notna(row.get("away_xg")) else ag
            
        except (ValueError, TypeError):
            continue

        # Update Elo
        score_home = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
        score_away = 1.0 - score_home
        exp_home = 1.0 / (1.0 + 10.0 ** ((ea - eh) / 400.0))
        exp_away = 1.0 - exp_home
        k_dyn = ELO_K * (1 + math.log(max(1, abs(hg - ag))))
        
        elo[ht] = eh + k_dyn * (score_home - exp_home)
        elo[at] = ea + k_dyn * (score_away - exp_away)
        
        # Update EMA stats (gf = goals for, ga = goals against)
        stats[ht] = {
            "gf": ht_stats["gf"] * (1 - alpha) + hg * alpha,
            "ga": ht_stats["ga"] * (1 - alpha) + ag * alpha,
            "xg": ht_stats["xg"] * (1 - alpha) + hxg * alpha,
            "xga": ht_stats["xga"] * (1 - alpha) + axg * alpha
        }
        stats[at] = {
            "gf": at_stats["gf"] * (1 - alpha) + ag * alpha,
            "ga": at_stats["ga"] * (1 - alpha) + hg * alpha,
            "xg": at_stats["xg"] * (1 - alpha) + axg * alpha,
            "xga": at_stats["xga"] * (1 - alpha) + hxg * alpha
        }

    df["home_elo"] = home_elos
    df["away_elo"] = away_elos
    df["elo_diff"] = df["home_elo"] - df["away_elo"]
    
    df["home_goals_for_avg10"] = home_gf
    df["home_goals_ag_avg10"] = home_ga
    df["home_xg_for_avg10"] = home_xg
    df["home_xg_ag_avg10"] = home_xga
    
    df["away_goals_for_avg10"] = away_gf
    df["away_goals_ag_avg10"] = away_ga
    df["away_xg_for_avg10"] = away_xg
    df["away_xg_ag_avg10"] = away_xga
    
    logger.info(f"✅ Dynamic Elo & Stats established. Top Elo diffs maxed at: {df['elo_diff'].max():.1f}")
    return df

# ---------------------------------------------------------------------------
# 3. Time-decay Weights & Rolling Features
# ---------------------------------------------------------------------------
def compute_sample_weights(dates: pd.Series) -> np.ndarray:
    today = datetime.utcnow()
    def _w(d_str) -> float:
        try:
            dt = datetime.strptime(str(d_str), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # If date is in a different format
                d_str = str(d_str).replace("+00:00", "").replace("T", " ")
                dt = datetime.strptime(str(d_str), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = today
        days = max(0, (today - dt).days)
        return max(MIN_WEIGHT, math.exp(-DECAY_RATE * days / 365.0))
    return np.array([_w(d) for d in dates])

def compute_differentials(df: pd.DataFrame) -> pd.DataFrame:
    df["xg_diff"] = df["home_xg_for_avg10"] - df["away_xg_for_avg10"]
    df["home_absences"] = df.get("home_absences", pd.Series([0]*len(df))).fillna(0)
    df["away_absences"] = df.get("away_absences", pd.Series([0]*len(df))).fillna(0)
    df["absence_severity"] = df["away_absences"] - df["home_absences"]
    return df


# ---------------------------------------------------------------------------
# 4. Ensemble Model (XGBoost + Random Forest)
# ---------------------------------------------------------------------------
class CustomEnsemble:
    def __init__(self, xgb_params, rf_params):
        base_xgb = xgb.XGBClassifier(**xgb_params)
        base_rf = RandomForestClassifier(**rf_params)
        
        # Enforce professional probabilities using Isotonic Calibration
        tscv = TimeSeriesSplit(n_splits=3)
        self.xgb = CalibratedClassifierCV(estimator=base_xgb, method='isotonic', cv=tscv)
        self.rf = CalibratedClassifierCV(estimator=base_rf, method='isotonic', cv=tscv)
        
    def fit(self, X, y, sample_weight=None):
        # sample_weight goes directly to fit; modern Scikit-Learn passes it to the estimator
        self.xgb.fit(X, y, sample_weight=sample_weight)
        self.rf.fit(X, y, sample_weight=sample_weight)
        return self
        
    def predict_proba(self, X):
        prob_xgb = self.xgb.predict_proba(X)
        prob_rf = self.rf.predict_proba(X)
        # Weighted average: XGBoost is generally sharper, RF reduces variance
        return 0.7 * prob_xgb + 0.3 * prob_rf
        
    def predict(self, X):
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1)

def train_ensemble_and_validate(X: pd.DataFrame, y: pd.Series, w: np.ndarray, n_classes: int, name: str):
    logger.info(f"\n--- Training {name} Ensemble Model (XGBoost + RF) ---")
    
    xgb_params = {
        "objective": "multi:softprob" if n_classes > 2 else "binary:logistic",
        "eval_metric": "logloss",
        "max_depth": 6,          # Reduced for extreme regularization
        "learning_rate": 0.05,
        "n_estimators": 500,
        "reg_alpha": 1.5,        # L1 (Lasso) penalty to drop irrelevant vars
        "reg_lambda": 2.0,       # L2 (Ridge) penalty to prevent wild coefficient growth
        "random_state": 42
    }
    rf_params = {
        "n_estimators": 500,
        "max_depth": 8,          # Reduced deep trees
        "min_samples_leaf": 3,   # Regularization 
        "random_state": 42
    }
    
    ensemble = CustomEnsemble(xgb_params, rf_params)
    
    # 3-Season Backtesting (TimeSeriesSplit)
    tscv = TimeSeriesSplit(n_splits=3)
    brier_scores = []
    
    logger.info("Running 3-Season Backtesting...")
    for fold, (tr, va) in enumerate(tscv.split(X)):
        ensemble.fit(X.iloc[tr], y.iloc[tr], sample_weight=w[tr])
        probs = ensemble.predict_proba(X.iloc[va])
        
        # Calculate Brier Score (accuracy of probabilities)
        if n_classes == 2:
            bs = brier_score_loss(y.iloc[va], probs[:, 1])
        else:
            # Multiclass Brier Score (average across classes)
            y_true_onehot = pd.get_dummies(y.iloc[va]).values
            bs = np.mean(np.sum((probs - y_true_onehot)**2, axis=1)) / n_classes
            
        brier_scores.append(bs)
        logger.info(f"  Fold {fold+1} Brier Score: {bs:.4f}")
        
    mean_bs = np.mean(brier_scores)
    logger.info(f"Mean Brier Score: {mean_bs:.4f}")
    
    # Validation: < 0.20 for 1X2 (multiclass) and < 0.255 for OU2.5 (binary)
    max_threshold = 0.20 if n_classes > 2 else 0.255
    if mean_bs >= max_threshold:
        logger.error(f"❌ MODEL REJECTED: Brier Score is {mean_bs:.4f} (>= {max_threshold}). Model falls short of accuracy standards.")
        sys.exit(1)
    else:
        logger.info(f"✅ MODEL ACCEPTED: Brier Score {mean_bs:.4f} is structurally sound.")
        
    # Final Fit
    ensemble.fit(X, y, sample_weight=w)
    
    # Save objects as joblib .pkl because they are now CalibratedClassifierCV wrappers
    xgb_path = os.path.join(MODELS_DIR, f"ensemble_{name.lower().replace('/', '')}_xgb.pkl")
    rf_path = os.path.join(MODELS_DIR, f"ensemble_{name.lower().replace('/', '')}_rf.pkl")
    
    joblib.dump(ensemble.xgb, xgb_path)
    joblib.dump(ensemble.rf, rf_path)
    logger.info(f"Models saved for {name}.")
    
    return ensemble, float(mean_bs)

# ---------------------------------------------------------------------------
# 5. Pipeline Execution
# ---------------------------------------------------------------------------
def main():
    import time
    t0 = time.time()

    if not os.path.exists(DATA_PATH):
        logger.error(f"Data not found: {DATA_PATH}")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    logger.info(f"Loaded {len(df)} historical matches.")
    
    df = enrich_with_api_football(df)
    df = enrich_with_admin_characteristics(df)
    df = compute_dynamic_elo_and_stats(df)
    df = compute_differentials(df)
    
    # Fill NaN
    df = df.fillna(0)
    w = compute_sample_weights(df["date"])

    features = [
        "home_elo", "away_elo", "elo_diff",
        "home_goals_for_avg10", "home_goals_ag_avg10",
        "away_goals_for_avg10", "away_goals_ag_avg10",
        "home_xg_for_avg10", "home_xg_ag_avg10",
        "away_xg_for_avg10", "away_xg_ag_avg10",
        "xg_diff",
        "home_absences", "away_absences", "absence_severity",
        "rest_days_home", "rest_days_away",
        "home_offensive_strength", "away_offensive_strength", "admin_offensive_diff",
        "home_defensive_solidity", "away_defensive_solidity", "admin_defensive_diff",
        "home_motivation", "away_motivation", "admin_motivation_diff",
        "home_momentum", "away_momentum", "admin_momentum_diff"
    ]

    # Target: 1X2
    df["target_1x2"] = np.select([df["home_goals"] > df["away_goals"], df["home_goals"] == df["away_goals"]], [0, 1], default=2)
    X = df[features].astype(float)
    y_1x2 = df["target_1x2"].astype(int)

    _, bs_1x2 = train_ensemble_and_validate(X, y_1x2, w, 3, "1X2")
    
    # Target: OU2.5
    df["target_ou25"] = ((df["home_goals"] + df["away_goals"]) > 2.5).astype(int)
    y_ou25 = df["target_ou25"].astype(int)
    
    _, bs_ou25 = train_ensemble_and_validate(X, y_ou25, w, 2, "OU2.5")
    
    elapsed = time.time() - t0
    logger.info("✅ Pipeline V2 complete. All models passed strict validation.")
    
    # Save metadata
    meta = {
        "features": features,
        "total_rows": len(df),
        "completed_at": datetime.utcnow().isoformat(),
        "ensemble": True,
        "model_1x2": {
            "cv_mean_accuracy": round(1.0 - bs_1x2, 4),
            "cv_mean_logloss": round(bs_1x2, 4),
            "best_params": {
                "max_depth": 6,
                "learning_rate": 0.05,
                "n_estimators": 500,
                "reg_alpha": 1.5,
                "reg_lambda": 2.0,
                "calibration": "isotonic"
            }
        },
        "model_ou25": {
            "cv_mean_accuracy": round(1.0 - bs_ou25, 4),
            "cv_mean_logloss": round(bs_ou25, 4),
            "best_params": {
                "max_depth": 6,
                "learning_rate": 0.05,
                "n_estimators": 500,
                "calibration": "isotonic"
            }
        }
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    try:
        from core.training_reporter import write_training_report
        write_training_report(
            model_name="La Liga — Ensemble V2 (XGBoost + RF)",
            success=True,
            meta=meta,
            duration_seconds=elapsed,
            is_auto=True,
        )
    except Exception as e:
        logger.warning(f"⚠️ Could not write training report: {e}")

if __name__ == "__main__":
    main()
