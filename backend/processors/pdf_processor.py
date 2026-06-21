import fitz  # PyMuPDF

from ocr import enhance_for_ocr, ocr_image

from .base import ProcessingResult

# Pages with fewer than this many words are treated as scanned/image-only.
_SCANNED_WORD_THRESHOLD = 20


def _is_scanned(text: str) -> bool:
    return len(text.strip().split()) < _SCANNED_WORD_THRESHOLD


def _render_page(page: fitz.Page) -> bytes:
    """Render a PDF page to a PNG at 3× zoom (≈216 DPI) for OCR.

    3× gives enough resolution for Devanagari/Hindi fine strokes and the
    horizontal shirorekha line that connects letters.
    """
    mat = fitz.Matrix(3.0, 3.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def extract_pdf(data: bytes) -> ProcessingResult:
    doc = fitz.open(stream=data, filetype="pdf")
    page_count = doc.page_count

    all_texts: list[str] = []
    had_ocr = False
    ocr_confidences: list[float] = []

    for page in doc:
        text = page.get_text("text")

        if _is_scanned(text):
            had_ocr = True
            img_bytes = _render_page(page)
            enhanced = enhance_for_ocr(img_bytes)
            ocr_text, conf = ocr_image(enhanced)
            all_texts.append(ocr_text)
            if conf > 0:
                ocr_confidences.append(conf)
        else:
            all_texts.append(text)

    doc.close()

    avg_confidence = (
        sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else None
    )

    return ProcessingResult(
        text="\n\n".join(all_texts),
        method="ocr" if had_ocr else "direct",
        page_count=page_count,
        confidence=avg_confidence,
    )
