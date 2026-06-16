import os
import uuid

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from sqlalchemy import text

from models import db, Session, Document
from storage import upload_file, get_presigned_url, delete_file, DOCUMENT_BUCKET
from storage.minio_client import CONTENT_TYPES

load_dotenv()

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "pptx", "ppt",
    "xlsx", "xls", "csv",
    "png", "jpg", "jpeg", "tiff", "tif",
}


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def run_migrations() -> None:
        with db.engine.connect() as conn:
            for col, definition in [
                ("bucket", "VARCHAR(100)"),
                ("object_key", "VARCHAR(512)"),
            ]:
                conn.execute(text(
                    f"ALTER TABLE documents ADD COLUMN IF NOT EXISTS {col} {definition}"
                ))
            conn.commit()

    with app.app_context():
        db.create_all()
        run_migrations()

    # ── Sessions ────────────────────────────────────────────────────────────

    @app.route("/api/sessions", methods=["POST"])
    def create_session():
        data = request.json or {}
        if not data.get("name"):
            return jsonify({"error": "Session name is required"}), 400
        session = Session(name=data["name"], description=data.get("description"))
        db.session.add(session)
        db.session.commit()
        return jsonify(session.to_dict()), 201

    @app.route("/api/sessions", methods=["GET"])
    def get_sessions():
        sessions = Session.query.order_by(Session.created_at.desc()).all()
        return jsonify([s.to_dict() for s in sessions]), 200

    @app.route("/api/sessions/<id>", methods=["DELETE"])
    def delete_session(id):
        session_obj = Session.query.get(id)
        if not session_obj:
            return jsonify({"error": "Session not found"}), 404
        # Remove all documents from MinIO before deleting the session
        for doc in session_obj.documents:
            if doc.bucket and doc.object_key:
                delete_file(doc.bucket, doc.object_key)
        db.session.delete(session_obj)
        db.session.commit()
        return jsonify({"message": f"Session {id} deleted"}), 200

    # ── Documents ───────────────────────────────────────────────────────────

    @app.route("/api/documents", methods=["POST"])
    def upload_document():
        if "file" not in request.files:
            return jsonify({"error": "No file in request"}), 400

        file = request.files["file"]
        session_id = request.form.get("session_id")

        if not session_id:
            return jsonify({"error": "session_id is required"}), 400
        if not Session.query.get(session_id):
            return jsonify({"error": "Session not found"}), 404
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400

        filename = secure_filename(file.filename)
        ext = filename.rsplit(".", 1)[1].lower()
        doc_id = str(uuid.uuid4())
        object_key = f"{session_id}/{doc_id}/{filename}"
        content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

        data = file.read()
        upload_file(DOCUMENT_BUCKET, object_key, data, content_type)

        doc = Document(
            id=doc_id,
            session_id=session_id,
            filename=filename,
            filetype=ext,
            bucket=DOCUMENT_BUCKET,
            object_key=object_key,
            filepath=object_key,
            status="uploaded",
        )
        db.session.add(doc)
        db.session.commit()
        return jsonify(doc.to_dict()), 201

    @app.route("/api/documents/<session_id>", methods=["GET"])
    def get_documents(session_id):
        if not Session.query.get(session_id):
            return jsonify({"error": "Session not found"}), 404
        docs = Document.query.filter_by(session_id=session_id).all()
        return jsonify([d.to_dict() for d in docs]), 200

    @app.route("/api/documents/<doc_id>/url", methods=["GET"])
    def get_document_url(doc_id):
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        if not doc.bucket or not doc.object_key:
            return jsonify({"error": "Document has no storage reference"}), 400
        url = get_presigned_url(doc.bucket, doc.object_key, expires_hours=1)
        return jsonify({"url": url}), 200

    @app.route("/api/documents/<doc_id>", methods=["DELETE"])
    def delete_document(doc_id):
        doc = Document.query.get(doc_id)
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        if doc.bucket and doc.object_key:
            delete_file(doc.bucket, doc.object_key)
        db.session.delete(doc)
        db.session.commit()
        return jsonify({"message": f"Document {doc_id} deleted"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
