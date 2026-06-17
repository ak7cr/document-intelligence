from flask import Blueprint, jsonify, request

from models import Session, db
from storage import delete_file
from vector import search_chunks

sessions_bp = Blueprint("sessions", __name__)


@sessions_bp.route("/sessions", methods=["POST"])
def create_session():
    data = request.json or {}
    if not data.get("name"):
        return jsonify({"error": "Session name is required"}), 400
    session = Session(name=data["name"], description=data.get("description"))
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_dict()), 201


@sessions_bp.route("/sessions", methods=["GET"])
def get_sessions():
    sessions = Session.query.order_by(Session.created_at.desc()).all()
    return jsonify([s.to_dict() for s in sessions]), 200


@sessions_bp.route("/sessions/<session_id>/search", methods=["GET"])
def search_session(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    limit = min(int(request.args.get("limit", 5)), 20)
    results = search_chunks(q, session_id=session_id, top_k=limit)
    return jsonify({"query": q, "results": results}), 200


@sessions_bp.route("/sessions/<session_id>/analytics", methods=["GET"])
def session_analytics(session_id: str):
    from collections import Counter
    from models import Document, DocumentChunk, DocumentEntity, DocumentText

    session = Session.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id).order_by(Document.uploaded_at).all()

    # ── Totals ────────────────────────────────────────────────────────────────
    status_counts: dict[str, int] = Counter(d.status for d in docs)  # type: ignore[assignment]
    total_pages = 0
    total_words = 0
    total_chunks = 0
    for doc in docs:
        dt = DocumentText.query.filter_by(document_id=doc.id).first()
        if dt:
            total_pages += dt.page_count or 0
            total_words += dt.word_count or 0
        total_chunks += DocumentChunk.query.filter_by(document_id=doc.id).count()

    all_entities = DocumentEntity.query.filter(
        DocumentEntity.document_id.in_([d.id for d in docs])
    ).all()

    # ── Breakdowns ────────────────────────────────────────────────────────────
    filetype_counts: dict[str, int] = Counter(d.filetype for d in docs)  # type: ignore[assignment]
    entity_type_counts: dict[str, int] = Counter(e.entity_type for e in all_entities)  # type: ignore[assignment]

    # Top entities per type (max 5 per type)
    top_entities: dict[str, list[dict]] = {}
    for etype in entity_type_counts:
        if etype == "doc_type":
            continue
        vals: list[str] = [e.value for e in all_entities if e.entity_type == etype]
        top: list[dict] = [{"value": v, "count": c} for v, c in Counter(vals).most_common(5)]
        if top:
            top_entities[etype] = top

    # ── Upload timeline (by date) ──────────────────────────────────────────────
    date_counts: dict[str, int] = Counter(  # type: ignore[assignment]
        d.uploaded_at.strftime("%Y-%m-%d") for d in docs
    )
    timeline = [{"date": k, "count": v} for k, v in sorted(date_counts.items())]

    return jsonify({
        "session_id": session_id,
        "session_name": session.name,
        "totals": {
            "documents": len(docs),
            "ready": status_counts.get("ready", 0),
            "processing": status_counts.get("processing", 0) + status_counts.get("uploaded", 0),
            "failed": status_counts.get("failed", 0),
            "pages": total_pages,
            "words": total_words,
            "chunks": total_chunks,
            "entities": len(all_entities),
        },
        "doc_types": dict(filetype_counts),
        "entity_types": dict(entity_type_counts),
        "top_entities": top_entities,
        "timeline": timeline,
    }), 200


@sessions_bp.route("/sessions/<session_id>/compare", methods=["POST"])
def compare_session_docs(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    data = request.json or {}
    doc_ids = data.get("doc_ids", [])
    if len(doc_ids) < 2:
        return jsonify({"error": "At least 2 doc_ids required"}), 400
    try:
        from compare import compare_documents
        result = compare_documents(doc_ids)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "Comparison failed", "detail": str(exc)}), 500


@sessions_bp.route("/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    session_obj = Session.query.get(session_id)
    if not session_obj:
        return jsonify({"error": "Session not found"}), 404
    for doc in session_obj.documents:
        if doc.bucket and doc.object_key:
            delete_file(doc.bucket, doc.object_key)
    db.session.delete(session_obj)
    db.session.commit()
    return jsonify({"message": f"Session {session_id} deleted"}), 200
