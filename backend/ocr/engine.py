"""EasyOCR wrapper with lazy model initialisation.

Replaces PaddleOCR 3.x which has irrecoverable version compatibility issues
between paddleocr/paddlex 3.7.x and the available paddlepaddle wheels.

EasyOCR uses PyTorch (already in the env via sentence-transformers) and has
no C++ binary compatibility issues. Models download on first use (~100 MB).
"""

from __future__ import annotations

import io
import logging

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

        logger.info("Initialising EasyOCR (first run downloads models)… GPU=%s", use_gpu)
        _reader = easyocr.Reader(["en", "hi"], gpu=use_gpu)
        logger.info("EasyOCR ready")
    return _reader


def ocr_image(img_bytes: bytes) -> tuple[str, float]:
    """Run OCR on raw image bytes.

    Returns:
        (text, avg_confidence) — confidence is 0.0 if nothing detected.
    """
    reader = _get_reader()

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_array = np.array(img)

    results = reader.readtext(img_array)

    if not results:
        return "", 0.0

    texts = [r[1] for r in results]
    scores = [float(r[2]) for r in results]

    avg_confidence = sum(scores) / len(scores) if scores else 0.0
    return "\n".join(texts), avg_confidence
