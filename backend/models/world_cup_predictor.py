"""
world_cup_predictor.py
----------------------
Specialist predictor for FIFA World Cup national team matches.

Key differences vs club predictor:
  - FIFA ranking points as primary strength signal (not ELO calculated from scratch)
  - Squad quality score: average club-level rating of the squad's players
  - Head-to-head historical win rate between two national teams
  - Recent form from last 5 official matches (qualifiers + friendlies)
  - Tournament stage (group_stage vs knockout — changes probability distribution)
  - Player quality differential: captures mismatches in individual talent

Fallback model (no trained .pkl):
  Uses an analytic logistic model based on FIFA point differential alone.
  Once train_model_worldcup.py is run the trained XGBoost model is loaded.
"""

import json
import logging
import os

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

MODELS_DIR      = os.path.dirname(__file__)
DATA_DIR        = os.path.join(os.path.dirname(MODELS_DIR), "data")
SQUAD_PATH      = os.path.join(DATA_DIR, "world_cup_squads.json")
HIST_CSV_PATH   = os.path.join(DATA_DIR, "world_cup_historical.csv")
MODEL_1X2_PATH  = os.path.join(MODELS_DIR, "wc_1x2_xgb.pkl")
MODEL_OU25_PATH = os.path.join(MODELS_DIR, "wc_ou25_xgb.pkl")
META_PATH       = os.path.join(MODELS_DIR, "wc_training_meta.json")

# Minimum real matches needed to prefer trained model over analytic fallback.
# Below this threshold the analytic model (FIFA points + squad quality) is
# more reliable than a model trained on synthetic data.
MIN_REAL_MATCHES_FOR_ML = 150


# ---------------------------------------------------------------------------
# FIFA Ranking Points — World Cup 2026 (March 2026 snapshot)
# ---------------------------------------------------------------------------

FIFA_POINTS: dict[str, float] = {
    "Argentina": 1862.0, "France": 1840.0, "Spain": 1815.0,
    "England": 1790.0, "Brazil": 1775.0, "Portugal": 1767.0,
    "Belgium": 1744.0, "Netherlands": 1738.0, "Germany": 1728.0,
    "Italy": 1719.0, "Colombia": 1692.0, "Uruguay": 1678.0,
    "Morocco": 1669.0, "Croatia": 1654.0, "Senegal": 1638.0,
    "United States": 1630.0, "Mexico": 1624.0, "Japan": 1614.0,
    "Ecuador": 1608.0, "South Korea": 1596.0, "Canada": 1588.0,
    "Australia": 1580.0, "Switzerland": 1570.0, "Poland": 1556.0,
    "Denmark": 1548.0, "Serbia": 1536.0, "Turkey": 1524.0,
    "Austria": 1514.0, "Ukraine": 1506.0, "Hungary": 1498.0,
    "Slovakia": 1490.0, "Romania": 1478.0, "Slovenia": 1468.0,
    "Czechia": 1460.0, "Scotland": 1448.0, "Greece": 1438.0,
    "Albania": 1428.0, "Georgia": 1420.0, "Costa Rica": 1410.0,
    "Panama": 1398.0, "Venezuela": 1388.0, "Chile": 1378.0,
    "Paraguay": 1366.0, "Bolivia": 1348.0, "Honduras": 1336.0,
    "El Salvador": 1320.0, "New Zealand": 1298.0, "Saudi Arabia": 1280.0,
    "Haiti": 1260.0, "Curaçao": 1250.0, "Ivory Coast": 1530.0,
    "Sweden": 1530.0, "Tunisia": 1520.0, "Cape Verde": 1300.0,
    "Egypt": 1500.0, "Iran": 1610.0, "Iraq": 1420.0,
    "Norway": 1460.0, "Algeria": 1480.0, "Jordan": 1380.0,
    "DR Congo": 1380.0, "Ghana": 1450.0, "Uzbekistan": 1380.0,
    "South Africa": 1410.0, "Bosnia & Herzegovina": 1330.0, "Qatar": 1440.0,
    # Aliases
    "USA": 1630.0, "Korea Republic": 1596.0, "Türkiye": 1524.0,
    "Czech Republic": 1460.0,
}

