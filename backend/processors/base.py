from dataclasses import dataclass


@dataclass
class ProcessingResult:
    text: str
    method: str              # 'direct' | 'ocr' | 'ocr_pending'
    page_count: int | None = None
    confidence: float | None = None   # avg OCR confidence 0–1, None for direct

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text.strip() else 0
