"""Generate a structured document summary using the configured LLM."""

import json
import logging
import os
import re

from llm.client import generate_json

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

    try:
        raw = generate_json(prompt, timeout=120)
        return _parse(raw)
    except Exception:
        logger.exception("Summarization LLM call failed")
        return {"headline": "", "summary_text": "", "key_points": []}


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
