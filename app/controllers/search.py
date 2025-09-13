import json
from math import ceil
from urllib.parse import urlencode
from flask import Blueprint, render_template, request, abort, current_app

from ..config import CATALOG_JSON

bp = Blueprint("search", __name__)

# ---------- Data helpers ----------
def _load_items():
    try:
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                items = []
    except Exception as ex:
        current_app.logger.warning(f"Failed to load catalog: {ex}")
        items = []
    # normalize some keys to avoid KeyError in templates
    for it in items:
        it.setdefault("id", None)
        it.setdefault("clothes_title", it.get("Title", ""))
        it.setdefault("clothes_desc", it.get("Review Text", ""))
        it.setdefault("preview", (it.get("clothes_desc") or "")[:100])
        it.setdefault("division", it.get("Division Name", ""))
        it.setdefault("department", it.get("Department Name", ""))
        it.setdefault("class", it.get("Class Name", ""))
    return items

def _match_query(q: str, item: dict) -> bool:
    if not q:
        return True
    hay = " ".join([
        str(item.get("search_text", "")),
        str(item.get("clothes_title", "")),
        str(item.get("clothes_desc", "")),
        str(item.get("Title", "")),
        str(item.get("Review Text", "")),
    ]).lower()
    tokens = q.lower().split()
    return all(tok in hay for tok in tokens)

def _match_filters(item, division, department, klass):
    if division and str(item.get("division", "")).lower() != division.lower():
        return False
    if department and str(item.get("department", "")).lower() != department.lower():
        return False
    if klass and str(item.get("class", "")).lower() != klass.lower():
        return False
    return True

def _facets(items):
    divs = sorted({str(it.get("division", "")).strip() for it in items if str(it.get("division", "")).strip()})
    deps = sorted({str(it.get("department", "")).strip() for it in items if str(it.get("department", "")).strip()})
    clss = sorted({str(it.get("class", "")).strip() for it in items if str(it.get("class", "")).strip()})
    return divs, deps, clss

# ---------- Routes ----------
@bp.get("/search")
def search():
    # read query params
    q          = request.args.get("q", "").strip()
    page       = max(1, int(request.args.get("page", "1") or "1"))
    per_page   = int(request.args.get("per_page", "12") or "12")
    division   = request.args.get("division", "").strip()
    department = request.args.get("department", "").strip()
    klass      = request.args.get("class", "").strip()  # 'class' is fine as query param

    # load and facet
    all_items = _load_items()
    divs, deps, clss = _facets(all_items)

    # filter
    filtered = [it for it in all_items if _match_query(q, it) and _match_filters(it, division, department, klass)]

    # pagination math
    total = len(filtered)
    total_pages = max(1, ceil(total / per_page))
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end   = start + per_page
    page_items = filtered[start:end]

    # Build a base query string for pagination links WITHOUT 'page'
    base_qs = urlencode({
        "q": q,
        "division": division,
        "department": department,
        "class": klass,          # safe here because we're not using it as a Python kwarg
        "per_page": per_page
    })

    return render_template(
        "search.html",
        # filters
        q=q, division=division, department=department, klass=klass,
        # data
        items=page_items, total=total, total_pages=total_pages,
        # pagination
        page=page, per_page=per_page, base_qs=base_qs,
        # facets
        divisions=divs, departments=deps, classes=clss,
    )

@bp.get("/detail/<int:item_id>")
def detail(item_id: int):
    items = _load_items()
    for it in items:
        try:
            if int(it.get("id", -1)) == item_id:
                return render_template("detail.html", item=it)
        except Exception:
            continue
    abort(404)