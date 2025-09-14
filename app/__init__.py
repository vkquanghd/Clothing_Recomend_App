from flask import Flask
from pathlib import Path

def create_app():
    app = Flask(__name__)
    app.config["DB_PATH"] = str((Path(__file__).resolve().parent.parent / "data" / "app.db"))

    # Blueprints
    from .controllers.main import bp as main_bp
    app.register_blueprint(main_bp)

    from .controllers.model_info import bp as model_info_bp
    app.register_blueprint(model_info_bp)         # url_prefix='/model'

    return app