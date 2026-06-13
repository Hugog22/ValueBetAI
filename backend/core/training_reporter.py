"""
training_reporter.py
--------------------
Centralized training report writer for all AI models.

Each time a model is trained, this module appends a structured
entry to `logs/training_report.log` (created automatically).

The log is human-readable and contains:
  - Timestamp of training
  - Model name and type
  - Training data size
  - Best hyperparameters (with explanation of each)
  - CV accuracy / log-loss before and after
  - Whether accuracy improved vs the previous run
  - Success or failure status + error message if applicable
"""

import os
import json
import logging
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    MADRID_TZ = ZoneInfo("Europe/Madrid")
except ImportError:
    MADRID_TZ = None
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Path inside the backend/ directory so it's writable in Render's filesystem
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BACKEND_DIR, "logs")
REPORT_PATH = os.path.join(LOG_DIR, "training_report.log")
HISTORY_PATH = os.path.join(LOG_DIR, "training_history.json")

# Human-readable explanations for common XGBoost / RandomForest hyperparameters
PARAM_EXPLANATIONS = {
    "learning_rate": (
        "Velocidad de aprendizaje del gradient boosting. "
        "Valores más bajos (<0.01) hacen el modelo más conservador y menos propenso a sobreajustarse, "
        "pero requieren más árboles. Valores más altos (>0.05) aprenden más rápido pero pueden sobreajustarse."
    ),
    "max_depth": (
        "Profundidad máxima de cada árbol de decisión. "
        "Más profundidad permite capturar relaciones más complejas, "
        "pero aumenta el riesgo de sobreajuste."
    ),
    "subsample": (
        "Fracción de datos usada para entrenar cada árbol. "
        "Valores <1.0 añaden aleatoriedad y reducen sobreajuste (regularización estocástica)."
    ),
    "colsample_bytree": (
        "Fracción de variables (features) usada por árbol. "
        "Reducir este valor mejora la diversidad del ensemble y reduce sobreajuste."
    ),
    "min_child_weight": (
        "Peso mínimo (suma de instancias) en un nodo hoja. "
        "Valores más altos evitan splits en grupos muy pequeños → más regularización."
    ),
    "gamma": (
        "Reducción mínima de pérdida para hacer un split adicional. "
        "Aumentarlo hace el modelo más conservador."
    ),
    "reg_alpha": (
        "Regularización L1 (Lasso). Induce esparsidad en los pesos → selección implícita de features."
    ),
    "reg_lambda": (
        "Regularización L2 (Ridge). Reduce el tamaño de los pesos → suaviza el modelo."
    ),
    "n_estimators": (
        "Número de árboles en el ensemble. "
        "Determinado por early stopping — se detiene cuando el CV no mejora."
    ),
}


def _load_history() -> dict:
    """Load previous training history to compare improvements."""
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_history(history: dict) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def _format_param_change(key: str, old_val: Any, new_val: Any) -> str:
    """Generate a human-readable explanation of a parameter change."""
    if old_val is None:
        return f"  • {key}: {new_val}  ← [nuevo parámetro]"
    if old_val == new_val:
        return f"  • {key}: {new_val}  ← [sin cambio]"
    direction = "↑ aumentó" if new_val > old_val else "↓ bajó"
    explanation = PARAM_EXPLANATIONS.get(key, "")
    return f"  • {key}: {old_val} → {new_val}  ({direction})\n    📌 {explanation}" if explanation else \
           f"  • {key}: {old_val} → {new_val}  ({direction})"


