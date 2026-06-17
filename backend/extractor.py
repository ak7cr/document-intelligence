"""Extract structured entities from document text using the configured LLM."""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_CHARS = 12_000

_PROMPT = """\
You are a document analyst. Extract structured information from the document excerpt below.
Return ONLY a valid JSON object matching this exact schema — no markdown, no prose:
{{
  "doc_type": "<document type, e.g. Tender Notice, RFP, Purchase Order, Contract, Invoice>",
  "entities": [
    {{"type": "<date|deadline|party|amount|reference>", "label": "<short descriptive label>", "value": "<extracted value>"}}
  ]
}}

Entity types to look for:
- date: issue date, validity date, opening date, any mentioned dates
- deadline: submission deadline, bid closing date, response due date
- party: organizations, companies, agencies, signatories, bidders
- amount: monetary values, bid amounts, estimated contract value, quantities
- reference: document reference numbers, tender IDs, procurement IDs, order numbers

Document excerpt:
---
{text}
---

JSON:"""


def extract_entities(text: str) -> dict:
    """Return dict with 'doc_type' (str) and 'entities' (list[dict])."""
    prompt = _PROMPT.format(text=text[:MAX_CHARS])

    provider = os.getenv("LLM_PROVIDER", "ollama")
    try:
        raw = _call_gemini(prompt) if provider == "gemini" else _call_ollama(prompt)
        return _parse(raw)
    except Exception:
        logger.exception("Entity extraction LLM call failed")
        return {"doc_type": "", "entities": []}


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
        }
    except (json.JSONDecodeError, TypeError):
        logger.warning("Entity extraction: could not parse LLM JSON output")
        return {"doc_type": "", "entities": []}
