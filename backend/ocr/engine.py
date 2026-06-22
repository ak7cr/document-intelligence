"""OCR dispatcher — selects backend based on OCR_ENGINE env var.

OCR_ENGINE=easyocr   (default) GPU-accelerated, good Hindi accuracy, ~100 MB download
OCR_ENGINE=tesseract             CPU-only, no download, needs system packages:
                                 apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng
                                 pip install pytesseract
"""

from __future__ import annotations

import io
import logging
import os

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        try:
            import easyocr
        except ImportError as exc:
            raise RuntimeError(
                "easyocr is not installed. Run: pip install easyocr"
            ) from exc

        try:
            import torch
            use_gpu = torch.cuda.is_available()
        except Exception:
            use_gpu = False

        logger.info("Initialising EasyOCR (en+hi) — GPU=%s", use_gpu)
        _reader = easyocr.Reader(["en", "hi"], gpu=use_gpu)
        logger.info("EasyOCR ready")
    return _reader


_TILE_HEIGHT = 1000   # px — max strip height fed to CRAFT at once
_TILE_OVERLAP = 80    # px — overlap between strips to avoid cutting text
_MIN_CONF = 0.4
_CANVAS_SIZE = 1920   # CRAFT detection canvas cap


def _tile(img_array: np.ndarray) -> list[np.ndarray]:
    """Split a tall image into overlapping horizontal strips."""
    h = img_array.shape[0]
    if h <= _TILE_HEIGHT:
        return [img_array]
    strips = []
    step = _TILE_HEIGHT - _TILE_OVERLAP
    y = 0
    while y < h:
        strip = img_array[y: y + _TILE_HEIGHT]
        if strip.shape[0] > 30:
            strips.append(strip)
        y += step
    return strips


_reader_cpu_only = False


def _move_to_cpu(reader) -> None:
    """Move EasyOCR's detector and recognizer to CPU permanently."""
    global _reader_cpu_only
    if _reader_cpu_only:
        return
    try:
        import torch
        torch.cuda.empty_cache()
        reader.detector.to("cpu")
        reader.recognizer.to("cpu")
        _reader_cpu_only = True
        logger.info("EasyOCR moved permanently to CPU due to VRAM pressure from other processes")
    except Exception as exc:
        logger.warning("Could not move EasyOCR to CPU: %s", exc)


def _ocr_strip(reader, strip: np.ndarray) -> list[tuple[str, float]]:
    """Run EasyOCR on one strip, falling back to CPU on OOM."""
    try:
        results = reader.readtext(strip, adjust_contrast=0.5, canvas_size=_CANVAS_SIZE)
    except RuntimeError as exc:
        if "out of memory" not in str(exc).lower():
            raise
        logger.warning("GPU OOM — moving EasyOCR to CPU for the rest of this session")
        _move_to_cpu(reader)
        results = reader.readtext(strip, adjust_contrast=0.5, canvas_size=_CANVAS_SIZE)

    kept = [(r[1], float(r[2])) for r in results if float(r[2]) >= _MIN_CONF]
    return kept or [(r[1], float(r[2])) for r in results]


def ocr_image(img_bytes: bytes) -> tuple[str, float]:
    """Run OCR on raw image bytes using the configured backend.

    Returns:
        (text, avg_confidence) — confidence is 0.0 if nothing detected.
    """
    if os.getenv("OCR_ENGINE", "easyocr").lower() == "tesseract":
        from .tesseract_engine import ocr_image_tesseract
        return ocr_image_tesseract(img_bytes)

    reader = _get_reader()

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_array = np.array(img)

    all_texts: list[str] = []
    all_scores: list[float] = []

    for strip in _tile(img_array):
        kept = _ocr_strip(reader, strip)
        all_texts.extend(t for t, _ in kept)
        all_scores.extend(s for _, s in kept)
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    if not all_texts:
        return "", 0.0

    avg_confidence = sum(all_scores) / len(all_scores) if all_scores else 0.0
    return "\n".join(all_texts), avg_confidence