DEFAULT_FIFA_POINTS = 1350.0  # for teams not in the ranking

TEAM_ALIASES: dict[str, str] = {
    # API-Sports / Odds API variants
    "USA":                          "United States",
    "Korea Republic":               "South Korea",
    "Republic of Korea":            "South Korea",
    "Türkiye":                      "Turkey",
    "Czech Republic":               "Czechia",
    "IR Iran":                      "Iran",
    "Côte d'Ivoire":                "Ivory Coast",
    # Bosnia variants
    "Bosnia-Herzegovina":           "Bosnia and Herzegovina",
    "Bosnia & Herzegovina":         "Bosnia and Herzegovina",
    # Other hyphenated variants
    "Guinea-Bissau":                "Guinea Bissau",
    "Equatorial-Guinea":            "Equatorial Guinea",
    # Football-data.org variants
    "North Macedonia":              "North Macedonia",
    "DR Congo":                     "Democratic Republic of Congo",
    "Congo DR":                     "Democratic Republic of Congo",
    "Cape Verde Islands":           "Cape Verde",
    "Cabo Verde":                   "Cape Verde",
    "New Zealand":                  "New Zealand",
    
    # Spanish and Native Names mappings
    "España":                       "Spain",
    "Alemania":                     "Germany",
    "Deutschland":                  "Germany",
    "Brasil":                       "Brazil",
    "Italia":                       "Italy",
    "Holanda":                      "Netherlands",
    "Países Bajos":                 "Netherlands",
    "Pays-Bas":                     "Netherlands",
    "Inglaterra":                   "England",
    "Francia":                      "France",
    "Bélgica":                      "Belgium",
    "Belgique":                     "Belgium",
    "België":                       "Belgium",
    "Suiza":                        "Switzerland",
    "Schweiz":                      "Switzerland",
    "Suisse":                       "Switzerland",
    "Croacia":                      "Croatia",
    "Hrvatska":                     "Croatia",
    "Marruecos":                    "Morocco",
    "Maroc":                        "Morocco",
    "Japón":                        "Japan",
    "Nihon":                        "Japan",
    "Nippon":                       "Japan",
    "Corea del Sur":                "South Korea",
    "Estados Unidos":               "United States",
    "EEUU":                         "United States",
    "EE.UU.":                       "United States",
    "México":                       "Mexico",
    "Canadá":                       "Canada",
    "Polonia":                      "Poland",
    "Polska":                       "Poland",
    "Dinamarca":                    "Denmark",
    "Danmark":                      "Denmark",
    "Turquía":                      "Turkey",
    "Ucrania":                      "Ukraine",
    "Hungría":                      "Hungary",
    "Magyarország":                 "Hungary",
    "Eslovaquia":                    "Slovakia",
    "Slovensko":                    "Slovakia",
    "Rumanía":                      "Romania",
    "Rumania":                      "Romania",
    "România":                      "Romania",
    "Eslovenia":                    "Slovenia",
    "Slovenija":                    "Slovenia",
    "República Checa":              "Czechia",
    "Escocia":                      "Scotland",
    "Grecia":                       "Greece",
    "Hellas":                       "Greece",
    "Panamá":                       "Panama",
    "Nueva Zelanda":                "New Zealand",
    "Arabia Saudita":               "Saudi Arabia",
    "Arabia Saudí":                 "Saudi Arabia",
    "Haití":                        "Haiti",
    "Curazao":                      "Curaçao",
    "Curacao":                      "Curaçao",
    "Costa de Marfil":              "Ivory Coast",
    "Suecia":                       "Sweden",
    "Sverige":                      "Sweden",
    "Túnez":                        "Tunisia",
    "Tunisie":                      "Tunisia",
    "Egipto":                       "Egypt",
    "Irán":                         "Iran",
    "Irak":                         "Iraq",
    "Noruega":                      "Norway",
    "Norge":                        "Norway",
    "Argelia":                      "Algeria",
    "Algérie":                      "Algeria",
    "Jordania":                     "Jordan",
    "República Democrática del Congo": "Democratic Republic of Congo",
    "Uzbekistán":                   "Uzbekistan",
    "Sudáfrica":                    "South Africa",
    "Catar":                        "Qatar"
}

