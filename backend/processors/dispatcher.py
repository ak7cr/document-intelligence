from .base import ProcessingResult
from .csv_processor import extract_csv
from .docx_processor import extract_docx
from .image_processor import extract_image
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
        return extract_image(data)
    raise ValueError(f"Unsupported filetype: {filetype}")
