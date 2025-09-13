import os
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Đường dẫn mặc định cho model + data (tương đối với project root)
    app.config.setdefault("MODEL_BUNDLE_PATH", os.path.join("model", "ensemble.pkl"))
    app.config.setdefault("MODEL_MANIFEST_PATH", os.path.join("model", "manifest.json"))
    app.config.setdefault("CATALOG_PATH", os.path.join("data", "site_items.json"))
    app.config.setdefault("REVIEWS_PATH", os.path.join("data", "reviews.json"))

    # Blueprint
    from .controllers.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app