FEATURES = [
    "home_fifa_pts",           # FIFA ranking points (absolute)
    "away_fifa_pts",
    "fifa_pts_diff",           # home - away differential
    "home_squad_quality",      # avg club rating of squad players (0-100)
    "away_squad_quality",
    "squad_quality_diff",
    "home_form_pts5",          # pts in last 5 official matches (0-15)
    "away_form_pts5",
    "form_diff",
    "home_h2h_win_rate",       # historical H2H win rate (0-1)
    "away_h2h_win_rate",
    "is_knockout",             # 0=group, 1=elimination round
    "home_goals_avg5",         # avg goals scored last 5 matches
    "away_goals_avg5",
    "home_conceded_avg5",      # avg goals conceded last 5
    "away_conceded_avg5",
    "home_avg_xg",             # average expected goals
    "away_avg_xg",
    "home_avg_possession",
    "away_avg_possession",
    "home_avg_shots",
    "away_avg_shots",
    "home_wc_matches",         # dynamic world cup match count
    "away_wc_matches",
    "home_wc_goals",           # dynamic world cup goals
    "away_wc_goals",
]

# Analytic defaults for cold-start (used as fallback when no historical data)
DEFAULTS: dict[str, float] = {
    "home_fifa_pts":     1500.0,
    "away_fifa_pts":     1500.0,
    "fifa_pts_diff":     0.0,
    "home_squad_quality": 60.0,
    "away_squad_quality": 60.0,
    "squad_quality_diff": 0.0,
    "home_form_pts5":    7.5,
    "away_form_pts5":    7.5,
    "form_diff":         0.0,
    "home_h2h_win_rate": 0.33,
    "away_h2h_win_rate": 0.33,
    "is_knockout":       0.0,
    "home_goals_avg5":   1.35,
    "away_goals_avg5":   1.35,
    "home_conceded_avg5": 1.15,
    "away_conceded_avg5": 1.15,
    "home_avg_xg": 1.5,
    "away_avg_xg": 1.5,
    "home_avg_possession": 50.0,
    "away_avg_possession": 50.0,
    "home_avg_shots": 4.0,
    "away_avg_shots": 4.0,
    # Dynamic WC match stats (injected via extra_features; default to 0 cold-start)
    "home_wc_matches":        0.0,
    "away_wc_matches":        0.0,
    "home_wc_goals":          0.0,
    "away_wc_goals":          0.0,
}


def _normalize(name: str) -> str:
    return TEAM_ALIASES.get(name, name)


def _get_fifa_pts(team: str) -> float:
    return FIFA_POINTS.get(_normalize(team), DEFAULT_FIFA_POINTS)


# ---------------------------------------------------------------------------
# Head-to-head stats from historical CSV
# ---------------------------------------------------------------------------

