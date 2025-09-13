import os, json
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash
import joblib

bp = Blueprint("main", __name__)

# ---------------------------
# Helpers
# ---------------------------
_BUNDLE = None

def get_bundle():
    """Load joblib bundle once (EnsembleBundle from notebook)."""
    global _BUNDLE
    if _BUNDLE is None:
        path = current_app.config["MODEL_BUNDLE_PATH"]
        if os.path.exists(path):
            _BUNDLE = joblib.load(path)
        else:
            _BUNDLE = None
    return _BUNDLE

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def load_catalog():
    return load_json(current_app.config["CATALOG_PATH"], [])

def load_reviews():
    return load_json(current_app.config["REVIEWS_PATH"], [])

def save_reviews(rows):
    return save_json(current_app.config["REVIEWS_PATH"], rows)

def normalize(s: str):
    # very simple normalize for search
    s = "".join(ch.lower() if (ch.isalnum() or ch.isspace()) else " " for ch in s)
    return " ".join(s.split())

# ---------------------------
# Template context
# ---------------------------
@bp.app_context_processor
def inject_flags():
    bundle_path = current_app.config["MODEL_BUNDLE_PATH"]
    has_model = os.path.exists(bundle_path)
    return {"has_model": has_model}

# ---------------------------
# Routes
# ---------------------------
@bp.route("/")
def index():
    return render_template("index.html")

@bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    items = load_catalog()
    matches = items
    if q:
        ntoks = normalize(q).split()
        matches = [it for it in items if all(tok in it.get("search_text", "") for tok in ntoks)]
    return render_template("search.html", q=q, items=matches, total=len(matches))

@bp.route("/item/<int:item_id>")
def item_detail(item_id):
    items = load_catalog()
    item = next((it for it in items if it.get("id") == item_id), None)
    if not item:
        flash("Item not found.", "warning")
        return redirect(url_for("main.search"))
    return render_template("detail.html", item=item)

@bp.route("/reviews/new", methods=["GET", "POST"])
def new_review():
    if request.method == "GET":
        item_id = request.args.get("item_id", type=int)
        return render_template("new_review.html", item_id=item_id, suggested=None)

    # POST
    title   = request.form.get("title", "").strip()
    text    = request.form.get("review_text", "").strip()
    rating  = request.form.get("rating", type=int)
    item_id = request.form.get("item_id", type=int)

    if not text:
        flash("Review text is required.", "warning")
        return redirect(url_for("main.new_review", item_id=item_id))

    # model inference
    bundle = get_bundle()
    if bundle is None:
        flash("Model bundle not found. Please export model/ensemble.pkl.", "danger")
        return render_template("new_review.html", item_id=item_id, title=title, review_text=text, rating=rating, suggested=None)

    prob = float(bundle.predict_proba([text])[0])
    suggested_label = 1 if prob >= 0.5 else 0

    # First pass → show suggestion allowing override
    if request.form.get("confirm") != "yes":
        return render_template(
            "new_review.html",
            item_id=item_id, title=title, review_text=text, rating=rating,
            suggested={"prob": prob, "label": suggested_label}
        )

    # Confirmed → persist review
    final_label = int(request.form.get("label", suggested_label))
    rows = load_reviews()
    new_id = (max([r["id"] for r in rows]) + 1) if rows else 1
    rec = {
        "id": new_id,
        "item_id": item_id,
        "title": title,
        "review_text": text,
        "rating": rating,
        "model_prob": prob,
        "suggested_label": suggested_label,
        "final_label": final_label,
    }
    rows.append(rec)
    save_reviews(rows)
    return redirect(url_for("main.review_detail", review_id=new_id))

@bp.route("/reviews/<int:review_id>")
def review_detail(review_id):
    rows = load_reviews()
    r = next((x for x in rows if x.get("id") == review_id), None)
    if not r:
        flash("Review not found.", "warning")
        return redirect(url_for("main.index"))
    item = None
    if r.get("item_id"):
        items = load_catalog()
        item = next((it for it in items if it.get("id") == r["item_id"]), None)
    return render_template("review_detail.html", review=r, item=item)

@bp.route("/metrics")
def metrics():
    manifest_path = current_app.config["MODEL_MANIFEST_PATH"]
    bundle_path   = current_app.config["MODEL_BUNDLE_PATH"]
    exists = os.path.exists(bundle_path)
    manifest = load_json(manifest_path, None)
    return render_template("metrics.html", exists=exists, manifest=manifest, bundle_path=bundle_path)