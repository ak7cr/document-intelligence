import io

import pandas as pd

from .base import ProcessingResult

_ENCODINGS = ("utf-8", "utf-8-sig", "latin-1", "cp1252")


def extract_csv(data: bytes) -> ProcessingResult:
    df: pd.DataFrame | None = None

    for enc in _ENCODINGS:
        try:
            df = pd.read_csv(io.BytesIO(data), encoding=enc)
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    if df is None:
        raise ValueError("Could not parse CSV with any supported encoding")

    return ProcessingResult(
        text=df.to_string(index=False),
        method="direct",
        page_count=1,
    )
