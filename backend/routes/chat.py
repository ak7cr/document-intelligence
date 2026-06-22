import logging

from flask import Blueprint, jsonify, request

from models import ChatHistory, Session, db
from rag import answer_question

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/sessions/<session_id>/messages", methods=["GET"])
def get_messages(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    msgs = ChatHistory.query.filter_by(session_id=session_id).order_by(ChatHistory.created_at).all()
    return jsonify([m.to_dict() for m in msgs]), 200


@chat_bp.route("/sessions/<session_id>/messages", methods=["DELETE"])
def clear_messages(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404
    ChatHistory.query.filter_by(session_id=session_id).delete()
    db.session.commit()
    return jsonify({"message": "Chat history cleared"}), 200


@chat_bp.route("/sessions/<session_id>/chat", methods=["POST"])
def chat(session_id: str):
    if not Session.query.get(session_id):
        return jsonify({"error": "Session not found"}), 404

    data = request.json or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "'question' is required"}), 400

    try:
        result = answer_question(session_id, question)

        # Persist both turns
        db.session.add(ChatHistory(
            session_id=session_id, role="user", content=question,
        ))
        db.session.add(ChatHistory(
            session_id=session_id, role="assistant",
            content=result["answer"],
            sources=result.get("sources"),
            confidence=result.get("confidence"),
        ))
        db.session.commit()

        return jsonify(result), 200
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        logger.exception("Chat error for session %s", session_id)
        return jsonify({"error": "Internal error", "detail": str(exc)}), 500
