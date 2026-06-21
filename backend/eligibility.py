"""Eligibility/compliance checker — compares a company profile against tender criteria."""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 12_000

_PROMPT = """\
You are a procurement compliance analyst.
The tender document may be in Hindi, English, or mixed script — always respond in ENGLISH.
Keep proper nouns (organization names, place names) as they appear in the source document.
Assess whether the company below is eligible to bid for the given tender.

Company Profile:
- Name: {company_name}
- Annual Turnover: {annual_turnover}
- Years in Business: {years_in_business}
- Certifications Held: {certifications}
- Similar Projects Completed: {similar_projects}
- Employee Count: {employee_count}
- Additional Info: {extra_details}

Tender Document:
---
{tender_text}
---

Extract every eligibility criterion from the tender and compare it against the company profile.
Return ONLY a valid JSON object — no markdown, no prose:
{{
  "score": <integer 0-100, percentage of key criteria met>,
  "met": [
    "<criterion satisfied — brief evidence from profile>"
  ],
  "missing": [
    "<criterion not met or uncertain — include specific gap>"
  ],
  "documents_required": [
    {{"name": "<document the tender requires>", "status": "available|required"}}
  ],
  "recommendation": "<2-3 sentences: should the company bid, and what is the single biggest gap or strength?>"
}}

Scoring:
- 90-100: fully eligible, all major criteria met
- 70-89: mostly eligible, minor gaps that may be waived
- 50-69: partially eligible, significant gaps but bidding may still be worthwhile
- 0-49: likely ineligible due to disqualifying gaps

Documents status:
- "available": company almost certainly has this (PAN, GST, financial statements, audit reports)
- "required": must be specifically arranged (project completion certificates, unlisted certifications, bank guarantees)

JSON:"""


def check_eligibility(tender_text: str, profile: dict) -> dict:
    """Compare company profile against tender text. Returns eligibility result."""
    certs = profile.get("certifications") or []
    certs_str = ", ".join(certs) if certs else "None specified"

    yib = profile.get("years_in_business")
    sp = profile.get("similar_projects")

    prompt = _PROMPT.format(
        company_name=profile.get("company_name") or "Not specified",
        annual_turnover=profile.get("annual_turnover") or "Not specified",
        years_in_business=f"{yib} years" if yib is not None else "Not specified",
        certifications=certs_str,
        similar_projects=str(sp) if sp is not None else "Not specified",
        employee_count=profile.get("employee_count") or "Not specified",
        extra_details=profile.get("extra_details") or "None",
        tender_text=tender_text[:MAX_TEXT_CHARS],
    )

    provider = os.getenv("LLM_PROVIDER", "ollama")
    try:
        raw = _call_gemini(prompt) if provider == "gemini" else _call_ollama(prompt)
        return _parse(raw)
    except Exception:
        logger.exception("Eligibility check LLM call failed")
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
        logger.warning("eligibility: could not parse LLM JSON output")
        return _empty()

    score = max(0, min(100, int(data.get("score", 0))))

    docs = []
    for d in data.get("documents_required", []):
        status = str(d.get("status", "required")).lower()
        if status not in ("available", "required"):
            status = "required"
        name = str(d.get("name", "")).strip()
        if name:
            docs.append({"name": name, "status": status})

    return {
        "score": score,
        "met": [str(m).strip() for m in data.get("met", []) if m],
        "missing": [str(m).strip() for m in data.get("missing", []) if m],
        "documents_required": docs,
        "recommendation": str(data.get("recommendation", "")).strip(),
    }


def _empty() -> dict:
    return {
        "score": 0,
        "met": [],
        "missing": [],
        "documents_required": [],
        "recommendation": "",
    }
