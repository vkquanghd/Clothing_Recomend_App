# app/controllers/main.py
import math
import sqlite3
from pathlib import Path
from flask import (
    Blueprint, render_template, request, current_app,
    has_app_context, abort, jsonify
)

bp = Blueprint("main", __name__)

# ---------- DB helpers ----------
def _db_path() -> Path:
    """Resolve data/app.db without needing an app context at import time."""
    if has_app_context():
        base = Path(current_app.root_path).parent
    else:
        # app/controllers/main.py -> app/controllers -> app -> project root
        base = Path(__file__).resolve().parents[2]
    return (base / "data" / "app.db").resolve()


def _conn():
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


# ---------- Home ----------
@bp.route("/", methods=["GET"])
def index():
    """Home: card grid with search + pagination."""
    q = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = max(1, min(48, int(request.args.get("per_page", 12) or 12)))
    offset = (page - 1) * per_page

    con = _conn()
    cur = con.cursor()

    # Count for pagination
    if q:
        total = cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM items
            WHERE division   LIKE ?
               OR department LIKE ?
               OR class_name LIKE ?
               OR description LIKE ?
            """,
            tuple([f"%{q}%"] * 4),
        ).fetchone()["c"]
    else:
        total = cur.execute("SELECT COUNT(*) AS c FROM items;").fetchone()["c"]

    total_pages = max(1, math.ceil(total / per_page))

    # Main listing
    if q:
        rows = cur.execute(
            """
            SELECT i.clothing_id, i.division, i.department, i.class_name, i.description,
                   ROUND(AVG(r.rating), 2) AS avg_rating,
                   COUNT(r.id) AS review_count
            FROM items i
            LEFT JOIN reviews r ON r.clothing_id = i.clothing_id
            WHERE i.division   LIKE ?
               OR i.department LIKE ?
               OR i.class_name LIKE ?
               OR i.description LIKE ?
            GROUP BY i.clothing_id
            ORDER BY review_count DESC
            LIMIT ? OFFSET ?
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%", per_page, offset),
        ).fetchall()
    else:
        rows = cur.execute(
            """
            SELECT i.clothing_id, i.division, i.department, i.class_name, i.description,
                   ROUND(AVG(r.rating), 2) AS avg_rating,
                   COUNT(r.id) AS review_count
            FROM items i
            LEFT JOIN reviews r ON r.clothing_id = i.clothing_id
            GROUP BY i.clothing_id
            ORDER BY review_count DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        ).fetchall()

    con.close()

    # Photo helper (maps class_name -> static/photos path if exists)
    class_photo = {
        "Blouses":      "Blouses/casual-white-blouse-women-rsquo-s-fashion.jpg",
        "Casual bottoms": "Casual bottoms/hand-holding-light-brown-beige-pants.jpg",
        "Chemises":     "Chemises/basic-green-shirt-men-rsquo-s-fashion-apparel-studio-shoot.jpg",
        "Dresses":      "Dresses/khaled-ghareeb--NyPn9up_7o-unsplash.jpg",
        "Fine gauge":   "Fine gauge/fernando-lavin-fi5YSQfxbVk-unsplash.jpg",
        "Intimates":    "Intimates/laura-chouette-2sIvempJoI8-unsplash.jpg",
        "Jackets":      "Jackets/caio-coelho-QRN47la37gw-unsplash.jpg",
        "Jeans":        "Jeans/alicia-petresc-BciCcl8tjVU-unsplash.jpg",
        "Knits":        "Knits/nataliya-melnychuk-_iESFap6fgA-unsplash.jpg",
        "Layering":     "Layering/cullen-jones-PQi3Zp1qksc-unsplash.jpg",
        "Legwear":      "Legwear/annie-spratt-JsFx6F2FQz8-unsplash.jpg",
        "Lounge":       "Lounge/fernando-hernandez-p55Oqj-8dyQ-unsplash.jpg",
        "Outerwear":    "Outerwear/anna-evans-YehJ089r0uY-unsplash.jpg",
        "Pants":        "Pants/felirbe-OCmNJnFx44U-unsplash.jpg",
        "Shorts":       "Shorts/kristino-boxers-MDWZ9H6oG7w-unsplash.jpg",
        "Skirts":       "Skirts/laura-chouette-WLSiDqaBeuc-unsplash.jpg",
        "Sleep":        "Sleep/kristina-petrick-AqcgORY1aiM-unsplash.jpg",
        "Sweaters":     "Sweaters/shelter-dg0uHhW0Fd4-unsplash.jpg",
        "Swim":         "Swim/logan-weaver-lgnwvr-XXgTal6eLTA-unsplash.jpg",
        "Trend":        "Trend/pavel-pjatakov-48CYtvgSAWw-unsplash.jpg",
    }

    def photo_for(class_name: str) -> str:
        rel = class_photo.get((class_name or "").strip())
        if not rel:
            return "img/placeholder.jpg"
        static_dir = Path(current_app.static_folder)
        if (static_dir / "photos" / rel).exists():
            return f"photos/{rel}"
        return "img/placeholder.jpg"

    items = []
    for r in rows:
        d = dict(r)
        d["photo"] = photo_for(d["class_name"])
        items.append(d)

    return render_template(
        "index.html",
        items=items,
        query=q,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )


# ---------- Detail ----------
@bp.route("/detail/<int:item_id>", methods=["GET"])
def detail(item_id: int):
    """Detail: item meta + paginated reviews (no prediction columns required)."""
    # review pagination
    rpage = max(1, int(request.args.get("rpage", 1) or 1))
    rper_page = max(1, min(20, int(request.args.get("rper_page", 10) or 10)))
    roffset = (rpage - 1) * rper_page

    con = _conn()
    cur = con.cursor()

    item = cur.execute(
        """
        SELECT clothing_id, division, department, class_name, description
        FROM items WHERE clothing_id = ?
        """,
        (item_id,),
    ).fetchone()
    if not item:
        con.close()
        abort(404, f"No item with id={item_id}")

    # Count reviews
    rtotal = cur.execute(
        "SELECT COUNT(*) AS c FROM reviews WHERE clothing_id = ?",
        (item_id,),
    ).fetchone()["c"]
    rpages = max(1, math.ceil(rtotal / rper_page))

    # NOTE: only select existing columns
    revs = cur.execute(
        """
        SELECT id, age, title, review_text, rating, recommended, positive_feedback
        FROM reviews
        WHERE clothing_id = ?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (item_id, rper_page, roffset),
    ).fetchall()

    con.close()

    # attach photo path like index
    class_name = item["class_name"]
    # reuse photo mapping from index() via a tiny helper
    def photo_for(class_name: str) -> str:
        static_dir = Path(current_app.static_folder)
        mapping = {
            "Blouses":      "Blouses/casual-white-blouse-women-rsquo-s-fashion.jpg",
            "Casual bottoms": "Casual bottoms/hand-holding-light-brown-beige-pants.jpg",
            "Chemises":     "Chemises/basic-green-shirt-men-rsquo-s-fashion-apparel-studio-shoot.jpg",
            "Dresses":      "Dresses/khaled-ghareeb--NyPn9up_7o-unsplash.jpg",
            "Fine gauge":   "Fine gauge/fernando-lavin-fi5YSQfxbVk-unsplash.jpg",
            "Intimates":    "Intimates/laura-chouette-2sIvempJoI8-unsplash.jpg",
            "Jackets":      "Jackets/caio-coelho-QRN47la37gw-unsplash.jpg",
            "Jeans":        "Jeans/alicia-petresc-BciCcl8tjVU-unsplash.jpg",
            "Knits":        "Knits/nataliya-melnychuk-_iESFap6fgA-unsplash.jpg",
            "Layering":     "Layering/cullen-jones-PQi3Zp1qksc-unsplash.jpg",
            "Legwear":      "Legwear/annie-spratt-JsFx6F2FQz8-unsplash.jpg",
            "Lounge":       "Lounge/fernando-hernandez-p55Oqj-8dyQ-unsplash.jpg",
            "Outerwear":    "Outerwear/anna-evans-YehJ089r0uY-unsplash.jpg",
            "Pants":        "Pants/felirbe-OCmNJnFx44U-unsplash.jpg",
            "Shorts":       "Shorts/kristino-boxers-MDWZ9H6oG7w-unsplash.jpg",
            "Skirts":       "Skirts/laura-chouette-WLSiDqaBeuc-unsplash.jpg",
            "Sleep":        "Sleep/kristina-petrick-AqcgORY1aiM-unsplash.jpg",
            "Sweaters":     "Sweaters/shelter-dg0uHhW0Fd4-unsplash.jpg",
            "Swim":         "Swim/logan-weaver-lgnwvr-XXgTal6eLTA-unsplash.jpg",
            "Trend":        "Trend/pavel-pjatakov-48CYtvgSAWw-unsplash.jpg",
        }
        rel = mapping.get((class_name or "").strip())
        if rel and (static_dir / "photos" / rel).exists():
            return f"photos/{rel}"
        return "img/placeholder.jpg"

    item_dict = dict(item)
    item_dict["photo"] = photo_for(class_name)

    return render_template(
        "detail.html",
        item=item_dict,
        reviews=[dict(r) for r in revs],
        rcount=rtotal,
        rpage=rpage,
        rpages=rpages,
    )