class H2HCache:
    """Lazy-loaded head-to-head win rate cache from world_cup_historical.csv."""

    def __init__(self):
        self._cache: dict[tuple[str, str], dict] = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        self._loaded = True
        if not os.path.exists(HIST_CSV_PATH):
            return
        try:
            df = pd.read_csv(HIST_CSV_PATH)
            df = df.dropna(subset=["home_goals", "away_goals"])
            for _, row in df.iterrows():
                ht = str(row.get("home_team", ""))
                at = str(row.get("away_team", ""))
                hg = float(row.get("home_goals", 0))
                ag = float(row.get("away_goals", 0))
                for team_a, team_b, score_a in [(ht, at, hg - ag), (at, ht, ag - hg)]:
                    key = (team_a, team_b)
                    if key not in self._cache:
                        self._cache[key] = {"wins": 0, "draws": 0, "losses": 0,
                                            "goals_for": 0.0, "goals_ag": 0.0}
                    entry = self._cache[key]
                    entry["goals_for"] += hg if team_a == ht else ag
                    entry["goals_ag"]  += ag if team_a == ht else hg
                    if score_a > 0:
                        entry["wins"]   += 1
                    elif score_a == 0:
                        entry["draws"]  += 1
                    else:
                        entry["losses"] += 1
        except Exception as e:
            logger.warning(f"H2H cache load failed: {e}")

    def get_stats(self, team_a: str, team_b: str) -> dict:
        self._load()
        key = (team_a, team_b)
        entry = self._cache.get(key, {})
        total = entry.get("wins", 0) + entry.get("draws", 0) + entry.get("losses", 0)
        if total == 0:
            return {"win_rate": None, "goals_avg": None, "conceded_avg": None, "n": 0}
        win_rate    = entry["wins"] / total
        goals_avg   = entry["goals_for"] / total
        conceded_avg = entry["goals_ag"] / total
        return {"win_rate": win_rate, "goals_avg": goals_avg, "conceded_avg": conceded_avg, "n": total}


_h2h = H2HCache()


# ---------------------------------------------------------------------------
# Squad quality loader
# ---------------------------------------------------------------------------

class SquadQualityCache:
    """Loads squad quality scores from world_cup_squads.json."""

    def __init__(self):
        self._data: dict[str, float] = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        self._loaded = True
        if not os.path.exists(SQUAD_PATH):
            return
        try:
            with open(SQUAD_PATH) as f:
                raw = json.load(f)
            for team, info in raw.items():
                self._data[team] = float(info.get("squad_quality_score", 60.0))
        except Exception as e:
            logger.warning(f"Squad quality load failed: {e}")

    def get(self, team: str) -> float:
        self._load()
        team_norm = _normalize(team)
        if team_norm in self._data:
            return self._data[team_norm]
        # Derive from FIFA points if no squad data
        pts = _get_fifa_pts(team)
        normalized = (pts - 1280.0) / (1862.0 - 1280.0)
        return 40.0 + (normalized ** 0.7) * 55.0


_squad_quality = SquadQualityCache()


# ---------------------------------------------------------------------------
# Analytic fallback model (no ML training required)
# ---------------------------------------------------------------------------

def _analytic_predict(home_pts: float, away_pts: float,
                      home_quality: float, away_quality: float,
                      form_diff: float, is_knockout: bool) -> dict:
    """
    Logistic model using FIFA points + squad quality differential.
    Returns P(home win), P(draw), P(away win).
    Calibrated against historical World Cup results.
    """
    # Composite strength score (70% FIFA points, 30% squad quality)
    home_str = 0.70 * home_pts + 0.30 * home_quality * 15
    away_str = 0.70 * away_pts + 0.30 * away_quality * 15

    delta = home_str - away_str + form_diff * 30

    # Bradley-Terry logistic for home win (extremely sharp curve to crush mismatches)
    p_home = 1.0 / (1.0 + 10.0 ** (-delta / 200.0))

    # Draw probability: peaks at 0.28 when evenly matched, collapses for huge mismatches
    draw_base = 0.28 * max(0.0, 1.0 - abs(delta) / 600.0)
    if is_knockout:
        draw_base *= 0.40  # penalties replace draws in knockout

    # Redistribute
    p_draw = draw_base
    p_home_adj = p_home * (1.0 - draw_base)
    p_away_adj = (1.0 - p_home) * (1.0 - draw_base)

    total = p_home_adj + p_draw + p_away_adj
    return {
        "home": round(p_home_adj / total, 4),
        "draw": round(p_draw / total, 4),
        "away": round(p_away_adj / total, 4),
    }


