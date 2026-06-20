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

        import paddle

        # PaddleX 3.7.x calls AnalysisConfig.set_optimization_level() which was
        # removed in PaddlePaddle 3.3.x. Patch it before pipeline init.
        _cfg = paddle.base.libpaddle.AnalysisConfig
        if not hasattr(_cfg, "set_optimization_level"):
            _cfg.set_optimization_level = lambda *_: None
            logger.debug("Patched AnalysisConfig.set_optimization_level (PaddlePaddle 3.3.x compat)")

        if paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0:
            device = "gpu:0"
            logger.info("GPU detected — initialising PaddleOCR on CUDA")
        else:
            device = "cpu"
            logger.info("No GPU detected — initialising PaddleOCR on CPU")

        _ocr = PaddleOCR(
            use_textline_orientation=False,
            lang="en",
            device=device,
        )
        logger.info("PaddleOCR ready on %s", device)
    return _ocr


def ocr_image(img_bytes: bytes) -> tuple[str, float]:
    """Run OCR on raw image bytes.

    Returns:
        (text, avg_confidence)  — confidence is 0.0 if nothing was detected.
    """
    ocr = _get_ocr()

    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img_array = np.array(img)  # shape: (H, W, 3) — PaddleOCR 3.x requires 3-channel

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
