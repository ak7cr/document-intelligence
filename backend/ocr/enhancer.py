"""Basic image enhancement before OCR: grayscale, auto-contrast, sharpen."""

import io

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def enhance_for_ocr(img_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(img_bytes))

    # Normalise mode (handles RGBA, P, CMYK, etc.)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Grayscale
    img = img.convert("L")

    # Auto-contrast (clip 1% of darkest/lightest pixels)
    img = ImageOps.autocontrast(img, cutoff=1)

    # Contrast boost
    img = ImageEnhance.Contrast(img).enhance(1.5)

    # Mild sharpen
    img = img.filter(ImageFilter.SHARPEN)

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
