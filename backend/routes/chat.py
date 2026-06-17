from flask import Blueprint, jsonify, request

from models import Session
from rag import answer_question

chat_bp = Blueprint("chat", __name__)


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
        return jsonify(result), 200
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": "Internal error", "detail": str(exc)}), 500
