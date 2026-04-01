"""
predictor.py
------------
Loads and exposes three trained XGBoost models:

  Model A: xgb_1x2.json      → P(Home win), P(Draw), P(Away win)
  Model B: xgb_ou25.json     → P(Over 2.5 goals)
  Model C: xgb_corners.json  → P(Over corners threshold)

All models use 12–16 rolling-average features computed by train_model.py.
Missing feature values fall back to historical La Liga averages (DEFAULTS).
"""

import json
import logging
import os

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.dirname(__file__)
META_PATH  = os.path.join(MODELS_DIR, "training_meta.json")

PATH_1X2_XGB  = os.path.join(MODELS_DIR, "ensemble_1x2_xgb.pkl")
PATH_1X2_RF   = os.path.join(MODELS_DIR, "ensemble_1x2_rf.pkl")
PATH_OU25_XGB = os.path.join(MODELS_DIR, "ensemble_ou2.5_xgb.pkl")
PATH_OU25_RF  = os.path.join(MODELS_DIR, "ensemble_ou2.5_rf.pkl")
PATH_CORNERS  = os.path.join(MODELS_DIR, "xgb_corners.json")

FEATURES_CORE = [
    "home_elo", "away_elo", "elo_diff",
    "home_xg_for_avg10", "away_xg_for_avg10", "xg_diff",
    "home_possession_avg10", "away_possession_avg10", "possession_diff",
    "home_shots_target_avg10", "away_shots_target_avg10", "shots_diff",
    "home_absences", "away_absences", "absence_severity",
    "rest_days_home", "rest_days_away"
]

FEATURES_CORNERS = FEATURES_CORE + [
    "home_corners_avg5", "away_corners_avg5", "home_corners_ag5", "away_corners_ag5"
]


# Historical La Liga averages — used as cold-start defaults
DEFAULTS: dict[str, float] = {
    # Own form
    "home_xg_for_avg5":  1.45,
    "home_xg_ag_avg5":   1.05,
    "home_goals_avg5":   1.50,
    "home_pts_avg5":     1.60,
    "away_xg_for_avg5":  1.10,
    "away_xg_ag_avg5":   1.40,
    "away_goals_avg5":   1.10,
    "away_pts_avg5":     1.20,
    # Opponent quality (average La Liga opponent)
    "home_opp_pts_avg5":  1.20,
    "home_opp_xgag_avg5": 1.25,
    "away_opp_pts_avg5":  1.60,
    "away_opp_xgag_avg5": 1.05,
    "home_xg_adj":       1.16,
    "away_xg_adj":       0.88,
    # Differentials
    "xg_diff":           0.35,
    "form_diff":         0.40,
    "opp_diff":         -0.40,
    "xg_adj_diff":       0.28,
    # Fatigue
    "rest_days_home":    7.0,
    "rest_days_away":    7.0,
    # ELO (neutral average team)
    "home_elo":          1500.0,
    "away_elo":          1500.0,
    "elo_diff":          0.0,
    # Corners (model C)
    "home_corners_avg5": 5.2,
    "away_corners_avg5": 4.3,
    "home_corners_ag5":  4.3,
    "away_corners_ag5":  5.2,
}


def _make_model() -> xgb.XGBClassifier:
    return xgb.XGBClassifier(use_label_encoder=False, random_state=42)