def _analytic_ou25(home_quality: float, away_quality: float,
                   home_goals5: float, away_goals5: float,
                   is_knockout: bool) -> float:
    """
    Estimate P(over 2.5 goals) analytically.
    Historical WC average is ~2.4 goals/match (lower than club football).
    """
    avg_goals = (home_goals5 + away_goals5) / 2.0
    quality_factor = (home_quality + away_quality) / 2.0 / 80.0  # normalised
    # Knockout games tend to be more conservative
    knockout_factor = 0.85 if is_knockout else 1.0
    lambda_goals = avg_goals * quality_factor * knockout_factor * 2.5 / 1.5

    # Poisson P(X > 2.5) ≈ P(X >= 3)
    import math
    p_under = sum(
        math.exp(-lambda_goals) * (lambda_goals ** k) / math.factorial(k)
        for k in range(3)
    )
    return round(1.0 - p_under, 4)


def _anchor_to_fifa_differential(probs: dict, home_pts: float, away_pts: float,
                                  is_knockout: bool = False) -> dict:
    """
    Mezcla las probabilidades del modelo ML con las del modelo analítico
    usando alpha como peso del modelo analítico.
    Evita que el ML se aleje demasiado de lo que dictan los FIFA points
    en partidos muy desiguales (donde el ML tiene menos datos de entrenamiento).
    """
    diff = abs(home_pts - away_pts)
    if diff < 150:
        if is_knockout:
            # The ML model was trained mostly on group-stage data and strongly
            # overestimates draw probability in evenly-matched knockout games.
            # Use a heavy analytic blend (0.55) to correct this: in knockout
            # rounds a draw at 90' is just one possible path to penalties, so
            # the true draw probability is far lower than what the ML outputs.
            analytic = _analytic_predict(home_pts, away_pts, 60.0, 60.0, 0.0, True)
            alpha = 0.55  # heavy blend toward analytic for knockout
            blended = {
                k: (1 - alpha) * probs[k] + alpha * analytic[k]
                for k in ("home", "draw", "away")
            }
            total = sum(blended.values())
            return {k: round(v / total, 4) for k, v in blended.items()}
        return probs

    alpha = min(0.65, 0.25 + diff / 1500.0)

    analytic = _analytic_predict(home_pts, away_pts, 60.0, 60.0, 0.0, is_knockout)
    blended = {
        k: (1 - alpha) * probs[k] + alpha * analytic[k]
        for k in ("home", "draw", "away")
    }
    # Renormalizar
    total = sum(blended.values())
    return {k: round(v / total, 4) for k, v in blended.items()}


# ---------------------------------------------------------------------------
# Main predictor class
# ---------------------------------------------------------------------------

