import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from sqlalchemy import text

from celery_app import init_celery
from models import db
from routes import documents_bp, sessions_bp

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REDIS_URL"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    db.init_app(app)
    init_celery(app)

    app.register_blueprint(sessions_bp, url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()
        _migrate()

    return app


def _migrate() -> None:
    """Idempotent column additions for schema evolution."""
    with db.engine.connect() as conn:
        for table, col, definition in [
            ("documents",     "bucket",         "VARCHAR(100)"),
            ("documents",     "object_key",     "VARCHAR(512)"),
            ("document_text", "ocr_confidence", "FLOAT"),
        ]:
            conn.execute(text(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {definition}"
            ))
        conn.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
