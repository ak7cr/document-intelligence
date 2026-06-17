"""PaddleOCR wrapper with lazy model initialisation.

Models are downloaded (~100 MB) on the first call and cached locally.
The engine singleton is created once per process and reused.
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

        logger.info("Initialising PaddleOCR (first run downloads ~100 MB of models)…")
        _ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
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

    result = ocr.ocr(img_array, cls=True)

    if not result or not result[0]:
        return "", 0.0

    lines: list[str] = []
    confidences: list[float] = []

    for line in result[0]:
        if line and len(line) >= 2:
            lines.append(str(line[1][0]))
            confidences.append(float(line[1][1]))

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return "\n".join(lines), avg_confidence
