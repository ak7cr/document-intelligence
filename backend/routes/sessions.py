from flask import Blueprint, jsonify, request

from models import Session, db
from storage import delete_file
from vector import search_chunks

OCR_CONFIDENCE_THRESHOLD = 0.70

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


@sessions_bp.route("/sessions/<session_id>/ocr-review", methods=["GET"])
def ocr_review(session_id: str):
    from models import Document, DocumentText

    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    items = []
    for doc in docs:
        dt = DocumentText.query.filter_by(document_id=doc.id).first()
        if not dt or dt.method != "ocr":
            continue
        confidence = dt.ocr_confidence
        if confidence is None or confidence < OCR_CONFIDENCE_THRESHOLD:
            items.append({
                "document_id": doc.id,
                "filename": doc.filename,
                "method": dt.method,
                "ocr_confidence": confidence,
                "page_count": dt.page_count,
                "word_count": dt.word_count,
            })

    items.sort(key=lambda x: (x["ocr_confidence"] or 0.0))
    return jsonify({"session_id": session_id, "items": items, "threshold": OCR_CONFIDENCE_THRESHOLD}), 200


@sessions_bp.route("/sessions/<session_id>/entity-graph", methods=["GET"])
def entity_graph(session_id: str):
    from collections import defaultdict
    from models import Document, DocumentEntity

    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    if not docs:
        return jsonify({"session_id": session_id, "clusters": [], "total_shared": 0}), 200

    doc_map = {d.id: d.filename for d in docs}
    doc_ids = list(doc_map.keys())

    entities = DocumentEntity.query.filter(
        DocumentEntity.document_id.in_(doc_ids),
        DocumentEntity.entity_type != "doc_type",
    ).all()

    # Group by (type, normalized value)
    groups: dict[tuple, list] = defaultdict(list)
    for e in entities:
        key = (e.entity_type, e.value.lower().strip())
        groups[key].append(e)

    clusters = []
    for (etype, _), ents in groups.items():
        unique_docs = {e.document_id for e in ents}
        if len(unique_docs) < 2:
            continue
        doc_entries = []
        seen = set()
        for e in ents:
            if e.document_id not in seen:
                seen.add(e.document_id)
                doc_entries.append({
                    "id": e.document_id,
                    "filename": doc_map.get(e.document_id, ""),
                    "label": e.label,
                })
        clusters.append({
            "entity_type": etype,
            "value": ents[0].value,
            "doc_count": len(unique_docs),
            "documents": doc_entries,
        })

    clusters.sort(key=lambda x: (-x["doc_count"], x["entity_type"]))

    return jsonify({
        "session_id": session_id,
        "clusters": clusters,
        "total_shared": len(clusters),
    }), 200




@sessions_bp.route("/sessions/<session_id>/timeline", methods=["GET"])
def session_timeline(session_id: str):
    from datetime import date, datetime
    from models import Document, DocumentEntity

    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    doc_map = {d.id: d.filename for d in docs}

    entities = DocumentEntity.query.filter(
        DocumentEntity.document_id.in_(list(doc_map.keys())),
        DocumentEntity.entity_type.in_(["date", "deadline"]),
    ).all()

    today = date.today()
    items = []
    for ent in entities:
        parsed_date = None
        try:
            from dateutil import parser as dateparser
            parsed_date = dateparser.parse(
                ent.value,
                default=datetime(today.year, today.month, today.day),
            ).date()
        except Exception:
            pass

        days_from_now = None
        urgency = "unknown"
        if parsed_date:
            days_from_now = (parsed_date - today).days
            if days_from_now < 0:
                urgency = "past"
            elif days_from_now <= 7:
                urgency = "critical"
            elif days_from_now <= 30:
                urgency = "soon"
            else:
                urgency = "future"

        items.append({
            "entity_id": ent.id,
            "document_id": ent.document_id,
            "filename": doc_map.get(ent.document_id, ""),
            "label": ent.label,
            "value": ent.value,
            "entity_type": ent.entity_type,
            "parsed_date": parsed_date.isoformat() if parsed_date else None,
            "days_from_now": days_from_now,
            "urgency": urgency,
        })

    items.sort(key=lambda x: (x["parsed_date"] is None, x["parsed_date"] or "9999-99-99"))

    return jsonify({"session_id": session_id, "items": items}), 200


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
