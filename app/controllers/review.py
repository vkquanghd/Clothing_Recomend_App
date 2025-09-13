from flask import Blueprint, render_template, request
import numpy as np

from .main import load_bundle

bp = Blueprint("review", __name__)

def _ensemble_predict(texts, bundle):
    """
    Hỗ trợ cả 2 định dạng:
    - bundle là object có .models (dict<name, pipeline>) & .weights (dict<name,float>)
    - hoặc bundle là dict tương đương đã được bọc ở main.load_bundle()
    """
    if bundle is None or not getattr(bundle, "models", None):
        return None, []

    models = bundle.models
    weights = getattr(bundle, "weights", {})
    wsum = sum(weights.values()) or 1.0

    per_model = []
    agg = np.zeros(len(texts), dtype=float)
    for name, pipe in models.items():
        try:
            proba = pipe.predict_proba(texts)[:, 1]
        except Exception:
            # Một số model (nếu logistic) chắc chắn có predict_proba; nếu không, dùng decision_function chuẩn hoá về [0,1]
            df = pipe.decision_function(texts)
            proba = 1 / (1 + np.exp(-df))
        w = float(weights.get(name, 0.0))
        agg += w * proba
        per_model.append((name, float(proba[0])))

    agg = agg / wsum
    return float(agg[0]), sorted(per_model, key=lambda x: x[0])

@bp.route("/predict", methods=["GET", "POST"])
def predict():
    bundle = load_bundle()
    text = None
    proba = None
    result = None

    if request.method == "POST":
        text = (request.form.get("text") or "").strip()
        if text and bundle:
            p, _ = _ensemble_predict([text], bundle)
            if p is not None:
                proba = p
                result = 1 if proba >= 0.5 else 0

    return render_template("predict.html", text=text, proba=proba, result=result)

@bp.route("/new", methods=["GET", "POST"])
def new_review():
    bundle = load_bundle()

    title = review = rating = None
    suggested = None
    suggested_p = None
    per_model = []

    if request.method == "POST":
        title   = (request.form.get("title") or "").strip()
        review  = (request.form.get("review") or "").strip()
        rating  = (request.form.get("rating") or "").strip()
        text = " ".join([t for t in [title, review] if t])

        if text and bundle:
            p, per = _ensemble_predict([text], bundle)
            if p is not None:
                suggested_p = p
                suggested   = 1 if p >= 0.5 else 0
                per_model   = per

    return render_template(
        "new_review.html",
        title=title, review=review, rating=rating,
        suggested=suggested, suggested_p=suggested_p, per_model=per_model
    )