# app/controllers/review.py
import sqlite3
from flask import Blueprint, request, jsonify
from pathlib import Path
from .main import get_db_path  # dùng cùng helper để đúng đường DB

bp = Blueprint("review", __name__, url_prefix="/reviews")

def conn():
    c = sqlite3.connect(get_db_path())
    c.row_factory = sqlite3.Row
    return c

# GET one (for edit)
@bp.get("/<int:review_id>")
def get_review(review_id):
    c = conn()
    r = c.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
    c.close()
    if not r: return jsonify({"error":"not found"}), 404
    return jsonify(dict(r))

# LIST (paged) for item
@bp.get("/by-item/<int:item_id>")
def list_reviews(item_id):
    try: page = max(1, int(request.args.get("page", 1)))
    except: page = 1
    try: per = max(1, min(20, int(request.args.get("per_page", 8))))
    except: per = 8
    off = (page-1)*per

    c = conn()
    total = c.execute("SELECT COUNT(*) AS c FROM reviews WHERE clothing_id=?", (item_id,)).fetchone()["c"]
    rows  = c.execute("""
        SELECT id, clothing_id, age, title, review_text, rating, recommended, positive_feedback
        FROM reviews WHERE clothing_id=?
        ORDER BY id DESC LIMIT ? OFFSET ?
    """, (item_id, per, off)).fetchall()
    c.close()

    next_page = page+1 if off+per < total else None
    return jsonify({
        "items": [dict(r) for r in rows],
        "total": total,
        "next_page": next_page
    })

# CREATE
@bp.post("/create/<int:item_id>")
def create_review(item_id):
    data = request.get_json(force=True)
    c = conn()
    c.execute("""
      INSERT INTO reviews (clothing_id, age, title, review_text, rating, recommended, positive_feedback)
      VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (item_id,
          int(data.get("age") or 0),
          data.get("title") or "",
          data.get("review_text") or "",
          int(data.get("rating") or 0),
          int(data.get("recommended") or 0)))
    c.commit(); c.close()
    return jsonify({"ok": True})

# UPDATE
@bp.put("/update/<int:review_id>")
def update_review(review_id):
    data = request.get_json(force=True)
    c = conn()
    c.execute("""
      UPDATE reviews
      SET age=?, title=?, review_text=?, rating=?, recommended=?
      WHERE id=?
    """, (int(data.get("age") or 0),
          data.get("title") or "",
          data.get("review_text") or "",
          int(data.get("rating") or 0),
          int(data.get("recommended") or 0),
          review_id))
    c.commit(); c.close()
    return jsonify({"ok": True})

# DELETE
@bp.delete("/delete/<int:review_id>")
def delete_review(review_id):
    c = conn()
    c.execute("DELETE FROM reviews WHERE id=?", (review_id,))
    c.commit(); c.close()
    return jsonify({"ok": True})