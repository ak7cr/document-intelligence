"""Tesseract OCR backend — CPU-only, no VRAM, works on any Python version.

Install:
    apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng
    pip install pytesseract
"""

from __future__ import annotations

import io
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def ocr_image_tesseract(img_bytes: bytes) -> tuple[str, float]:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError(
            "pytesseract not installed. Run: pip install pytesseract"
        ) from exc

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    # hin+eng covers Hindi Devanagari + English in the same image
    lang = "hin+eng"
    try:
        data = pytesseract.image_to_data(
            img,
            lang=lang,
            config="--psm 3",  # fully automatic page segmentation
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractError as exc:
        if "hin" in str(exc):
            logger.warning(
                "Hindi language pack missing — falling back to English only. "
                "Install with: apt-get install tesseract-ocr-hin"
            )
            data = pytesseract.image_to_data(
                img, lang="eng", config="--psm 3",
                output_type=pytesseract.Output.DICT,
            )
        else:
            raise

    words, confs = [], []
    for text, conf in zip(data["text"], data["conf"]):
        text = text.strip()
        conf = int(conf)
        if text and conf > 0:
            words.append(text)
            confs.append(conf / 100.0)

    avg_confidence = sum(confs) / len(confs) if confs else 0.0
    return " ".join(words), avg_confidence
