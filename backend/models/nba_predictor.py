"""
nba_predictor.py
----------------
Loads and exposes NBA XGBoost models:
  Model A: nba_1x2_xgb.pkl  → P(Home win)
  Model B: nba_ou_xgb.pkl   → P(Total points > threshold)
"""

import os
import logging
import json

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.dirname(__file__)
META_PATH  = os.path.join(MODELS_DIR, "nba_training_meta.json")

PATH_WIN_XGB = os.path.join(MODELS_DIR, "nba_1x2_xgb.pkl")
PATH_OU_XGB  = os.path.join(MODELS_DIR, "nba_ou_xgb.pkl")

FEATURES_NBA = [
    "home_pts_avg10", "away_pts_avg10",
    "home_pts_allowed_avg10", "away_pts_allowed_avg10",
    "home_win_pct10", "away_win_pct10",
    "rest_days_home", "rest_days_away",
    "home_elo", "away_elo", "elo_diff",
]

# NBA league averages (fallback when no rolling data available)
NBA_DEFAULTS = {
    "home_pts_avg10":          112.0,
    "away_pts_avg10":          110.0,
    "home_pts_allowed_avg10":  110.0,
    "away_pts_allowed_avg10":  112.0,
    "home_win_pct10":          0.52,
    "away_win_pct10":          0.48,
    "rest_days_home":          2.0,
    "rest_days_away":          2.0,
    "home_elo":                1500.0,
    "away_elo":                1500.0,
    "elo_diff":                0.0,
}


class NBAPredictor:
    """Loads and runs two NBA market models (Win/Loss, O/U Total Points)."""

    def __init__(self):
        self._model_win  = None
        self._model_ou   = None
        self._ou_threshold = 220.5  # default; overridden from metadata
        self._ready = False

    def load_model(self):
        """Load NBA models from disk. Gracefully handles missing files."""
        if os.path.exists(PATH_WIN_XGB):
            self._model_win = joblib.load(PATH_WIN_XGB)
            logger.info("✅ NBA Win model loaded.")
        else:
            logger.warning(f"⚠️  NBA Win model not found at {PATH_WIN_XGB}. "
                           "Run scripts/train_model_nba.py to train it.")

        if os.path.exists(PATH_OU_XGB):
            self._model_ou = joblib.load(PATH_OU_XGB)
            logger.info("✅ NBA O/U model loaded.")
        else:
            logger.warning(f"⚠️  NBA O/U model not found at {PATH_OU_XGB}.")

        if os.path.exists(META_PATH):
            with open(META_PATH) as f:
                meta = json.load(f)
            self._ou_threshold = meta.get("ou_threshold", 220.5)
            logger.info(
                f"NBA models loaded — {meta.get('total_rows', '?')} games | "
                f"O/U threshold: {self._ou_threshold:.1f} pts | "
                f"Win acc={meta.get('model_win', {}).get('cv_mean_accuracy', '?')}"
            )

        self._ready = True

    def predict_game(self, features: dict) -> dict:
        """
        Predict Win/Loss and O/U for a NBA game.

        Parameters
        ----------
        features : dict
            Keys from FEATURES_NBA. Missing values fall back to NBA_DEFAULTS.

        Returns
        -------
        dict with:
            prob_home_win  : float
            prob_away_win  : float
            fair_odds_home : float
            fair_odds_away : float
            prob_over      : float  (P(total > threshold))
            prob_under     : float
            fair_odds_over : float
            fair_odds_under: float
            ou_threshold   : float
        """
        if not self._ready:
            self.load_model()

        fv = {**NBA_DEFAULTS, **features}
        X = pd.DataFrame([{k: fv[k] for k in FEATURES_NBA}]).astype(float)
        eps = 1e-6

        # ---- Win/Loss ----
        if self._model_win is not None:
            probs_win = self._model_win.predict_proba(X)[0]
            # Binary: [P(away wins), P(home wins)]
            prob_home = float(probs_win[1])
        else:
            # ELO-based fallback when model not trained yet
            elo_diff = fv["elo_diff"]
            prob_home = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))

        prob_away = 1.0 - prob_home

        # ---- Over/Under ----
        if self._model_ou is not None:
            probs_ou = self._model_ou.predict_proba(X)[0]
            prob_over = float(probs_ou[1])
        else:
            prob_over = 0.5  # neutral fallback

        prob_under = 1.0 - prob_over

        return {
            "prob_home_win":  round(prob_home,  4),
            "prob_away_win":  round(prob_away,  4),
            "fair_odds_home": round(1.0 / (prob_home  + eps), 2),
            "fair_odds_away": round(1.0 / (prob_away  + eps), 2),
            "prob_over":      round(prob_over,  4),
            "prob_under":     round(prob_under, 4),
            "fair_odds_over": round(1.0 / (prob_over  + eps), 2),
            "fair_odds_under":round(1.0 / (prob_under + eps), 2),
            "ou_threshold":   self._ou_threshold,
        }
