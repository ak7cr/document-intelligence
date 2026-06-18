import uuid

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from models import CompanyProfile, Document, DocumentChunk, DocumentChecklist, DocumentEntity, DocumentPrediction, DocumentSummary, DocumentText, EligibilityCheck, Session, db
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


@documents_bp.route("/documents/<doc_id>/chunks", methods=["GET"])
def get_document_chunks(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.status != "ready":
        return jsonify({"error": "Document not ready", "status": doc.status}), 409
    chunks = (
        DocumentChunk.query
        .filter_by(document_id=doc_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    return jsonify({
        "document_id": doc_id,
        "chunk_count": len(chunks),
        "chunks": [c.to_dict() for c in chunks],
    }), 200


@documents_bp.route("/documents/<doc_id>/summary", methods=["GET"])
def get_document_summary(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    s = DocumentSummary.query.filter_by(document_id=doc_id).first()
    if not s:
        return jsonify({"error": "No summary yet", "status": doc.status}), 404
    return jsonify(s.to_dict()), 200


@documents_bp.route("/documents/<doc_id>/summarize", methods=["POST"])
def resimmarize_document(doc_id: str):
    """Re-run summarization on demand (e.g. for docs processed pre-Stage 14)."""
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.status != "ready":
        return jsonify({"error": "Document not ready", "status": doc.status}), 409
    doc_text = DocumentText.query.filter_by(document_id=doc_id).first()
    if not doc_text:
        return jsonify({"error": "No extracted text found"}), 404

    try:
        from summarizer import summarize_document
        result = summarize_document(doc_text.raw_text)
        s = DocumentSummary.query.filter_by(document_id=doc_id).first()
        if s:
            s.headline = result["headline"]
            s.summary_text = result["summary_text"]
            s.key_points = result["key_points"]
        else:
            s = DocumentSummary(
                document_id=doc_id,
                headline=result["headline"],
                summary_text=result["summary_text"],
                key_points=result["key_points"],
            )
            db.session.add(s)
        db.session.commit()
        return jsonify(s.to_dict()), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@documents_bp.route("/documents/<doc_id>/extract", methods=["POST"])
def reextract_entities(doc_id: str):
    """Re-run entity extraction for an already-processed document."""
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.status != "ready":
        return jsonify({"error": "Document not ready", "status": doc.status}), 409
    doc_text = DocumentText.query.filter_by(document_id=doc_id).first()
    if not doc_text:
        return jsonify({"error": "No extracted text found"}), 404

    try:
        from extractor import extract_entities
        extracted = extract_entities(doc_text.raw_text)
        DocumentEntity.query.filter_by(document_id=doc_id).delete()
        if extracted.get("doc_type"):
            db.session.add(DocumentEntity(
                document_id=doc_id, entity_type="doc_type",
                label="Document Type", value=extracted["doc_type"],
            ))
        for ent in extracted.get("entities", []):
            if ent.get("type") and ent.get("label") and ent.get("value"):
                db.session.add(DocumentEntity(
                    document_id=doc_id, entity_type=ent["type"],
                    label=ent["label"], value=ent["value"],
                ))
        db.session.commit()
        entities = DocumentEntity.query.filter_by(document_id=doc_id).all()
        return jsonify({"document_id": doc_id, "entities": [e.to_dict() for e in entities]}), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@documents_bp.route("/documents/<doc_id>/entities", methods=["GET"])
def get_document_entities(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    entities = (
        DocumentEntity.query
        .filter_by(document_id=doc_id)
        .order_by(DocumentEntity.entity_type, DocumentEntity.label)
        .all()
    )
    return jsonify({
        "document_id": doc_id,
        "entities": [e.to_dict() for e in entities],
    }), 200


@documents_bp.route("/documents/<doc_id>/prediction", methods=["GET"])
def get_prediction(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    p = DocumentPrediction.query.filter_by(document_id=doc_id).first()
    if not p:
        return jsonify({"error": "No prediction yet", "status": doc.status}), 404
    return jsonify(p.to_dict()), 200


@documents_bp.route("/documents/<doc_id>/predict", methods=["POST"])
def run_prediction(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.status != "ready":
        return jsonify({"error": "Document not ready", "status": doc.status}), 409
    try:
        from predictor import predict_document
        result = predict_document(doc_id)
        p = DocumentPrediction.query.filter_by(document_id=doc_id).first()
        if p:
            p.risk_level = result["risk_level"]
            p.confidence = result["confidence"]
            p.timeline_urgency = result["timeline_urgency"]
            p.risk_factors = result["risk_factors"]
            p.opportunities = result["opportunities"]
            p.recommended_actions = result["recommended_actions"]
        else:
            p = DocumentPrediction(document_id=doc_id, **result)
            db.session.add(p)
        db.session.commit()
        return jsonify(p.to_dict()), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@documents_bp.route("/documents/<doc_id>/eligibility", methods=["GET"])
def get_eligibility(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    check = EligibilityCheck.query.filter_by(document_id=doc_id).first()
    if not check:
        return jsonify({"error": "No eligibility check yet"}), 404
    return jsonify(check.to_dict()), 200


@documents_bp.route("/documents/<doc_id>/eligibility", methods=["POST"])
def run_eligibility(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.status != "ready":
        return jsonify({"error": "Document not ready", "status": doc.status}), 409

    profile = CompanyProfile.query.filter_by(session_id=doc.session_id).first()
    if not profile:
        return jsonify({"error": "No company profile set up for this session"}), 400

    doc_text = DocumentText.query.filter_by(document_id=doc_id).first()
    if not doc_text:
        return jsonify({"error": "No extracted text found"}), 404

    try:
        from eligibility import check_eligibility
        result = check_eligibility(doc_text.raw_text, profile.to_dict())
        check = EligibilityCheck.query.filter_by(document_id=doc_id).first()
        if check:
            check.profile_id = profile.id
            check.score = result["score"]
            check.met = result["met"]
            check.missing = result["missing"]
            check.documents_required = result["documents_required"]
            check.recommendation = result["recommendation"]
        else:
            check = EligibilityCheck(document_id=doc_id, profile_id=profile.id, **result)
            db.session.add(check)
        db.session.commit()
        return jsonify(check.to_dict()), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


@documents_bp.route("/documents/<doc_id>/checklist", methods=["GET"])
def get_checklist(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    cl = DocumentChecklist.query.filter_by(document_id=doc_id).first()
    if not cl:
        return jsonify({"error": "No checklist yet"}), 404
    return jsonify(cl.to_dict()), 200


@documents_bp.route("/documents/<doc_id>/checklist", methods=["POST"])
def run_checklist(doc_id: str):
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    if doc.status != "ready":
        return jsonify({"error": "Document not ready", "status": doc.status}), 409
    doc_text = DocumentText.query.filter_by(document_id=doc_id).first()
    if not doc_text:
        return jsonify({"error": "No extracted text found"}), 404

    try:
        from checklist import build_checklist
        result = build_checklist(doc_text.raw_text)
        cl = DocumentChecklist.query.filter_by(document_id=doc_id).first()
        if cl:
            cl.items = result["items"]
        else:
            cl = DocumentChecklist(document_id=doc_id, items=result["items"])
            db.session.add(cl)
        db.session.commit()
        return jsonify(cl.to_dict()), 200
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 500


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
