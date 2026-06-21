from ocr import ocr_image

from .base import ProcessingResult


def extract_image(data: bytes) -> ProcessingResult:
    # Skip enhancement for direct image uploads — they are already clean.
    # enhance_for_ocr (grayscale + contrast boost) is meant for noisy scans
    # and degrades quality on clean PNGs/JPEGs.
    text, confidence = ocr_image(data)
    return ProcessingResult(
        text=text,
        method="ocr",
        page_count=1,
        confidence=confidence,
    )
