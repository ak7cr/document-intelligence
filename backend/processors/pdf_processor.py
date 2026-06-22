import fitz  # PyMuPDF

from ocr import enhance_for_ocr, ocr_image

from .base import ProcessingResult

# Pages with fewer than this many words are treated as scanned/image-only.
_SCANNED_WORD_THRESHOLD = 20


def _is_scanned(text: str) -> bool:
    return len(text.strip().split()) < _SCANNED_WORD_THRESHOLD


def _extract_tables(page: fitz.Page) -> str:
    """Extract tables from a page as markdown using PyMuPDF's table finder.

    Works on both native-text and scanned pages rendered at high DPI.
    Returns empty string if no tables are detected.
    """
    try:
        # Render at 3x for table detection on scanned pages
        mat = fitz.Matrix(3.0, 3.0)
        clip = page.rect
        tabs = page.find_tables(clip=clip)
        if not tabs or not tabs.tables:
            return ""
        parts = []
        for tab in tabs.tables:
            rows = tab.extract()
            if not rows:
                continue
            # Build markdown table
            lines = []
            for i, row in enumerate(rows):
                cells = [str(c or "").replace("\n", " ").strip() for c in row]
                lines.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)
    except Exception:
        return ""


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
            # Append table markdown before prose so LLM sees structured data
            table_md = _extract_tables(page)
            if table_md:
                all_texts.append(table_md + "\n\n" + ocr_text)
            else:
                all_texts.append(ocr_text)
            if conf > 0:
                ocr_confidences.append(conf)
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        else:
            table_md = _extract_tables(page)
            all_texts.append((table_md + "\n\n" + text).strip() if table_md else text)

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
