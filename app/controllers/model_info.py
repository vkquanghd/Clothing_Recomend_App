# app/controllers/model_info.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional, Iterable, Set
from flask import Blueprint, request, render_template, jsonify, current_app, has_app_context
import json

# Prefer joblib for models saved via joblib.dump; fallback to dill/pickle
try:
    import joblib  # noqa
except Exception:  # pragma: no cover
    joblib = None  # type: ignore

try:
    import dill as dpickle  # noqa
except Exception:  # pragma: no cover
    dpickle = None

import pickle as spickle  # stdlib pickle (last resort)

bp = Blueprint("model_info", __name__, url_prefix="/model")

# ---- Shim for old pickles saved with custom class name ---------------------
class EnsembleBundle:
    def __init__(self, models=None, weights=None, **kw):
        self.models = models or {}
        self.weights = weights or {}

    def predict_proba(self, texts: Iterable[str]):
        import numpy as np
        if not self.models:
            raise RuntimeError("No base models in EnsembleBundle")
        probs = []
        X = list(texts)
        for m in self.models.values():
            if hasattr(m, "predict_proba"):
                probs.append(m.predict_proba(X)[:, 1])
            else:
                raise RuntimeError("Base model lacks predict_proba")
        probs = np.vstack(probs)
        return probs.mean(axis=0)

    def predict(self, texts: Iterable[str]):
        import numpy as np
        return (self.predict_proba(texts) >= 0.5).astype(int)

# ---- model loader with graceful fallback -----------------------------------
_model: Optional[Any] = None
_model_err: Optional[str] = None
_degraded = False  # True when using rule-based fallback

# Config (override by manifest)
_THRESHOLD: float = 0.60
_HEURISTIC_DELTA: float = 0.08
_NEG_PHRASES: Set[str] = {
    "too tight", "too small", "itchy", "scratchy", "see through",
    "cheap fabric", "poor fit", "returned", "uncomfortable",
    "runs small", "runs large"
}

def _root() -> Path:
    if has_app_context():
        return Path(current_app.root_path).parent
    return Path(__file__).resolve().parents[2]

def _model_path() -> Path:
    # Pure scikit-learn VotingClassifier exported as joblib
    return _root() / "model" / "ensemble_soft.pkl"

def _manifest_path() -> Path:
    return _root() / "model" / "manifest.json"

def _load_manifest_config():
    """Load threshold / heuristic from manifest.json if available."""
    global _THRESHOLD, _HEURISTIC_DELTA, _NEG_PHRASES
    p = _manifest_path()
    if not p.exists():
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        # threshold
        thr = float(data.get("threshold", _THRESHOLD))
        _THRESHOLD = max(0.0, min(1.0, thr))
        # heuristic on/off and delta
        if bool(data.get("post_prob_heuristic", True)):
            _HEURISTIC_DELTA = float(data.get("heuristic_delta", _HEURISTIC_DELTA))
            # phrases list
            phrases = data.get("neg_phrases")
            if isinstance(phrases, list) and phrases:
                _NEG_PHRASES = {str(x).lower().strip() for x in phrases if str(x).strip()}
    except Exception:
        # Keep defaults on any parsing error
        pass

def _try_joblib(p: Path) -> Any:
    if joblib is None:
        raise RuntimeError("joblib not available")
    return joblib.load(p)

def _try_dill(p: Path) -> Any:
    if dpickle is None:
        raise RuntimeError("dill not available")
    with open(p, "rb") as f:
        return dpickle.load(f)

def _try_std_pickle(p: Path) -> Any:
    with open(p, "rb") as f:
        return spickle.load(f)

def _load():
    """Load model once. Try joblib first, then dill, then std pickle. Fallback to rule-based."""
    global _model, _model_err, _degraded
    if _model is not None or _model_err is not None:
        return

    # read manifest-driven config first
    _load_manifest_config()

    p = _model_path()
    if not p.exists():
        _model_err = f"Model file not found: {p}"
        _use_rule_based_fallback()
        return

    # Try loaders in order
    errors = []
    for loader_name, loader_func in (
        ("joblib", _try_joblib),
        ("dill", _try_dill),
        ("pickle", _try_std_pickle),
    ):
        try:
            _model = loader_func(p)
            _model_err = None
            return
        except Exception as e:
            errors.append(f"{loader_name}: {type(e).__name__}: {e}")

    # If all failed -> fallback
    _model_err = "Failed to load model → " + " | ".join(errors)
    _use_rule_based_fallback()

