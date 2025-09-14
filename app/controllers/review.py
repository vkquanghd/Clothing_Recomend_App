# app/controllers/review.py
import sqlite3
from pathlib import Path
from flask import Blueprint, request, jsonify
from .main import get_db_path  # reuse same helper to resolve DB path

bp = Blueprint("review", __name__, url_prefix="/reviews")


# ---------- DB helpers ----------
def conn():
    c = sqlite3.connect(get_db_path())
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON;")
    return c


def _as_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


# ---------- GET one (for edit modal) ----------
@bp.get("/<int:review_id>")
def get_review(review_id: int):
    c = conn()
    row = c.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    c.close()
    if not row:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "item": dict(row)})


# ---------- LIST by item (paged) ----------
@bp.get("/by-item/<int:item_id>")
def list_reviews(item_id: int):
    try:
        page = max(1, int(request.args.get("page", 1)))
    except Exception:
        page = 1
    try:
        per_page = max(1, min(20, int(request.args.get("per_page", 8))))
    except Exception:
        per_page = 8

    offset = (page - 1) * per_page

    c = conn()
    total = c.execute(
        "SELECT COUNT(*) AS c FROM reviews WHERE clothing_id=?",
        (item_id,),
    ).fetchone()["c"]

    rows = c.execute(
        """
        SELECT id, clothing_id, age, title, review_text, rating, recommended, positive_feedback
        FROM reviews
        WHERE clothing_id=?
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (item_id, per_page, offset),
    ).fetchall()
    c.close()

    return jsonify({
        "ok": True,
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "next_page": (page + 1) if (offset + per_page) < total else None,
    })


# ---------- CREATE ----------
@bp.post("/create/<int:item_id>")
def create_review(item_id: int):
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    review_text = (data.get("review_text") or "").strip()
    age = _as_int(data.get("age"), 0)
    rating = _as_int(data.get("rating"), 0)
    recommended = 1 if _as_int(data.get("recommended"), 0) == 1 else 0

    if not title or not review_text or not (1 <= rating <= 5):
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    c = conn()
    cur = c.cursor()
    cur.execute(
        """
        INSERT INTO reviews (clothing_id, age, title, review_text, rating, recommended, positive_feedback)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (item_id, age, title, review_text, rating, recommended, 0),
    )
    c.commit()
    new_id = cur.lastrowid
    c.close()

    return jsonify({"ok": True, "id": new_id})


# ---------- UPDATE ----------
@bp.put("/update/<int:review_id>")
def update_review(review_id: int):
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    review_text = (data.get("review_text") or "").strip()
    rating = _as_int(data.get("rating"), 0)
    recommended = 1 if _as_int(data.get("recommended"), 0) == 1 else 0
    age = _as_int(data.get("age"), 0)  # optional

    if not title or not review_text or not (1 <= rating <= 5):
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    c = conn()
    cur = c.cursor()
    cur.execute(
        """
        UPDATE reviews
        SET age=?, title=?, review_text=?, rating=?, recommended=?
        WHERE id=?
        """,
        (age, title, review_text, rating, recommended, review_id),
    )
    c.commit()
    changed = cur.rowcount
    c.close()

    if changed <= 0:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True})


# ---------- DELETE ----------
@bp.delete("/delete/<int:review_id>")
def delete_review(review_id: int):
    c = conn()
    cur = c.cursor()
    cur.execute("DELETE FROM reviews WHERE id=?", (review_id,))
    c.commit()
    changed = cur.rowcount
    c.close()

    if changed <= 0:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True})