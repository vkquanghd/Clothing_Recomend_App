from flask import Flask
from .config import DATA_DIR, MODEL_DIR

def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # Make sure folders exist (no error if missing; app vẫn chạy)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Register blueprints
    from .controllers.main import bp as main_bp
    from .controllers.review import bp as review_bp
    from .controllers.search import bp as search_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(review_bp, url_prefix="/")
    app.register_blueprint(search_bp, url_prefix="/")

    return app

# Flask CLI entry
app = create_app()