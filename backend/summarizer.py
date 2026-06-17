"""Generate a structured document summary using the configured LLM."""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_CHARS = 14_000

_PROMPT = """\
You are a document analyst. Read the document excerpt below and produce a structured summary.
Return ONLY a valid JSON object matching this exact schema — no markdown, no prose:
{{
  "headline": "<one sentence describing what this document is and its main purpose>",
  "summary_text": "<2-3 sentence paragraph summarizing the document content, purpose, and key facts>",
  "key_points": [
    "<concise bullet point 1>",
    "<concise bullet point 2>",
    "<concise bullet point 3>"
  ]
}}

Rules:
- headline: max 120 characters, factual, no filler words
- summary_text: 2-3 sentences, covers what the doc is, who it involves, and what it's for
- key_points: 3-6 bullet points, each under 100 characters, most important facts only

Document excerpt:
---
{text}
---

JSON:"""


def summarize_document(text: str) -> dict:
    """Return dict with 'headline', 'summary_text', 'key_points' (list[str])."""
    prompt = _PROMPT.format(text=text[:MAX_CHARS])

    provider = os.getenv("LLM_PROVIDER", "ollama")
    try:
        raw = _call_gemini(prompt) if provider == "gemini" else _call_ollama(prompt)
        return _parse(raw)
    except Exception:
        logger.exception("Summarization LLM call failed")
        return {"headline": "", "summary_text": "", "key_points": []}


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
            "headline": str(data.get("headline", "")).strip(),
            "summary_text": str(data.get("summary_text", "")).strip(),
            "key_points": [
                str(p).strip()
                for p in data.get("key_points", [])
                if str(p).strip()
            ],
        }
    except (json.JSONDecodeError, TypeError):
        logger.warning("Summarizer: could not parse LLM JSON output")
        return {"headline": "", "summary_text": "", "key_points": []}
