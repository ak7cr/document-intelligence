"""Gemini Vision OCR — sends rendered page images directly to Gemini.

Far more accurate than EasyOCR/Tesseract on Hindi, mixed-script, and
structured documents (tables, forms). Uses the same gemini-2.0-flash
model already configured for LLM analysis.

Quota: each page = 1 Gemini call. A 6-page PDF = 6 OCR calls.
With 1500 req/day free tier that supports ~250 6-page documents/day.
"""

from __future__ import annotations

import io
import logging
import os

from PIL import Image

logger = logging.getLogger(__name__)


def ocr_image_gemini(img_bytes: bytes) -> tuple[str, float, str]:
    """Extract text from an image using Gemini Vision.

    Returns:
        (text, confidence) — confidence is 0.95 on success, 0.0 on failure.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set in .env — cannot use OCR_ENGINE=gemini"
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError("google-genai not installed. Run: pip install google-genai") from exc

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    client = genai.Client(api_key=api_key)

    # Normalise to PNG
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    prompt = (
        "Extract ALL text from this document image exactly as it appears. "
        "Preserve the original language — do NOT translate Hindi or any other language. "
        "Preserve paragraph and line breaks. "
        "For tables, output each row as: col1 | col2 | col3. "
        "Output only the extracted text — no explanation, no commentary."
    )

    import time
    last_exc: Exception = RuntimeError("no attempt made")
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=png_bytes, mime_type="image/png"),
                    prompt,
                ],
            )
            text = (response.text or "").strip()
            return text, 0.95 if text else 0.0, "gemini"
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            if any(x in msg for x in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")):
                wait = 2 ** attempt  # 1 → 2 → 4 → 8 s
                logger.warning(
                    "Gemini OCR transient error (attempt %d/4): %s — retrying in %ds",
                    attempt + 1, msg[:80], wait,
                )
                time.sleep(wait)
            else:
                break

    logger.error("Gemini OCR failed after retries (%s) — trying EasyOCR then Tesseract", last_exc)

    # Fallback 1: EasyOCR
    try:
        import io as _io
        import numpy as np
        from PIL import Image as _Image
        from .engine import _get_reader, _ocr_strip, _tile
        reader = _get_reader()
        img_array = np.array(_Image.open(_io.BytesIO(img_bytes)).convert("RGB"))
        all_texts, all_scores = [], []
        for strip in _tile(img_array):
            kept = _ocr_strip(reader, strip)
            all_texts.extend(t for t, _ in kept)
            all_scores.extend(s for _, s in kept)
        text = "\n".join(all_texts)
        if text.strip():
            conf = sum(all_scores) / len(all_scores) if all_scores else 0.0
            logger.info("EasyOCR fallback succeeded")
            return text, conf, "easyocr:fallback"
    except Exception as exc:
        logger.warning("EasyOCR fallback failed: %s — trying Tesseract", exc)

    # Fallback 2: Tesseract
    try:
        from .tesseract_engine import ocr_image_tesseract
        text, conf = ocr_image_tesseract(img_bytes)
        logger.info("Tesseract fallback succeeded")
        return text, conf, "tesseract:fallback"
    except Exception as exc:
        logger.error("Tesseract fallback also failed: %s", exc)
        return "", 0.0, "none:failed"