def write_training_report(
    model_name: str,
    success: bool,
    meta: Optional[dict] = None,
    error: Optional[str] = None,
    duration_seconds: Optional[float] = None,
) -> None:
    """
    Append a training report entry to logs/training_report.log.

    Parameters
    ----------
    model_name    : e.g. "LaLiga XGBoost 1X2", "World Cup XGBoost"
    success       : True if training completed without errors
    meta          : dict with keys like best_params, cv_mean_accuracy, etc.
    error         : error message if success=False
    duration_secs : elapsed training time
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    now = datetime.now(MADRID_TZ) if MADRID_TZ else datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S (Madrid)")
    separator = "=" * 72

    lines = [
        "",
        separator,
        f"  INFORME DE AUTOENTRENAMIENTO — {ts}",
        f"  Modelo: {model_name}",
        separator,
    ]

    if not success:
        lines += [
            f"  ❌ ESTADO: FALLIDO",
            f"  Error: {error}",
            separator,
        ]
        _write_lines(lines)
        return

    lines.append(f"  ✅ ESTADO: EXITOSO")
    if duration_seconds:
        mins = int(duration_seconds // 60)
        secs = int(duration_seconds % 60)
        lines.append(f"  ⏱  Duración: {mins}m {secs}s")

    if meta:
        # Data stats
        rows = meta.get("total_rows") or meta.get("training_rows")
        if rows:
            lines.append(f"  📊 Datos de entrenamiento: {rows:,} partidos")
        seasons = meta.get("seasons", [])
        if seasons:
            lines.append(f"  📅 Temporadas: {', '.join(str(s) for s in seasons)}")
        leagues = meta.get("leagues", [])
        if leagues:
            lines.append(f"  🏆 Ligas: {', '.join(leagues)}")

        # Load previous run for comparison
        history = _load_history()
        prev = history.get(model_name, {})

        # Per-model metrics
        for model_key, model_label in [
            ("model_1x2",   "Modelo 1X2 (Victoria Local / Empate / Visitante)"),
            ("model_ou25",  "Modelo Over/Under 2.5"),
        ]:
            m = meta.get(model_key)
            if not m:
                continue
            lines += ["", f"  ─── {model_label} ───"]

            acc_now = m.get("cv_mean_accuracy")
            acc_prev = prev.get(model_key, {}).get("cv_mean_accuracy")
            if acc_now is not None:
                acc_str = f"{acc_now*100:.2f}%"
                if acc_prev is not None:
                    delta = (acc_now - acc_prev) * 100
                    sign = "+" if delta >= 0 else ""
                    acc_str += f"  (antes: {acc_prev*100:.2f}%, cambio: {sign}{delta:.2f}%)"
                    if delta > 0:
                        acc_str += " ✅ MEJORA"
                    elif delta < -0.5:
                        acc_str += " ⚠️ EMPEORA"
                lines.append(f"  📈 Exactitud CV: {acc_str}")

            ll_now = m.get("cv_mean_logloss")
            if ll_now is not None:
                ll_prev = prev.get(model_key, {}).get("cv_mean_logloss")
                ll_str = f"{ll_now:.4f}"
                if ll_prev is not None:
                    delta = ll_now - ll_prev
                    sign = "+" if delta >= 0 else ""
                    ll_str += f"  (antes: {ll_prev:.4f}, cambio: {sign}{delta:.4f})"
                lines.append(f"  📉 Log-Loss CV: {ll_str}")

            # Hyperparameter changes
            best_now = m.get("best_params", {})
            best_prev = prev.get(model_key, {}).get("best_params", {})
            if best_now:
                lines.append(f"  🔧 Hiperparámetros seleccionados por Optuna:")
                for k, v in best_now.items():
                    lines.append(_format_param_change(k, best_prev.get(k), v))

        # World Cup specific metrics
        cv_1x2 = meta.get("cv_1x2_acc")
        cv_ou25 = meta.get("cv_ou25_logloss")
        if cv_1x2 is not None:
            prev_acc = prev.get("cv_1x2_acc")
            acc_str = f"{cv_1x2*100:.2f}%"
            if prev_acc:
                delta = (cv_1x2 - prev_acc) * 100
                acc_str += f"  (antes: {prev_acc*100:.2f}%, cambio: {'+' if delta>=0 else ''}{delta:.2f}%)"
            lines.append(f"  📈 1X2 CV Accuracy: {acc_str}")
        if cv_ou25 is not None:
            lines.append(f"  📉 O/U 2.5 CV Log-Loss: {cv_ou25:.4f}")

        # Save current as history for next comparison
        history[model_name] = meta
        _save_history(history)

    lines += [
        "",
        f"  💡 RESUMEN:",
        f"  Los modelos actualizados se usarán en las próximas predicciones automáticamente.",
        f"  Si la exactitud bajó significativamente, considera revisar los datos de entrenamiento.",
        separator,
    ]

    _write_lines(lines)


def _write_lines(lines: list[str]) -> None:
    """Append lines to the training report log file."""
    text = "\n".join(lines) + "\n"
    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.write(text)
    logger.info(f"📝 Training report appended → {REPORT_PATH}")


def get_report_path() -> str:
    return REPORT_PATH
