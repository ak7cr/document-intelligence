from dataclasses import dataclass


@dataclass
class ProcessingResult:
    text: str
    method: str        # 'direct' | 'ocr_pending'
    page_count: int | None = None

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text.strip() else 0
