import uuid

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from models import Document, DocumentText, Session, db
from processing import trigger_processing
from storage import DOCUMENT_BUCKET, delete_file, get_presigned_url, upload_file
from storage.minio_client import CONTENT_TYPES

documents_bp = Blueprint("documents", __name__)

ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "pptx", "ppt",
    "xlsx", "xls", "csv",
    "png", "jpg", "jpeg", "tiff", "tif",
}


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@documents_bp.route("/documents", methods=["POST"])
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
    if not _allowed(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower()
    doc_id = str(uuid.uuid4())
    object_key = f"{session_id}/{doc_id}/{filename}"
    content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

    upload_file(DOCUMENT_BUCKET, object_key, file.read(), content_type)

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
    trigger_processing(doc.id)
    return jsonify(doc.to_dict()), 201


@documents_bp.route("/documents/<session_id>", methods=["GET"])
def get_documents(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    docs = Document.query.filter_by(session_id=session_id).all()
    return jsonify([d.to_dict() for d in docs]), 200


@documents_bp.route("/documents/<doc_id>/url", methods=["GET"])
def get_document_url(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if not doc.bucket or not doc.object_key:
        return jsonify({"error": "Document has no storage reference"}), 400
    url = get_presigned_url(doc.bucket, doc.object_key, expires_hours=1)
    return jsonify({"url": url}), 200


@documents_bp.route("/documents/<doc_id>/text", methods=["GET"])
def get_document_text(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    doc_text = DocumentText.query.filter_by(document_id=doc_id).first()
    if not doc_text:
        return jsonify({"error": "Text not yet extracted", "status": doc.status}), 404
    return jsonify({
        "document_id": doc_id,
        "text": doc_text.raw_text,
        "word_count": doc_text.word_count,
        "page_count": doc_text.page_count,
        "method": doc_text.method,
        "ocr_confidence": doc_text.ocr_confidence,
        "extracted_at": doc_text.extracted_at.isoformat(),
    }), 200


@documents_bp.route("/documents/<doc_id>", methods=["DELETE"])
def delete_document(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.bucket and doc.object_key:
        delete_file(doc.bucket, doc.object_key)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"message": f"Document {doc_id} deleted"}), 200
