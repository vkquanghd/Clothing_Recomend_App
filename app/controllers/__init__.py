# app/controllers/__init__.py
# Chỉ cần import các submodule để Flask có thể "thấy" chúng khi from app.controllers import ...
from . import main
from . import review
from . import search

__all__ = ["main", "review", "search"]