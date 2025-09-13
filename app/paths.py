# app/paths.py
import os

APP_DIR      = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, ".."))

DATA_DIR   = os.path.join(PROJECT_ROOT, "data")
MODEL_DIR  = os.path.join(PROJECT_ROOT, "model")

CATALOG_JSON = os.path.join(DATA_DIR, "site_items.json")
BUNDLE_PKL   = os.path.join(MODEL_DIR, "ensemble.pkl")