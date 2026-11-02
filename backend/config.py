"""Runtime configuration store — overrides env vars without restarting the worker.

The OCR-engine override is persisted to a small file (not just an in-process
dict) so the Flask API and the Celery worker — separate processes — agree on
which engine to use.
"""

import os
from pathlib import Path

VALID_OCR_ENGINES = {"gemini", "claude", "easyocr", "tesseract"}

_OVERRIDE_FILE = Path(__file__).with_name(".ocr_engine_override")


def _read_override() -> str | None:
    try:
        value = _OVERRIDE_FILE.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return None
    return value if value in VALID_OCR_ENGINES else None


def get_ocr_engine() -> str:
    return _read_override() or os.getenv("OCR_ENGINE", "easyocr").strip().lower()


def set_ocr_engine(engine: str) -> None:
    engine = engine.strip().lower()
    if engine not in VALID_OCR_ENGINES:
        raise ValueError(f"Unknown OCR engine: {engine}. Valid: {VALID_OCR_ENGINES}")
    _OVERRIDE_FILE.write_text(engine, encoding="utf-8")
