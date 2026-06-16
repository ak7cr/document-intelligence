from ocr import enhance_for_ocr, ocr_image

from .base import ProcessingResult


def extract_image(data: bytes) -> ProcessingResult:
    enhanced = enhance_for_ocr(data)
    text, confidence = ocr_image(enhanced)
    return ProcessingResult(
        text=text,
        method="ocr",
        page_count=1,
        confidence=confidence,
    )
