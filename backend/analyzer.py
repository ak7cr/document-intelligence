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
You are a document analyst specializing in procurement and tender documents.
Analyze the document excerpt below and return ALL of the following in ONE JSON object.
Return ONLY valid JSON — no markdown fences, no prose, no explanation.

{{
  "doc_type": "<Tender Notice | RFP | Purchase Order | Contract | Invoice | Other>",
  "entities": [
    {{"type": "<date|deadline|party|amount|reference>", "label": "<short label>", "value": "<extracted value>"}}
  ],
  "headline": "<one sentence, max 120 chars: what this document is and its main purpose>",
  "summary_text": "<2-3 sentence paragraph: what the doc is, who it involves, what it is for>",
  "key_points": ["<concise fact 1, under 100 chars>", "<fact 2>", "<fact 3>"],
  "risk_level": "<low|medium|high>",
  "confidence": 0.0,
  "timeline_urgency": "<brief deadline urgency description, or No deadline found>",
  "risk_factors": ["<specific risk 1>", "<specific risk 2>"],
  "opportunities": ["<opportunity 1>", "<opportunity 2>"],
  "recommended_actions": ["<concrete action 1>", "<concrete action 2>"]
}}

Entity types:
- date: issue date, validity date, opening date, any named dates
- deadline: submission deadline, bid closing date, response due date
- party: organizations, companies, agencies, signatories, bidders
- amount: monetary values, bid amounts, contract value, quantities with units
- reference: document IDs, tender IDs, procurement IDs, order numbers

Risk guidelines:
- low: clear terms, reasonable deadlines, known parties, standard amounts
- medium: ambiguous terms, tight timeline, unfamiliar party, moderate value
- high: deadline under 7 days, very large amounts, unusual clauses, critical info missing
- confidence: 0.0-1.0, how certain you are given available information
- key_points: 3-6 bullets, each under 100 characters
- risk_factors: 2-5 specific concerns
- opportunities: 2-4 positive indicators or advantages
- recommended_actions: 2-4 concrete next steps

Document excerpt:
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


def _call_ollama(prompt: str) -> str:
    import requests
    resp = requests.post(
        f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
        json={"model": os.getenv("OLLAMA_MODEL", "llama3.2"), "prompt": prompt, "stream": False},
        timeout=180,
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
    except (json.JSONDecodeError, TypeError):
        logger.warning("analyze_document: could not parse LLM JSON output")
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
