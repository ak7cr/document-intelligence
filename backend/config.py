"""Runtime configuration store — overrides env vars without restarting the worker."""

import os

_overrides: dict[str, str] = {}

VALID_OCR_ENGINES = {"gemini", "easyocr", "tesseract"}


def get_ocr_engine() -> str:
    return _overrides.get("ocr_engine", os.getenv("OCR_ENGINE", "easyocr")).lower()


def set_ocr_engine(engine: str) -> None:
    if engine not in VALID_OCR_ENGINES:
        raise ValueError(f"Unknown OCR engine: {engine}. Valid: {VALID_OCR_ENGINES}")
    _overrides["ocr_engine"] = engine
