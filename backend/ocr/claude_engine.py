"""Claude Vision OCR — sends rendered page images directly to Anthropic's Claude.

Mirrors gemini_engine: one API call per page, same extraction prompt, and the
same fallback chain (EasyOCR → Tesseract) when the API call fails.

Model: CLAUDE_OCR_MODEL, falling back to CLAUDE_MODEL (default claude-haiku-4-5).
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time

from PIL import Image

logger = logging.getLogger(__name__)

_PROMPT = (
    "Extract ALL text from this document image exactly as it appears. "
    "Preserve the original language — do NOT translate Hindi or any other language. "
    "Preserve paragraph and line breaks. "
    "For tables, output each row as: col1 | col2 | col3. "
    "Output only the extracted text — no explanation, no commentary."
)

_TRANSIENT_STATUS = {429, 500, 503, 529}


def ocr_image_claude(img_bytes: bytes) -> tuple[str, float, str]:
    """Extract text from an image using Claude Vision.

    Returns:
        (text, confidence, engine_used) — confidence is 0.95 on success,
        0.0 on failure. engine_used is 'claude', '*:fallback', or 'none:failed'.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set in .env — cannot use OCR_ENGINE=claude"
        )

    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic not installed. Run: pip install anthropic") from exc

    model = os.getenv("CLAUDE_OCR_MODEL") or os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

    # Normalise to PNG (also converts TIFF/WebP, which Claude does not accept).
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_png = base64.standard_b64encode(buf.getvalue()).decode("ascii")

    # Retries are handled below, so disable the SDK's own retry loop.
    client = anthropic.Anthropic(api_key=api_key, max_retries=0)

    last_exc: Exception = RuntimeError("no attempt made")
    for attempt in range(4):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=int(os.getenv("CLAUDE_OCR_MAX_TOKENS", "8192")),
                timeout=180.0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": b64_png,
                                },
                            },
                            {"type": "text", "text": _PROMPT},
                        ],
                    }
                ],
            )
            text = "".join(
                block.text for block in resp.content
                if getattr(block, "type", "") == "text"
            ).strip()
            if getattr(resp, "stop_reason", None) == "max_tokens":
                logger.warning("Claude OCR hit max_tokens — page text may be truncated")
            return text, 0.95 if text else 0.0, "claude"
        except Exception as exc:
            last_exc = exc
            status = getattr(exc, "status_code", None)
            msg = str(exc)
            if status in _TRANSIENT_STATUS or "overloaded" in msg.lower():
                wait = 2 ** attempt  # 1 → 2 → 4 → 8 s
                logger.warning(
                    "Claude OCR transient error (attempt %d/4): %s — retrying in %ds",
                    attempt + 1, msg[:80], wait,
                )
                time.sleep(wait)
            else:
                break

    logger.error(
        "Claude OCR failed after retries (%s) — trying EasyOCR then Tesseract",
        last_exc,
    )

    from .engine import local_fallback_ocr
    return local_fallback_ocr(img_bytes)
