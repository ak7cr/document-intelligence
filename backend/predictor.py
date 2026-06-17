"""AI risk assessment and prediction for a single document."""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 10_000

_PROMPT = """\
You are a procurement and tender risk analyst. Analyze the document below and return a structured risk assessment.
Return ONLY a valid JSON object — no markdown, no prose:
{{
  "risk_level": "<low|medium|high>",
  "confidence": <0.0-1.0>,
  "timeline_urgency": "<brief description of deadline urgency, or 'No deadline found' if none>",
  "risk_factors": [
    "<specific risk 1>",
    "<specific risk 2>"
  ],
  "opportunities": [
    "<opportunity or positive indicator 1>",
    "<opportunity or positive indicator 2>"
  ],
  "recommended_actions": [
    "<concrete action 1>",
    "<concrete action 2>"
  ]
}}

Scoring guidelines:
- low risk: clear terms, reasonable deadlines, known parties, standard amounts
- medium risk: some ambiguous terms, tight timeline, unfamiliar party, or moderate value
- high risk: very tight deadline (<7 days), very large amounts, unusual clauses, missing critical info
- confidence: how certain you are given the available information (1.0 = very certain)
- risk_factors: 2-5 specific concerns found in the document
- opportunities: 2-4 positive indicators or actionable advantages
- recommended_actions: 2-4 concrete next steps

Document context:
{context}

JSON:"""


def predict_document(doc_id: str) -> dict:
    """Run risk prediction for a document. Returns prediction dict."""
    from models import Document, DocumentEntity, DocumentSummary, DocumentText

    doc = Document.query.get(doc_id)
    if not doc:
        raise ValueError(f"Document {doc_id} not found")

    dt = DocumentText.query.filter_by(document_id=doc_id).first()
    summary = DocumentSummary.query.filter_by(document_id=doc_id).first()
    entities = DocumentEntity.query.filter_by(document_id=doc_id).all()

    context_parts = []
    if summary and summary.headline:
        context_parts.append(f"Headline: {summary.headline}")
    if summary and summary.key_points:
        context_parts.append("Key points:\n" + "\n".join(f"- {p}" for p in summary.key_points))
    if entities:
        ent_lines = [f"- {e.label}: {e.value}" for e in entities]
        context_parts.append("Extracted entities:\n" + "\n".join(ent_lines))
    if dt:
        context_parts.append(f"Document text excerpt:\n{dt.raw_text[:MAX_TEXT_CHARS]}")

    context = "\n\n".join(context_parts)
    prompt = _PROMPT.format(context=context)

    provider = os.getenv("LLM_PROVIDER", "ollama")
    try:
        raw = _call_gemini(prompt) if provider == "gemini" else _call_ollama(prompt)
        return _parse(raw)
    except Exception:
        logger.exception("Prediction LLM call failed for document %s", doc_id)
        return {
            "risk_level": "unknown",
            "confidence": 0.0,
            "timeline_urgency": "",
            "risk_factors": [],
            "opportunities": [],
            "recommended_actions": [],
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
        risk_level = str(data.get("risk_level", "unknown")).lower().strip()
        if risk_level not in ("low", "medium", "high"):
            risk_level = "unknown"
        return {
            "risk_level": risk_level,
            "confidence": min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
            "timeline_urgency": str(data.get("timeline_urgency", "")).strip(),
            "risk_factors": [str(r).strip() for r in data.get("risk_factors", []) if r],
            "opportunities": [str(o).strip() for o in data.get("opportunities", []) if o],
            "recommended_actions": [str(a).strip() for a in data.get("recommended_actions", []) if a],
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("Predictor: could not parse LLM JSON output")
        return {
            "risk_level": "unknown",
            "confidence": 0.0,
            "timeline_urgency": "",
            "risk_factors": [],
            "opportunities": [],
            "recommended_actions": [],
        }
