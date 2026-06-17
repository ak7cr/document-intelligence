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
