import json
import sys
from types import SimpleNamespace
from flask import Blueprint, render_template, current_app
import joblib

from ..config import CATALOG_JSON, BUNDLE_PKL, MANIFEST_JSON

bp = Blueprint("main", __name__)

_bundle_cache = None

def _shim_for_notebook_pickles():
    """
    Khi file ensemble.pkl được dump từ notebook, class EnsembleBundle
    có module='__main__'. Lúc Flask chạy, __main__ là trình chạy flask,
    không có class này → lỗi. Ta đăng ký một class trùng tên vào sys.modules['__main__'].
    """
    try:
        import types
        main_mod = sys.modules.get("__main__")
        if main_mod is None:
            main_mod = types.ModuleType("__main__")
            sys.modules["__main__"] = main_mod
        if not hasattr(main_mod, "EnsembleBundle"):
            class EnsembleBundle:
                # Chỉ cần tối thiểu cho unpickle: thuộc tính sẽ được set lại từ pickle
                def __init__(self, *args, **kwargs):
                    pass
            setattr(main_mod, "EnsembleBundle", EnsembleBundle)
    except Exception:
        # Không crash app nếu shim thất bại; load() sẽ thử tiếp
        pass

def load_bundle():
    global _bundle_cache
    if _bundle_cache is not None:
        return _bundle_cache

    bundle = None
    try:
        _shim_for_notebook_pickles()
        bundle = joblib.load(BUNDLE_PKL)
        # Nếu bundle là dict → bọc nhẹ cho template dễ truy cập
        if isinstance(bundle, dict):
            bundle = SimpleNamespace(**bundle)
        # Đảm bảo có .models/.weights
        if not hasattr(bundle, "models") and isinstance(getattr(bundle, "__dict__", {}), dict):
            # hợp thức hoá tối thiểu nếu pickle cũ không có thuộc tính
            setattr(bundle, "models", getattr(bundle, "models", {}))
        if not hasattr(bundle, "weights"):
            setattr(bundle, "weights", getattr(bundle, "weights", {}))
    except Exception as e:
        current_app.logger.error("Failed to load bundle: %s", e, exc_info=True)
        bundle = None

    _bundle_cache = bundle
    return bundle

def load_manifest():
    try:
        with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

@bp.get("/")
def index():
    return render_template("index.html")

@bp.get("/metrics")
def metrics():
    bundle = load_bundle()
    manifest = load_manifest()
    # manifest có thể là None; template xử lý được
    return render_template("metrics.html", bundle=bundle, manifest=manifest)