def _use_rule_based_fallback():
    """Tiny sentiment heuristic so the app keeps working."""
    global _model, _degraded
    pos = {"love","great","amazing","perfect","good","excellent","nice","recommend","best","beautiful","happy"}
    # Include "tight" as a weak negative cue, but real phrases handled above
    neg = {"bad","worst","poor","terrible","hate","awful","disappoint","return","ugly","broken","sad","tight"}
    class Rule:
        def predict_proba(self, X):
            import numpy as np
            out = []
            for t in X:
                s = (t or "").lower()
                p = sum(w in s for w in pos)
                n = sum(w in s for w in neg)
                prob = (p + 1) / (p + n + 2)  # Laplace smoothing
                out.append([1 - prob, prob])
            return np.array(out, dtype=float)
    _model = Rule()
    _degraded = True

def _post_prob_adjust(text: str, p: float) -> float:
    """Reduce probability if any negative phrase is present; clamp to [0,1]."""
    s = (text or "").lower()
    hits = sum(1 for ph in _NEG_PHRASES if ph in s)
    if hits > 0 and _HEURISTIC_DELTA > 0:
        p = p - hits * _HEURISTIC_DELTA
    if p < 0.0: p = 0.0
    if p > 1.0: p = 1.0
    return p

def _predict_one(text: str):
    if _model is None:
        _load()
    if _model is None:
        raise RuntimeError("Model not loaded")

    # raw probability
    if hasattr(_model, "predict_proba"):
        prob_raw = float(_model.predict_proba([text])[:, 1][0])
    elif hasattr(_model, "decision_function"):
        import numpy as np
        s = float(_model.decision_function([text])[0])
        prob_raw = float(1.0 / (1.0 + np.exp(-s)))
    else:
        y = int(_model.predict([text])[0])
        prob_raw = 0.75 if y == 1 else 0.25

    # adjusted probability (post-heuristic)
    prob_adj = _post_prob_adjust(text, prob_raw)

    # decide label from adjusted prob and configured threshold
    thr = _THRESHOLD if isinstance(_THRESHOLD, float) else 0.60
    label = "Positive" if prob_adj >= thr else "Negative"
    return label, prob_adj, prob_raw

# ---- routes ----------------------------------------------------------------
@bp.route("/predict", methods=["GET"], endpoint="quick_predict")
def quick_predict_view():
    _load()
    err = _model_err
    return render_template(
        "predict.html",
        text="",
        result=None,
        prob=None,
        error=err,
        degraded=_degraded
    )

@bp.route("/api/predict", methods=["POST"], endpoint="api_predict")
def api_predict_view():
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "Empty text"}), 400
        label, prob_adj, prob_raw = _predict_one(text)
        return jsonify({
            "ok": True,
            "label": label,
            "prob": prob_adj,        # adjusted probability (used in UI)
            "prob_raw": prob_raw,    # raw model probability (for debugging/metrics)
            "threshold": _THRESHOLD,
            "degraded": _degraded
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@bp.route("/metrics", methods=["GET"], endpoint="metrics")
def metrics_view():
    _load()
    status = "ready (fallback)" if _degraded else ("ready" if _model and not _model_err else "error")
    manifest = {}
    try:
        p = _manifest_path()
        if p.exists():
            manifest = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        manifest = {}
    # include the config we are using now
    manifest.setdefault("threshold_in_use", _THRESHOLD)
    manifest.setdefault("heuristic_delta_in_use", _HEURISTIC_DELTA)
    manifest.setdefault("neg_phrases_in_use", sorted(list(_NEG_PHRASES)))
    return render_template("metrics.html", status=status, error=_model_err, manifest=manifest)