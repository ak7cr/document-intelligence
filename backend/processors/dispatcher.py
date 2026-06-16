from .base import ProcessingResult
from .csv_processor import extract_csv
from .docx_processor import extract_docx
from .pdf_processor import extract_pdf
from .xlsx_processor import extract_excel

_IMAGE_TYPES = {"png", "jpg", "jpeg", "tiff", "tif"}


def dispatch(filetype: str, data: bytes) -> ProcessingResult:
    if filetype == "pdf":
        return extract_pdf(data)
    if filetype in ("docx", "doc"):
        return extract_docx(data)
    if filetype in ("xlsx", "xls"):
        return extract_excel(data)
    if filetype == "csv":
        return extract_csv(data)
    if filetype in _IMAGE_TYPES:
        # OCR pipeline added in Stage 6
        return ProcessingResult(text="", method="ocr_pending", page_count=1)
    raise ValueError(f"Unsupported filetype: {filetype}")
