# app/utils/model_loader.py
import sys, types, json
from pathlib import Path
import joblib
import numpy as np

# cache across requests
_CACHE = {"wrap": None, "manifest": None, "name": None}

def _project_root(start: Path) -> Path:
    # .../app/utils -> .../app -> project_root
    return start.resolve().parents[2]

def _model_dir() -> Path:
    return _project_root(Path(__file__)) / "model"

def _wrap_any_model(m):
    """
    Normalize to a unified interface:
      wrap["predict_proba"] -> returns (n,2)
      wrap["predict"]       -> returns (n,)
    """
    if hasattr(m, "predict_proba") and hasattr(m, "predict"):
        def predict_proba(texts):
            proba = m.predict_proba(texts)
            if proba.ndim == 1:
                return np.vstack([1.0 - proba, proba]).T
            return proba
        return {"predict_proba": predict_proba, "predict": m.predict}

    # legacy EnsembleBundle (already has predict_proba/predict)
    if hasattr(m, "predict") and hasattr(m, "predict_proba"):
        def predict_proba(texts):
            proba = m.predict_proba(texts)
            return (np.vstack([1.0 - proba, proba]).T
                    if getattr(proba, "ndim", 1) == 1 else proba)
        return {"predict_proba": predict_proba, "predict": m.predict}

    raise RuntimeError("Unsupported model object; missing predict/predict_proba")

def _load_legacy_with_shim(pkl_path: Path):
    """
    Inject a minimal __main__.EnsembleBundle symbol so the unpickler can resolve it.
    """
    legacy_main = types.ModuleType("__main__")
    class EnsembleBundle:  # placeholder; state is restored by unpickling
        pass
    legacy_main.EnsembleBundle = EnsembleBundle

    prev_main = sys.modules.get("__main__")
    sys.modules["__main__"] = legacy_main
    try:
        obj = joblib.load(pkl_path)
    finally:
        if prev_main is not None:
            sys.modules["__main__"] = prev_main
    return obj

def get_model():
    """
    Returns (wrap, manifest, name).
    - wrap: dict with 'predict' and 'predict_proba'
    - manifest: dict (may be empty)
    - name: string indicating the loaded artifact
    """
    if _CACHE["wrap"] is not None:
        return _CACHE["wrap"], _CACHE["manifest"], _CACHE["name"]

    mdir = _model_dir()
    preferred = mdir / "ensemble_soft.pkl"  # pure sklearn
    legacy    = mdir / "ensemble.pkl"       # notebook-era custom class
    manifest  = mdir / "manifest.json"

    if preferred.exists():
        obj = joblib.load(preferred)
        name = "ensemble_soft.pkl (VotingClassifier)"
    elif legacy.exists():
        try:
            obj = _load_legacy_with_shim(legacy)
            name = "ensemble.pkl (legacy with shim)"
        except Exception:
            obj = joblib.load(legacy)  # re-raise original if still broken
            name = "ensemble.pkl (direct)"
    else:
        raise FileNotFoundError("No model found in model/: expected ensemble_soft.pkl or ensemble.pkl")

    wrap = _wrap_any_model(obj)
    meta = {}
    if manifest.exists():
        try:
            meta = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    _CACHE.update({"wrap": wrap, "manifest": meta, "name": name})
    return wrap, meta, name