from flask import Blueprint, jsonify, request
from config import VALID_OCR_ENGINES, get_ocr_engine, set_ocr_engine

config_bp = Blueprint("config", __name__)


@config_bp.route("/config/ocr-engine", methods=["GET"])
def get_engine():
    return jsonify({"ocr_engine": get_ocr_engine(), "valid": sorted(VALID_OCR_ENGINES)}), 200


@config_bp.route("/config/ocr-engine", methods=["POST"])
def set_engine():
    engine = (request.json or {}).get("ocr_engine", "").lower()
    try:
        set_ocr_engine(engine)
        return jsonify({"ocr_engine": get_ocr_engine()}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
