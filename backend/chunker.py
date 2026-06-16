"""Sentence-boundary-aware sliding window text chunker.

Splits extracted document text into overlapping chunks suitable for
vector embedding.  Token count is approximated at 4 chars/token — close
enough for bge-small-en's 512-token context window.

Usage:
    from chunker import chunk_text
    chunks = chunk_text(text, chunk_size=500, overlap=100)
"""

import re
from dataclasses import dataclass

CHUNK_SIZE = 500         # target tokens per chunk
OVERLAP = 100            # overlap tokens between adjacent chunks
CHARS_PER_TOKEN = 4      # rough approximation (good for English prose)

# Boundaries tried in order: paragraph → sentence → word
_SPLIT_RE = re.compile(r'\n\n+|(?<=[.!?])\s+|(?<=\n)\s*(?=[A-Z0-9])')


@dataclass
class Chunk:
    index: int
    text: str
    token_count: int


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = OVERLAP,
) -> list[Chunk]:
    """Return a list of overlapping Chunk objects for *text*."""
    text = _clean(text)
    if not text:
        return []

    chunk_chars = chunk_size * CHARS_PER_TOKEN
    overlap_chars = overlap * CHARS_PER_TOKEN

    # Segment the text on natural boundaries
    segments = [s.strip() for s in _SPLIT_RE.split(text) if s and s.strip()]

    # Degenerate case: single segment longer than chunk_size → hard split
    expanded: list[str] = []
    for seg in segments:
        if len(seg) <= chunk_chars:
            expanded.append(seg)
        else:
            # Force-split on word boundaries
            words = seg.split()
            buf: list[str] = []
            buf_len = 0
            for w in words:
                if buf_len + len(w) + 1 > chunk_chars and buf:
                    expanded.append(" ".join(buf))
                    buf, buf_len = [], 0
                buf.append(w)
                buf_len += len(w) + 1
            if buf:
                expanded.append(" ".join(buf))

    chunks: list[Chunk] = []
    window: list[str] = []
    window_len = 0
    idx = 0

    for seg in expanded:
        seg_len = len(seg) + 1  # +1 for the space separator

        if window_len + seg_len > chunk_chars and window:
            # ── Flush current window ────────────────────────────────────
            body = " ".join(window)
            chunks.append(Chunk(
                index=idx,
                text=body,
                token_count=len(body) // CHARS_PER_TOKEN,
            ))
            idx += 1

            # ── Compute overlap tail ────────────────────────────────────
            tail: list[str] = []
            tail_len = 0
            for s in reversed(window):
                s_len = len(s) + 1
                if tail_len + s_len <= overlap_chars:
                    tail.insert(0, s)
                    tail_len += s_len
                else:
                    break
            window = tail
            window_len = tail_len

        window.append(seg)
        window_len += seg_len

    # ── Flush remaining segments ────────────────────────────────────────
    if window:
        body = " ".join(window)
        chunks.append(Chunk(
            index=idx,
            text=body,
            token_count=len(body) // CHARS_PER_TOKEN,
        ))

    return chunks


def _clean(text: str) -> str:
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()
