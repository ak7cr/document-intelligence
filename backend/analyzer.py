"""Single-call document analysis: entities + summary + risk prediction in one LLM call.

Used by the task pipeline to reduce per-document API calls from 3 → 1.
The individual extractor/summarizer/predictor modules remain available for
on-demand re-runs via the API endpoints.
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_CHARS = 14_000

_PROMPT = """\
You are a document analyst. The document below may be in Hindi, English, or mixed script.
OCR errors may be present — use context to correct them.
Respond in whichever language best captures the content — Hindi, English, or mixed is fine.
Keep proper nouns (org names, person names, places) exactly as they appear in the source.

Fill in this JSON using the document content:

JSON format:
{{"doc_type":"Tender Notice","entities":[{{"type":"party","label":"Issuing Authority","value":"<org name as in doc>"}},{{"type":"deadline","label":"Submission Deadline","value":"<date as in doc>"}},{{"type":"amount","label":"Contract Value","value":"<amount as in doc>"}}],"headline":"<one English sentence describing the document>","summary_text":"<2-3 English sentences: what, who, purpose>","key_points":["<fact 1>","<fact 2>","<fact 3>"],"risk_level":"low","confidence":0.8,"timeline_urgency":"<English description>","risk_factors":["<risk 1>"],"opportunities":["<opportunity 1>"],"recommended_actions":["<action 1>"]}}

Entity types: date, deadline, party, amount, reference
Risk levels: low, medium, high

Document:
---
{text}
---

JSON:"""


def analyze_document(text: str) -> dict:
    """One LLM call → entities + summary + prediction for a document.

    Returns a dict with keys from all three analysis types. Falls back to
    empty/default values for any section that fails to parse.
    """
    prompt = _PROMPT.format(text=text[:MAX_CHARS])
    provider = os.getenv("LLM_PROVIDER", "ollama")

    try:
        raw = _call_gemini(prompt) if provider == "gemini" else _call_ollama(prompt)
        return _parse(raw)
    except Exception:
        logger.exception("Combined document analysis LLM call failed")
        return _empty()


def _call_gemini(prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=prompt,
    )
    return response.text.strip()


_OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type":            {"type": "string"},
        "entities":            {"type": "array", "items": {"type": "object", "properties": {"type": {"type": "string"}, "label": {"type": "string"}, "value": {"type": "string"}}, "required": ["type", "label", "value"]}},
        "headline":            {"type": "string"},
        "summary_text":        {"type": "string"},
        "key_points":          {"type": "array", "items": {"type": "string"}},
        "risk_level":          {"type": "string", "enum": ["low", "medium", "high", "unknown"]},
        "confidence":          {"type": "number"},
        "timeline_urgency":    {"type": "string"},
        "risk_factors":        {"type": "array", "items": {"type": "string"}},
        "opportunities":       {"type": "array", "items": {"type": "string"}},
        "recommended_actions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["doc_type", "entities", "headline", "summary_text", "key_points",
                 "risk_level", "confidence", "timeline_urgency", "risk_factors",
                 "opportunities", "recommended_actions"],
}


def _call_ollama(prompt: str) -> str:
    import requests
    resp = requests.post(
        f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
        json={
            "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
            "prompt": prompt,
            "stream": False,
            "format": _OLLAMA_SCHEMA,  # constrained decoding — model CANNOT deviate from schema
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def _repair(text: str) -> str:
    """Fix common LLM JSON mistakes before parsing."""
    # Python-style literals
    text = re.sub(r'\bNone\b', 'null', text)
    text = re.sub(r'\bTrue\b', 'true', text)
    text = re.sub(r'\bFalse\b', 'false', text)
    # Trailing commas before ] or }
    text = re.sub(r',\s*([\]\}])', r'\1', text)
    # Smart quotes
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    return text


def _parse(raw: str) -> dict:
    text = raw.strip()

    # Strip markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()

    # Try candidates: full text, repaired text, first {...} block, repaired block
    candidates = [text, _repair(text)]
    block = re.search(r"\{[\s\S]*\}", text)
    if block:
        candidates += [block.group(0), _repair(block.group(0))]

    data = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            break
        except (json.JSONDecodeError, TypeError):
            continue

    if data is None:
        logger.warning(
            "analyze_document: could not parse LLM JSON output. Raw (first 400 chars): %s",
            raw[:400].replace('\n', ' '),
        )
        return _empty()

    risk_level = str(data.get("risk_level", "unknown")).lower().strip()
    if risk_level not in ("low", "medium", "high"):
        risk_level = "unknown"

    return {
        # entities section
        "doc_type": str(data.get("doc_type", "")).strip(),
        "entities": [
            {
                "type": str(e.get("type", "")).lower().strip(),
                "label": str(e.get("label", "")).strip(),
                "value": str(e.get("value", "")).strip(),
            }
            for e in data.get("entities", [])
            if e.get("label") and e.get("value")
        ],
        # summary section
        "headline": str(data.get("headline", "")).strip(),
        "summary_text": str(data.get("summary_text", "")).strip(),
        "key_points": [str(p).strip() for p in data.get("key_points", []) if str(p).strip()],
        # prediction section
        "risk_level": risk_level,
        "confidence": min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
        "timeline_urgency": str(data.get("timeline_urgency", "")).strip(),
        "risk_factors": [str(r).strip() for r in data.get("risk_factors", []) if r],
        "opportunities": [str(o).strip() for o in data.get("opportunities", []) if o],
        "recommended_actions": [str(a).strip() for a in data.get("recommended_actions", []) if a],
    }


def _empty() -> dict:
    return {
        "doc_type": "",
        "entities": [],
        "headline": "",
        "summary_text": "",
        "key_points": [],
        "risk_level": "unknown",
        "confidence": 0.0,
        "timeline_urgency": "",
        "risk_factors": [],
        "opportunities": [],
        "recommended_actions": [],
    }