class WorldCupPredictor:
    """
    Loads trained XGBoost models for WC prediction when available.
    Falls back to the analytic model otherwise.
    """

    def __init__(self):
        self._model_1x2  = None
        self._model_ou25 = None
        self._ready      = False

    def load_model(self):
        # Check training metadata — only use ML if trained on real data
        real_matches = 0
        if os.path.exists(META_PATH):
            try:
                with open(META_PATH) as f:
                    meta = json.load(f)
                real_matches = meta.get("training_rows", 0)
            except Exception:
                pass

        use_ml = real_matches >= MIN_REAL_MATCHES_FOR_ML

        if use_ml:
            if os.path.exists(MODEL_1X2_PATH):
                try:
                    self._model_1x2 = joblib.load(MODEL_1X2_PATH)
                    logger.info("WorldCupPredictor: loaded 1X2 ML model")
                except Exception as e:
                    logger.warning(f"WC 1X2 model load failed: {e}")

            if os.path.exists(MODEL_OU25_PATH):
                try:
                    self._model_ou25 = joblib.load(MODEL_OU25_PATH)
                    logger.info("WorldCupPredictor: loaded OU25 ML model")
                except Exception as e:
                    logger.warning(f"WC OU25 model load failed: {e}")

        if not use_ml or self._model_1x2 is None:
            logger.info(
                f"WorldCupPredictor: using analytic model "
                f"(training rows={real_matches} < threshold={MIN_REAL_MATCHES_FOR_ML})"
            )

        self._ready = True

    def _build_feature_vector(self, home: str, away: str,
                               is_knockout: bool = False) -> dict:
        """Build full feature dict for a match between two national teams."""
        home_n = _normalize(home)
        away_n = _normalize(away)

        home_pts   = _get_fifa_pts(home_n)
        away_pts   = _get_fifa_pts(away_n)
        home_qual  = _squad_quality.get(home_n) or DEFAULTS["home_squad_quality"]
        away_qual  = _squad_quality.get(away_n) or DEFAULTS["away_squad_quality"]

        h2h_home   = _h2h.get_stats(home_n, away_n)
        h2h_away   = _h2h.get_stats(away_n, home_n)

        h2h_win_rate_home = h2h_home["win_rate"] if h2h_home["n"] > 0 else (0.5 + (home_pts - away_pts) / 3000.0)
        h2h_win_rate_away = h2h_away["win_rate"] if h2h_away["n"] > 0 else (0.5 + (away_pts - home_pts) / 3000.0)

        return {
            "home_fifa_pts":      home_pts,
            "away_fifa_pts":      away_pts,
            "fifa_pts_diff":      home_pts - away_pts,
            "home_squad_quality": home_qual,
            "away_squad_quality": away_qual,
            "squad_quality_diff": home_qual - away_qual,
            "home_form_pts5":     7.5,   # default — overridden by feature enrichment
            "away_form_pts5":     7.5,
            "form_diff":          0.0,
            "home_h2h_win_rate":  h2h_win_rate_home,
            "away_h2h_win_rate":  h2h_win_rate_away,
            "is_knockout":        1.0 if is_knockout else 0.0,
            "home_goals_avg5":    h2h_home.get("goals_avg", 1.35),
            "away_goals_avg5":    h2h_away.get("goals_avg", 1.35),
            "home_conceded_avg5": h2h_home.get("conceded_avg", 1.15),
            "away_conceded_avg5": h2h_away.get("conceded_avg", 1.15),
            "home_avg_xg": 1.5,
            "away_avg_xg": 1.5,
            "home_avg_possession": 50.0,
            "away_avg_possession": 50.0,
            "home_avg_shots": 4.0,
            "away_avg_shots": 4.0,
        }

    def predict_match(self, home: str, away: str,
                      is_knockout: bool = False,
                      extra_features: dict | None = None) -> dict:
        """
        Predict all markets for a WC national team match.

        Parameters
        ----------
        home, away     : Team names (The Odds API format)
        is_knockout    : True for Round of 16 onwards
        extra_features : Optional overrides for features dict

        Returns
        -------
        dict with probabilities, fair_odds_1x2, prob_over25, fair_odds_ou25
        """
        if not self._ready:
            self.load_model()

        fv = {**DEFAULTS, **self._build_feature_vector(home, away, is_knockout)}
        if extra_features:
            fv.update(extra_features)

        eps = 1e-6

        # ── 1X2 ──────────────────────────────────────────────────────────
        if self._model_1x2 is not None:
            X = pd.DataFrame([{k: fv[k] for k in FEATURES}]).astype(float)
            raw = self._model_1x2.predict_proba(X)[0]
            
            fv_inv = fv.copy()
            for col in FEATURES:
                if col.startswith("home_"):
                    fv_inv[col.replace("home_", "away_")] = fv[col]
                elif col.startswith("away_"):
                    fv_inv[col.replace("away_", "home_")] = fv[col]
            fv_inv["fifa_pts_diff"] = -fv["fifa_pts_diff"]
            fv_inv["squad_quality_diff"] = -fv["squad_quality_diff"]
            fv_inv["form_diff"] = -fv["form_diff"]
            
            X_inv = pd.DataFrame([{k: fv_inv[k] for k in FEATURES}]).astype(float)
            raw_inv = self._model_1x2.predict_proba(X_inv)[0]
            
            p_home = (raw[0] + raw_inv[2]) / 2.0
            p_draw = (raw[1] + raw_inv[1]) / 2.0
            p_away = (raw[2] + raw_inv[0]) / 2.0
            
            probs_1x2 = {"home": float(p_home), "draw": float(p_draw), "away": float(p_away)}
            probs_1x2 = _anchor_to_fifa_differential(
                probs_1x2, fv["home_fifa_pts"], fv["away_fifa_pts"],
                is_knockout=is_knockout,
            )
        else:
            probs_1x2 = _analytic_predict(
                fv["home_fifa_pts"], fv["away_fifa_pts"],
                fv["home_squad_quality"], fv["away_squad_quality"],
                fv["form_diff"], bool(fv["is_knockout"]),
            )

        # ── O/U 2.5 ──────────────────────────────────────────────────────
        if self._model_ou25 is not None:
            X = pd.DataFrame([{k: fv[k] for k in FEATURES}]).astype(float)
            prob_over25_1 = float(self._model_ou25.predict_proba(X)[0][1])
            
            fv_inv = fv.copy()
            for col in FEATURES:
                if col.startswith("home_"):
                    fv_inv[col.replace("home_", "away_")] = fv[col]
                elif col.startswith("away_"):
                    fv_inv[col.replace("away_", "home_")] = fv[col]
            fv_inv["fifa_pts_diff"] = -fv["fifa_pts_diff"]
            fv_inv["squad_quality_diff"] = -fv["squad_quality_diff"]
            fv_inv["form_diff"] = -fv["form_diff"]
            
            X_inv = pd.DataFrame([{k: fv_inv[k] for k in FEATURES}]).astype(float)
            prob_over25_2 = float(self._model_ou25.predict_proba(X_inv)[0][1])
            
            prob_over25 = (prob_over25_1 + prob_over25_2) / 2.0
        else:
            prob_over25 = _analytic_ou25(
                fv["home_squad_quality"], fv["away_squad_quality"],
                fv["home_goals_avg5"],   fv["away_goals_avg5"],
                bool(fv["is_knockout"]),
            )

        p_h = probs_1x2["home"]
        p_d = probs_1x2["draw"]
        p_a = probs_1x2["away"]

        return {
            "probabilities": {
                "home": round(p_h, 4),
                "draw": round(p_d, 4),
                "away": round(p_a, 4),
            },
            "fair_odds_1x2": {
                "home": round(1.0 / (p_h + eps), 2),
                "draw": round(1.0 / (p_d + eps), 2),
                "away": round(1.0 / (p_a + eps), 2),
            },
            "prob_over25": round(prob_over25, 4),
            "fair_odds_ou25": {
                "over":  round(1.0 / (prob_over25 + eps), 2),
                "under": round(1.0 / (1 - prob_over25 + eps), 2),
            },
            # Extra context for display
            "home_fifa_pts":      fv["home_fifa_pts"],
            "away_fifa_pts":      fv["away_fifa_pts"],
            "home_squad_quality": round(fv["home_squad_quality"], 1),
            "away_squad_quality": round(fv["away_squad_quality"], 1),
            "h2h_matches":        _h2h.get_stats(_normalize(home), _normalize(away))["n"],
        }

    def detect_value(self, pred: dict, book_odds: dict) -> list[dict]:
        """Detect value bets across 1X2 and O/U 2.5 markets."""
        value_bets = []
        eps = 1e-6

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
        _check("Victoria Local",     "1x2",  f1x2["home"], book_odds.get("home", 0))
        _check("Empate",             "1x2",  f1x2["draw"], book_odds.get("draw", 0))
        _check("Victoria Visitante", "1x2",  f1x2["away"], book_odds.get("away", 0))

        fou25 = pred["fair_odds_ou25"]
        _check("Más de 2.5 Goles",   "ou25", fou25["over"],  book_odds.get("over25",  0))
        _check("Menos de 2.5 Goles", "ou25", fou25["under"], book_odds.get("under25", 0))

        return value_bets
