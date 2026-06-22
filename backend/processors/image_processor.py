from ocr import ocr_image

from .base import ProcessingResult


def extract_image(data: bytes) -> ProcessingResult:
    text, confidence, engine = ocr_image(data)
    return ProcessingResult(
        text=text,
        method="ocr",
        page_count=1,
        confidence=confidence,
        ocr_engine=engine,
    )
