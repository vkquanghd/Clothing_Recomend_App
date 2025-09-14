# app/controllers/model_info.py
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional, Iterable
from flask import Blueprint, request, render_template, jsonify, current_app, has_app_context

# dill preferred; fallback to std pickle
try:
    import dill as pickle  # pip install dill
except Exception:  # pragma: no cover
    import pickle  # type: ignore

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
        for m in self.models.values():
            if hasattr(m, "predict_proba"):
                probs.append(m.predict_proba(list(texts))[:, 1])
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

def _root() -> Path:
    if has_app_context():
        return Path(current_app.root_path).parent
    return Path(__file__).resolve().parents[2]

def _model_path() -> Path:
    return _root() / "model" / "ensemble_soft.pkl"

def _load():
    global _model, _model_err, _degraded
    if _model is not None or _model_err is not None:
        return
    p = _model_path()
    if not p.exists():
        _model_err = f"Model file not found: {p}"
        _use_rule_based_fallback()
        return
    try:
        with open(p, "rb") as f:
            _model = pickle.load(f)       # dill or pickle
    except Exception as e:
        _model_err = f"Failed to load model: {e!r}"
        _use_rule_based_fallback()

def _use_rule_based_fallback():
    # Tiny sentiment heuristic so the app keeps working
    global _model, _degraded
    pos = {"love","great","amazing","perfect","good","excellent","nice","recommend","best","beautiful","happy"}
    neg = {"bad","worst","poor","terrible","hate","awful","disappoint","return","ugly","broken","sad"}
    class Rule:
        def predict_proba(self, X):
            import numpy as np, re
            out = []
            for t in X:
                s = (t or "").lower()
                p = sum(w in s for w in pos)
                n = sum(w in s for w in neg)
                prob = (p + 1) / (p + n + 2)  # laplace
                out.append([1 - prob, prob])
            return np.array(out, dtype=float)
    _model = Rule()
    _degraded = True

def _predict_one(text: str):
    if _model is None:
        _load()
    if _model is None:
        raise RuntimeError("Model not loaded")

    if hasattr(_model, "predict_proba"):
        prob = float(_model.predict_proba([text])[:, 1][0])
    elif hasattr(_model, "decision_function"):
        import numpy as np
        s = float(_model.decision_function([text])[0])
        prob = float(1.0 / (1.0 + np.exp(-s)))
    else:
        y = int(_model.predict([text])[0])
        prob = 0.75 if y == 1 else 0.25
    label = "Positive" if prob >= 0.5 else "Negative"
    return label, prob

# ---- routes ----------------------------------------------------------------
@bp.get("/predict")
def quick_predict():
    _load()
    # Show error banner (and whether we’re using fallback)
    err = _model_err
    return render_template("predict.html", text="", result=None, prob=None, error=err, degraded=_degraded)

@bp.post("/api/predict")
def api_predict():
    try:
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "Empty text"}), 400
        label, prob = _predict_one(text)
        return jsonify({"ok": True, "label": label, "prob": prob, "degraded": _degraded})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@bp.get("/metrics")
def metrics():
    _load()
    status = "ready (fallback)" if _degraded else ("ready" if _model and not _model_err else "error")
    return render_template("metrics.html", status=status, error=_model_err, manifest={})