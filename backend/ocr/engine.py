"""PaddleOCR wrapper with lazy model initialisation.

Models are downloaded on the first call and cached locally.
The engine singleton is created once per process and reused.

PaddleOCR 3.x API: predict() returns a list of result objects (one per image).
Each result supports dict-style access: result["rec_texts"], result["rec_scores"].
"""

from __future__ import annotations

import io
import logging

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "paddleocr is not installed. Run: pip install paddlepaddle paddleocr"
            ) from exc

        logger.info("Initialising PaddleOCR (first run downloads models)…")
        _ocr = PaddleOCR(
            use_textline_orientation=True,
            lang="en",
        )
        logger.info("PaddleOCR ready")
    return _ocr


def ocr_image(img_bytes: bytes) -> tuple[str, float]:
    """Run OCR on raw image bytes.

    Returns:
        (text, avg_confidence)  — confidence is 0.0 if nothing was detected.
    """
    ocr = _get_ocr()

    img = Image.open(io.BytesIO(img_bytes))
    img_array = np.array(img)

    # predict() returns a list of OCRResult (one per input image)
    results = ocr.predict(img_array)

    if not results:
        return "", 0.0

    result = results[0]
    texts: list = result["rec_texts"]
    scores: list = result["rec_scores"]

    if not texts:
        return "", 0.0

    avg_confidence = sum(float(s) for s in scores) / len(scores) if scores else 0.0
    return "\n".join(str(t) for t in texts), avg_confidence
