import io

import pandas as pd

from .base import ProcessingResult


def extract_excel(data: bytes) -> ProcessingResult:
    # pandas handles both .xlsx (openpyxl) and .xls (xlrd) automatically
    sheets: dict = pd.read_excel(io.BytesIO(data), sheet_name=None)

    parts: list[str] = []
    for sheet_name, df in sheets.items():
        parts.append(f"[Sheet: {sheet_name}]")
        if not df.empty:
            parts.append(df.to_string(index=False))
        parts.append("")

    return ProcessingResult(
        text="\n".join(parts),
        method="direct",
        page_count=len(sheets),
    )
