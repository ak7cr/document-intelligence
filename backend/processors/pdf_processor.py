import fitz  # PyMuPDF

from .base import ProcessingResult


def extract_pdf(data: bytes) -> ProcessingResult:
    doc = fitz.open(stream=data, filetype="pdf")
    pages: list[str] = []

    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)

    page_count = doc.page_count
    doc.close()
    return ProcessingResult(
        text="\n\n".join(pages),
        method="direct",
        page_count=page_count,
    )
