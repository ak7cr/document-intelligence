import os

from dotenv import load_dotenv
from flask import Flask, request
from sqlalchemy import text

from celery_app import init_celery
from models import db
from routes import chat_bp, documents_bp, export_bp, sessions_bp
from vector.store import init_collection as init_qdrant

load_dotenv()

_ALLOWED_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}


def create_app() -> Flask:
    app = Flask(__name__)

    if os.getenv("CELERY_WORKER") == "1":
        # Workers hold connections open during slow OCR/embedding; NullPool
        # creates a fresh connection per statement instead of borrowing from
        # the shared pool, so tasks can never starve the web process.
        from sqlalchemy.pool import NullPool
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"poolclass": NullPool}
    else:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,   # discard stale connections silently
        }

    @app.after_request
    def _cors(response):
        origin = request.headers.get("Origin", "")
        if origin in _ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Max-Age"] = "86400"
        return response

    @app.before_request
    def _preflight():
        if request.method == "OPTIONS":
            from flask import make_response
            resp = make_response()
            origin = request.headers.get("Origin", "")
            if origin in _ALLOWED_ORIGINS:
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                resp.headers["Access-Control-Max-Age"] = "86400"
            return resp, 200

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["REDIS_URL"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    db.init_app(app)
    init_celery(app)

    app.register_blueprint(sessions_bp, url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api")
    app.register_blueprint(chat_bp, url_prefix="/api")
    app.register_blueprint(export_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()
        _migrate()
        try:
            init_qdrant()
        except Exception:
            app.logger.warning("Qdrant unavailable at startup — collection will be created on first use")

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
