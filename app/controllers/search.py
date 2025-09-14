# app/controllers/search.py
from __future__ import annotations
from flask import Blueprint, render_template, request, current_app
import sqlite3

bp = Blueprint("search", __name__)

def get_db() -> sqlite3.Connection:
    db_path = current_app.config["DB_PATH"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@bp.route("/search")
def search():
    """
    Keyword + facet search (division/department/class) + pagination.
    Renders the SAME 'index.html' grid for consistency.
    """
    q = request.args.get("q", "").strip().lower()
    division = request.args.get("division", "").strip().lower()
    department = request.args.get("department", "").strip().lower()
    clazz = request.args.get("class", "").strip().lower()
    page = max(1, int(request.args.get("page", 1)))
    page_size = 30
    offset = (page - 1) * page_size

    where = []
    params = []

    if q:
        where.append("(LOWER(i.clothes_title) LIKE ? OR LOWER(i.description) LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if division:
        where.append("LOWER(i.division) = ?")
        params.append(division)
    if department:
        where.append("LOWER(i.department) = ?")
        params.append(department)
    if clazz:
        where.append("LOWER(i.class_name) = ?")
        params.append(clazz)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_db()

    # total count of distinct items matching filters
    total = conn.execute(
        f"""
        SELECT COUNT(*) AS cnt
        FROM (
            SELECT i.clothing_id
            FROM items i
            LEFT JOIN reviews r ON r.clothing_id = i.clothing_id
            {where_sql}
            GROUP BY i.clothing_id
        ) x
        """
    , params).fetchone()["cnt"]

    # page data
    items = conn.execute(
        f"""
        SELECT i.clothing_id, i.clothes_title, i.description, i.division, i.department, i.class_name,
               COUNT(r.id) AS review_count,
               ROUND(AVG(r.rating), 2) AS avg_rating
        FROM items i
        LEFT JOIN reviews r ON r.clothing_id = i.clothing_id
        {where_sql}
        GROUP BY i.clothing_id
        ORDER BY review_count DESC
        LIMIT ? OFFSET ?;
        """,
        (*params, page_size, offset)
    ).fetchall()

    conn.close()

    total_pages = max(1, (total + page_size - 1) // page_size)

    return render_template(
        "index.html",
        items=items,
        query=q,
        page=page,
        total_pages=total_pages,
        division=division,
        department=department,
        clazz=clazz,
        # small flag to let template know it is a "search" context if you want
        is_search=True,
    )