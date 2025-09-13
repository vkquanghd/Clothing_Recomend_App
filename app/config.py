from pathlib import Path

# /project-root/app/config.py  → BASE_DIR = /project-root/app
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent  # /project-root

DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "model"

CATALOG_JSON = DATA_DIR / "site_items.json"
BUNDLE_PKL   = MODEL_DIR / "ensemble.pkl"
MANIFEST_JSON= MODEL_DIR / "manifest.json"