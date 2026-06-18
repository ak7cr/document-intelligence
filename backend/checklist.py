import json
import logging
import os

from google import genai

logger = logging.getLogger(__name__)
_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_VALID_CATS = {"Technical", "Financial", "Legal", "Administrative"}
_VALID_STATUSES = {"required", "optional"}


def build_checklist(tender_text: str) -> dict:
    """Extract bid submission checklist items from tender text."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""Analyze this tender document and extract a comprehensive bid submission checklist.

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
        resp = client.models.generate_content(model=_MODEL, contents=prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0]
        data = json.loads(raw.strip())
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