# ---------- Review JSON APIs (create / update / delete) ----------
@bp.post("/api/items/<int:item_id>/reviews")
def api_create_review(item_id: int):
    data = request.get_json(silent=True) or {}
    required = ("title", "review_text")
    if not all(data.get(k) for k in required):
        return jsonify(ok=False, error="Title and review_text required"), 400

    age = int(data.get("age") or 0)
    rating = max(1, min(5, int(data.get("rating") or 5)))
    recommended = 1 if int(data.get("recommended") or 0) == 1 else 0
    pf = max(0, int(data.get("positive_feedback") or 0))

    con = _conn()
    cur = con.cursor()
    cur.execute(
        """
        INSERT INTO reviews (clothing_id, age, title, review_text, rating, recommended, positive_feedback)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (item_id, age, data["title"], data["review_text"], rating, recommended, pf),
    )
    con.commit()
    rid = cur.lastrowid
    con.close()
    return jsonify(ok=True, id=rid)


@bp.put("/api/reviews/<int:review_id>")
def api_update_review(review_id: int):
    data = request.get_json(silent=True) or {}
    con = _conn()
    cur = con.cursor()
    cur.execute(
        """
        UPDATE reviews
        SET age = ?, title = ?, review_text = ?, rating = ?, recommended = ?, positive_feedback = ?
        WHERE id = ?
        """,
        (
            int(data.get("age") or 0),
            data.get("title") or "",
            data.get("review_text") or "",
            max(1, min(5, int(data.get("rating") or 5))),
            1 if int(data.get("recommended") or 0) == 1 else 0,
            max(0, int(data.get("positive_feedback") or 0)),
            review_id,
        ),
    )
    con.commit()
    con.close()
    return jsonify(ok=True)


@bp.delete("/api/reviews/<int:review_id>")
def api_delete_review(review_id: int):
    con = _conn()
    cur = con.cursor()
    cur.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    con.commit()
    con.close()
    return jsonify(ok=True)