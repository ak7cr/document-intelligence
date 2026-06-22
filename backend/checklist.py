import json
import logging
import os
import re

logger = logging.getLogger(__name__)

_CL_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "category": {"type": "string"},
            "status": {"type": "string"}, "notes": {"type": "string"},
        }, "required": ["name", "category", "status", "notes"]}},
    },
    "required": ["items"],
}


def _call_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "gemini":
        from llm.client import generate
        return generate(prompt)
    import requests
    resp = requests.post(
        f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/generate",
        json={"model": os.getenv("OLLAMA_MODEL", "llama3.2"), "prompt": prompt,
              "stream": False, "format": _CL_SCHEMA},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


_VALID_CATS = {"Technical", "Financial", "Legal", "Administrative"}
_VALID_STATUSES = {"required", "optional"}


def build_checklist(tender_text: str) -> dict:
    """Extract bid submission checklist items from tender text."""
    prompt = f"""Analyze this tender document and extract a comprehensive bid submission checklist.
The document may be in Hindi, English, or mixed script. Respond in ENGLISH.
Keep organization names and place names as they appear in the source document.

For each item a bidder must prepare or submit, identify:
- name: Short descriptive name of the item
- category: Exactly one of: Technical, Financial, Legal, Administrative
- status: "required" (mandatory) or "optional" (advantageous but not mandatory)
- notes: One sentence explaining what exactly is needed

Return ONLY a valid JSON object, no explanation:
{{
  "items": [
    {{"name": "Technical Proposal", "category": "Technical", "status": "required", "notes": "Detailed methodology, work plan, and technical approach for the project"}},
    {{"name": "Bank Guarantee / EMD", "category": "Financial", "status": "required", "notes": "Earnest money deposit as per tender amount"}},
    {{"name": "Certificate of Incorporation", "category": "Legal", "status": "required", "notes": "Proof of legal entity registration"}},
    {{"name": "Power of Attorney", "category": "Administrative", "status": "required", "notes": "Authorisation letter for signatory"}}
  ]
}}

TENDER DOCUMENT:
{tender_text[:7000]}
"""

    try:
        raw = _call_llm(prompt)
        text = raw.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        data = None
        for candidate in [text, (re.search(r"\{[\s\S]*\}", text) or type("", (), {"group": lambda *_: None})()).group(0)]:
            if not candidate:
                continue
            try:
                data = json.loads(candidate)
                break
            except (json.JSONDecodeError, TypeError):
                continue
        if data is None:
            logger.warning("build_checklist: LLM did not return valid JSON (model may not support multilingual JSON output)")
            return {"items": []}
        items = data.get("items", [])
        valid = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            cat = item.get("category", "Administrative")
            if cat not in _VALID_CATS:
                cat = "Administrative"
            status = item.get("status", "required")
            if status not in _VALID_STATUSES:
                status = "required"
            valid.append({
                "name": name,
                "category": cat,
                "status": status,
                "notes": str(item.get("notes", "")).strip(),
            })
        return {"items": valid}
    except Exception as exc:
        logger.error("checklist.build_checklist failed: %s", exc)
        return {"items": []}
