"""Multi-document comparison using extracted metadata + LLM narrative."""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 4_000  # per document (reduced so N docs fit in context)
MAX_DOCS = 8

_PROMPT_HEADER = """\
You are a document analyst. Compare the {n} documents below and return structured analysis.
Return ONLY a valid JSON object — no markdown, no prose:
{{
  "similarities": ["<shared characteristic 1>", "<shared characteristic 2>"],
  "differences": [
    {{
      "aspect": "<what differs>",
      "values": ["<value for Doc 1>", "<value for Doc 2>", ...]
    }}
  ],
  "recommendation": "<1-2 sentence conclusion covering all documents>"
}}

Rules:
- similarities: 2-5 bullet points on characteristics shared by most/all documents
- differences: 3-8 key differences; values array MUST have exactly {n} entries (one per doc, in order)
- Use "--" when a value is not found in a document
- recommendation: actionable, neutral, factual

"""

_DOC_BLOCK = """\
--- Document {label}: {name} ---
{context}

"""


def compare_documents(doc_ids: list[str]) -> dict:
    """Load N documents, build per-doc context, run LLM comparison."""
    if len(doc_ids) < 2:
        raise ValueError("At least 2 documents required")
    if len(doc_ids) > MAX_DOCS:
        raise ValueError(f"Maximum {MAX_DOCS} documents per comparison")

    from models import Document, DocumentEntity, DocumentSummary, DocumentText

    docs = []
    for doc_id in doc_ids:
        doc = Document.query.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        dt = DocumentText.query.filter_by(document_id=doc_id).first()
        summary = DocumentSummary.query.filter_by(document_id=doc_id).first()
        entities = DocumentEntity.query.filter_by(document_id=doc_id).all()
        docs.append({
            "id": doc.id,
            "filename": doc.filename,
            "filetype": doc.filetype,
            "page_count": dt.page_count if dt else None,
            "word_count": dt.word_count if dt else None,
            "text": dt.raw_text[:MAX_TEXT_CHARS] if dt else "",
            "headline": summary.headline if summary else "",
            "summary_text": summary.summary_text if summary else "",
            "key_points": summary.key_points if summary else [],
            "entities": [e.to_dict() for e in entities],
        })

    n = len(docs)
    labels = [str(i + 1) for i in range(n)]

    prompt = _PROMPT_HEADER.format(n=n)
    for i, doc in enumerate(docs):
        prompt += _DOC_BLOCK.format(
            label=labels[i],
            name=doc["filename"],
            context=_build_context(doc),
        )
    prompt += "JSON:"

    provider = os.getenv("LLM_PROVIDER", "ollama")
    try:
        raw = _call_gemini(prompt) if provider == "gemini" else _call_ollama(prompt)
        analysis = _parse(raw, n)
    except Exception:
        logger.exception("Comparison LLM call failed")
        analysis = {"similarities": [], "differences": [], "recommendation": ""}

    return {
        "docs": [_public(d) for d in docs],
        "analysis": analysis,
    }


def _build_context(doc: dict) -> str:
    parts = []
    if doc["headline"]:
        parts.append(f"Summary: {doc['headline']}")
    if doc["key_points"]:
        parts.append("Key points:\n" + "\n".join(f"- {p}" for p in doc["key_points"]))
    if doc["entities"]:
        ent_lines = [f"- {e['label']}: {e['value']}" for e in doc["entities"]]
        parts.append("Extracted entities:\n" + "\n".join(ent_lines))
    if doc["text"]:
        parts.append("Excerpt:\n" + doc["text"])
    return "\n\n".join(parts)


def _public(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "filename": doc["filename"],
        "page_count": doc["page_count"],
        "word_count": doc["word_count"],
        "headline": doc["headline"],
        "summary_text": doc["summary_text"],
        "key_points": doc["key_points"],
        "entities": doc["entities"],
    }


def _call_gemini(prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
    )
    return response.text.strip()


def _call_ollama(prompt: str) -> str:
    import requests
    resp = requests.post(
        f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
        json={"model": os.getenv("OLLAMA_MODEL", "llama3.2"), "prompt": prompt, "stream": False},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def _parse(raw: str, n: int) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        diffs = []
        for d in data.get("differences", []):
            aspect = str(d.get("aspect", "")).strip()
            if not aspect:
                continue
            values = d.get("values", [])
            # Pad or trim to exactly n entries
            values = [str(v).strip() for v in values]
            while len(values) < n:
                values.append("--")
            diffs.append({"aspect": aspect, "values": values[:n]})
        return {
            "similarities": [str(s).strip() for s in data.get("similarities", []) if s],
            "differences": diffs,
            "recommendation": str(data.get("recommendation", "")).strip(),
        }
    except (json.JSONDecodeError, TypeError):
        logger.warning("Compare: could not parse LLM JSON output")
        return {"similarities": [], "differences": [], "recommendation": ""}
