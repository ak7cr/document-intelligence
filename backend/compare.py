"""Side-by-side document comparison using extracted metadata + LLM narrative."""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 6_000  # per document

_PROMPT = """\
You are a document analyst. Compare the two documents below and return structured analysis.
Return ONLY a valid JSON object — no markdown, no prose:
{{
  "similarities": ["<point 1>", "<point 2>"],
  "differences": [
    {{"aspect": "<what differs>", "doc_a": "<value in Doc A>", "doc_b": "<value in Doc B>"}}
  ],
  "recommendation": "<1-2 sentence conclusion about which is more favourable or what action to take>"
}}

Rules:
- similarities: 2-5 bullet points on shared characteristics
- differences: 3-8 key differences, each with a clear aspect label
- recommendation: actionable, neutral, factual

--- Document A: {name_a} ---
{text_a}

--- Document B: {name_b} ---
{text_b}

JSON:"""


def compare_documents(doc_id_a: str, doc_id_b: str) -> dict:
    """Load both documents, build context, run LLM comparison."""
    from models import Document, DocumentText, DocumentEntity, DocumentSummary

    def _load(doc_id: str):
        doc = Document.query.get(doc_id)
        if not doc:
            raise ValueError(f"Document {doc_id} not found")
        dt = DocumentText.query.filter_by(document_id=doc_id).first()
        entities = DocumentEntity.query.filter_by(document_id=doc_id).all()
        summary = DocumentSummary.query.filter_by(document_id=doc_id).first()
        return {
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
        }

    doc_a = _load(doc_id_a)
    doc_b = _load(doc_id_b)

    prompt = _PROMPT.format(
        name_a=doc_a["filename"],
        text_a=_build_context(doc_a),
        name_b=doc_b["filename"],
        text_b=_build_context(doc_b),
    )

    provider = os.getenv("LLM_PROVIDER", "ollama")
    try:
        raw = _call_gemini(prompt) if provider == "gemini" else _call_ollama(prompt)
        analysis = _parse(raw)
    except Exception:
        logger.exception("Comparison LLM call failed")
        analysis = {"similarities": [], "differences": [], "recommendation": ""}

    return {
        "doc_a": _public(doc_a),
        "doc_b": _public(doc_b),
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
        parts.append("Document excerpt:\n" + doc["text"])
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
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def _parse(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        return {
            "similarities": [str(s).strip() for s in data.get("similarities", []) if s],
            "differences": [
                {
                    "aspect": str(d.get("aspect", "")).strip(),
                    "doc_a": str(d.get("doc_a", "")).strip(),
                    "doc_b": str(d.get("doc_b", "")).strip(),
                }
                for d in data.get("differences", [])
                if d.get("aspect")
            ],
            "recommendation": str(data.get("recommendation", "")).strip(),
        }
    except (json.JSONDecodeError, TypeError):
        logger.warning("Compare: could not parse LLM JSON output")
        return {"similarities": [], "differences": [], "recommendation": ""}
