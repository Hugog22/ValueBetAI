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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "world_cup_historical.csv")
SQUAD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "world_cup_squads.json")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
META_PATH  = os.path.join(MODELS_DIR, "wc_training_meta.json")

TSCV_SPLITS   = 3   # fewer splits — WC has limited data (~400 matches total)
OPTUNA_TRIALS = 20
TODAY = datetime.utcnow()


# ---------------------------------------------------------------------------
# Feature engineering for World Cup
# ---------------------------------------------------------------------------

def _days_ago(date_str: str) -> float:
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return max(0, (TODAY - dt).days)
    except Exception:
        return 365.0


def compute_sample_weights(df: pd.DataFrame) -> np.ndarray:
    """Exponential decay: recent WC finals matter more than 1998 groups."""
    decay = 2.0  # stronger decay for WC — recency is more important
    weights = []
    for _, row in df.iterrows():
        days   = _days_ago(str(row.get("date", TODAY)))
        w      = max(0.05, math.exp(-decay * days / 365.0))
        # Knockout games are more informative → double weight
        if row.get("is_knockout", 0) == 1:
            w *= 2.0
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


def build_features(df: pd.DataFrame) -> pd.DataFrame:
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
]


def train():
    """Run full training pipeline for World Cup models."""
    import xgboost as xgb
    import lightgbm as lgb
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.metrics import accuracy_score, log_loss

    if not os.path.exists(DATA_PATH):
        logger.error(f"No data found at {DATA_PATH}. Run fetch_world_cup_data.py first.")
        sys.exit(1)

    logger.info(f"Loading data from {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    logger.info(f"Raw rows: {len(df)}")

    logger.info("Building features…")
    feat_df = build_features(df)
    logger.info(f"Feature rows: {len(feat_df)}")

    if len(feat_df) < 30:
        logger.error("Not enough data to train. Need at least 30 matches.")
        sys.exit(1)

    weights = compute_sample_weights(df.sort_values("date").reset_index(drop=True))
    weights = weights[:len(feat_df)]

    X = feat_df[FEATURES].astype(float)
    tscv = TimeSeriesSplit(n_splits=TSCV_SPLITS)

    # ── MODEL A: 1X2 ─────────────────────────────────────────────────────────
    logger.info("Training 1X2 model…")
    y_1x2 = np.select(
        [feat_df["_home_goals"] > feat_df["_away_goals"],
         feat_df["_home_goals"] == feat_df["_away_goals"]],
        [0, 1], default=2
    )

    # ── ENSEMBLE DEFINITION 1X2 ───────────────────────────────────────────────
    xgb_1x2 = xgb.XGBClassifier(
        objective="multi:softprob", num_class=3,
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, random_state=42, eval_metric="mlogloss",
    )
    lgb_1x2 = lgb.LGBMClassifier(
        objective="multiclass", num_class=3,
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1,
    )
    rf_1x2 = RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_split=5, random_state=42,
    )
    
    ensemble_1x2 = VotingClassifier(
        estimators=[('xgb', xgb_1x2), ('lgb', lgb_1x2), ('rf', rf_1x2)],
        voting='soft'
    )

    # Cross-validation
    cv_scores = []
    for tr, va in tscv.split(X):
        ensemble_1x2.fit(X.iloc[tr], y_1x2[tr])
        preds = ensemble_1x2.predict(X.iloc[va])
        cv_scores.append(accuracy_score(y_1x2[va], preds))
    logger.info(f"1X2 Ensemble CV accuracy: {np.mean(cv_scores):.4f}")

    # Final model on all data + calibration
    split_idx = max(1, int(len(X) * 0.80))
    cal_1x2 = CalibratedClassifierCV(
        ensemble_1x2, cv=3, method="isotonic"
    )
    cal_1x2.fit(X.iloc[:split_idx], y_1x2[:split_idx])
    joblib.dump(cal_1x2, os.path.join(MODELS_DIR, "wc_1x2_xgb.pkl"))
    logger.info("✅  wc_1x2_xgb.pkl saved")

    # ── MODEL B: O/U 2.5 ─────────────────────────────────────────────────────
    logger.info("Training O/U 2.5 model…")
    y_ou25 = ((feat_df["_home_goals"] + feat_df["_away_goals"]) > 2.5).astype(int).values

    # ── ENSEMBLE DEFINITION O/U 2.5 ──────────────────────────────────────────
    xgb_ou = xgb.XGBClassifier(
        objective="binary:logistic", n_estimators=300,
        max_depth=4, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, use_label_encoder=False,
        random_state=42, eval_metric="logloss",
    )
    lgb_ou = lgb.LGBMClassifier(
        objective="binary", n_estimators=300,
        max_depth=4, learning_rate=0.05, subsample=0.8,
        colsample_bytree=0.8, random_state=42, verbose=-1,
    )
    rf_ou = RandomForestClassifier(
        n_estimators=300, max_depth=6, min_samples_split=5, random_state=42,
    )
    
    ensemble_ou25 = VotingClassifier(
        estimators=[('xgb', xgb_ou), ('lgb', lgb_ou), ('rf', rf_ou)],
        voting='soft'
    )

    cv_ou25 = []
    for tr, va in tscv.split(X):
        ensemble_ou25.fit(X.iloc[tr], y_ou25[tr])
        probs = ensemble_ou25.predict_proba(X.iloc[va])[:, 1]
        cv_ou25.append(log_loss(y_ou25[va], probs))
    logger.info(f"O/U 2.5 Ensemble CV LogLoss: {np.mean(cv_ou25):.4f}")

    cal_ou25 = CalibratedClassifierCV(
        ensemble_ou25, cv=3, method="isotonic"
    )
    cal_ou25.fit(X.iloc[:split_idx], y_ou25[:split_idx])
    joblib.dump(cal_ou25, os.path.join(MODELS_DIR, "wc_ou25_xgb.pkl"))
    logger.info("✅  wc_ou25_xgb.pkl saved")

    # ── Save metadata ─────────────────────────────────────────────────────────
    meta = {
        "trained_at":    TODAY.isoformat(),
        "training_rows": len(feat_df),
        "features":      FEATURES,
        "cv_1x2_acc":    round(float(np.mean(cv_scores)), 4),
        "cv_ou25_logloss": round(float(np.mean(cv_ou25)), 4),
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"✅  Metadata saved → {META_PATH}")
    logger.info("\nRestart the backend to load new models.")


if __name__ == "__main__":
    train()