class ValueBetPredictor:
    """Loads and runs three market models (1X2, O/U 2.5, O/U Corners)."""

    def __init__(self):
        self._model_1x2_xgb  = _make_model()
        self._model_ou25_xgb = _make_model()
        self._model_1x2_rf   = None
        self._model_ou25_rf  = None
        self._model_corners  = _make_model()
        
        self._corners_threshold: float = 9.0
        self._has_corners = False
        self._ready       = False

    def load_model(self):
        """Load ensemble models from disk."""
        for path, name in [(PATH_1X2_XGB, "1X2_XGB"), (PATH_OU25_XGB, "O/U2.5_XGB"), (PATH_1X2_RF, "1X2_RF"), (PATH_OU25_RF, "O/U2.5_RF")]:
            if not os.path.exists(path):
                logger.error(f"Missing ensemble part: {path}")

        if os.path.exists(PATH_1X2_XGB):
            self._model_1x2_xgb = joblib.load(PATH_1X2_XGB)
        if os.path.exists(PATH_OU25_XGB):
            self._model_ou25_xgb = joblib.load(PATH_OU25_XGB)
            
        if os.path.exists(PATH_1X2_RF):
            self._model_1x2_rf = joblib.load(PATH_1X2_RF)
        if os.path.exists(PATH_OU25_RF):
            self._model_ou25_rf = joblib.load(PATH_OU25_RF)

        if os.path.exists(PATH_CORNERS):
            self._model_corners.load_model(PATH_CORNERS)
            self._has_corners = True

        if os.path.exists(META_PATH):
            with open(META_PATH) as f:
                meta = json.load(f)
            m1 = meta.get("model_1x2", {})
            m2 = meta.get("model_ou25", {})
            mc = meta.get("model_corners") or {}
            if mc:
                self._corners_threshold = mc.get("corners_threshold", 9.0)
            logger.info(
                f"Models loaded — {len(meta.get('seasons', []))} seasons "
                f"({meta.get('total_rows','?')} rows) | "
                f"1X2 acc={m1.get('cv_mean_accuracy','?')} | "
                f"O/U2.5 acc={m2.get('cv_mean_accuracy','?')} | "
                f"Corners={'✓' if self._has_corners else '✗'}"
            )
        else:
            logger.info("Models loaded from disk (no metadata file).")

        self._ready = True

    def _predict_ensemble(self, xgb_model, rf_model, X: pd.DataFrame) -> np.ndarray:
        """
        Return the 70/30 blended probability for the ensemble.
        """
        prob_xgb = np.array(xgb_model.predict_proba(X))
        if rf_model is not None:
            prob_rf = np.array(rf_model.predict_proba(X))
            return 0.7 * prob_xgb + 0.3 * prob_rf
        return prob_xgb

    def predict_match(self, features: dict) -> dict:
        """
        Predict all available markets for a match.

        Parameters
        ----------
        features : dict
            Any subset of FEATURES_CORE (+ FEATURES_CORNERS for corners predictions).
            Missing keys fall back to DEFAULTS.

        Returns
        -------
        dict with:
            probabilities     : {"home", "draw", "away"}
            fair_odds_1x2     : {"home", "draw", "away"}
            prob_over25       : float
            fair_odds_ou25    : {"over", "under"}
            prob_over_corners : float | None
            fair_odds_corners : {"over", "under"} | None
            corners_threshold : float | None
        """
        if not self._ready:
            self.load_model()

        fv = {**DEFAULTS, **features}

        # ---- 1X2 (Ensemble) ----
        X_1x2 = pd.DataFrame([{k: fv[k] for k in FEATURES_CORE}]).astype(float)
        probs_1x2 = self._predict_ensemble(self._model_1x2_xgb, self._model_1x2_rf, X_1x2)[0]
        eps = 1e-6

        # ---- O/U 2.5 (Ensemble) ----
        X_ou25 = pd.DataFrame([{k: fv[k] for k in FEATURES_CORE}]).astype(float)
        probs_ou25 = self._predict_ensemble(self._model_ou25_xgb, self._model_ou25_rf, X_ou25)[0]
        prob_over25 = float(probs_ou25[1])

        # ---- Corners ----
        prob_over_corners = None
        fair_corners = None
        if self._has_corners:
            X_c = pd.DataFrame([{k: fv.get(k, DEFAULTS.get(k, 0.0)) for k in FEATURES_CORNERS}]).astype(float)
            probs_c = self._model_corners.predict_proba(X_c)[0]
            prob_over_corners = float(probs_c[1])
            fair_corners = {
                "over":  round(1.0 / (prob_over_corners + eps), 2),
                "under": round(1.0 / (1 - prob_over_corners + eps), 2),
            }

        # Helper: numpy.float32 → Python float (JSON-serializable)
        def _f(v) -> float:
            return float(v)

        p_home  = _f(probs_1x2[0])
        p_draw  = _f(probs_1x2[1])
        p_away  = _f(probs_1x2[2])

        return {
            "probabilities": {
                "home": round(p_home,  4),
                "draw": round(p_draw,  4),
                "away": round(p_away,  4),
            },
            "fair_odds_1x2": {
                "home": round(1.0 / (p_home  + eps), 2),
                "draw": round(1.0 / (p_draw  + eps), 2),
                "away": round(1.0 / (p_away  + eps), 2),
            },
            "prob_over25":   round(prob_over25, 4),
            "fair_odds_ou25": {
                "over":  round(1.0 / (prob_over25 + eps), 2),
                "under": round(1.0 / (1 - prob_over25 + eps), 2),
            },
            "prob_over_corners":  prob_over_corners,
            "fair_odds_corners":  fair_corners,
            "corners_threshold":  self._corners_threshold if self._has_corners else None,
        }

    def detect_value(self, pred: dict, book_odds: dict) -> list[dict]:
        """
        Return all value bets across all available markets.
        book_odds keys: home, draw, away, over25, under25, over_corners, under_corners
        """
        value_bets = []

        def _check(label: str, market: str, fair: float, actual: float):
            if actual and actual > fair:
                edge = (actual / fair - 1.0) * 100
                value_bets.append({
                    "label": label, "market": market,
                    "fair_odds": round(fair, 2),
                    "actual_odds": round(actual, 2),
                    "edge_pct": round(edge, 2),
                })

        f1x2 = pred["fair_odds_1x2"]
        _check("Victoria Local",      "1x2",   f1x2["home"], book_odds.get("home", 0))
        _check("Empate",              "1x2",   f1x2["draw"], book_odds.get("draw", 0))
        _check("Victoria Visitante",  "1x2",   f1x2["away"], book_odds.get("away", 0))

        fou25 = pred["fair_odds_ou25"]
        _check("Más de 2.5 Goles",   "ou25",  fou25["over"],  book_odds.get("over25", 0))
        _check("Menos de 2.5 Goles", "ou25",  fou25["under"], book_odds.get("under25", 0))

        if pred.get("fair_odds_corners"):
            fc = pred["fair_odds_corners"]
            thr = pred.get("corners_threshold", 9.0)
            _check(f"Más de {thr} Córners",   "corners", fc["over"],  book_odds.get("over_corners", 0))
            _check(f"Menos de {thr} Córners", "corners", fc["under"], book_odds.get("under_corners", 0))

        return value_bets
