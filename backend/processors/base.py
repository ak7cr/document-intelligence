from dataclasses import dataclass


@dataclass
class ProcessingResult:
    text: str
    method: str              # 'direct' | 'ocr'
    page_count: int | None = None
    confidence: float | None = None   # avg OCR confidence 0–1, None for direct
    ocr_engine: str | None = None     # 'gemini' | 'easyocr' | 'tesseract' | 'easyocr:fallback' | 'tesseract:fallback'

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text.strip() else 0
