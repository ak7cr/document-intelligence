"""RAG pipeline: retrieve relevant chunks then generate a grounded answer.

Verification layer: structured DB facts (entities, summaries, predictions) are
injected before chunk excerpts so the LLM prefers pre-extracted verified data
over noisy raw text for factual questions (dates, amounts, parties, risk).
"""

import os

from llm.client import generate
from vector.store import search_chunks

TOP_K = int(os.getenv("RAG_TOP_K", "5"))

_SYSTEM_PROMPT = (
    "You are a tender document analyst. "
    "Answer questions using BOTH the verified structured data AND the document excerpts below. "
    "For factual answers (dates, deadlines, amounts, party names, risk levels, certifications) "
    "prefer the Verified Structured Data section — this was pre-extracted and is reliable. "
    "Use document excerpts for detailed narrative context. "
    "When referencing information, mention the source document name. "
    'If the answer cannot be found in either section, say "I could not find this information '
    'in the uploaded documents." and stop.'
)


def _fetch_verified_facts(session_id: str) -> str:
    """Query DB for pre-extracted structured data and return as a formatted block."""
    from models import Document, DocumentEntity, DocumentPrediction, DocumentSummary

    docs = Document.query.filter_by(session_id=session_id, status="ready").all()
    if not docs:
        return ""

    doc_map = {d.id: d.filename for d in docs}
    doc_ids = list(doc_map.keys())

    parts: list[str] = []

    # ── Summaries ─────────────────────────────────────────────────────────────
    summaries = DocumentSummary.query.filter(
        DocumentSummary.document_id.in_(doc_ids)
    ).all()
    if summaries:
        lines = ["[DOCUMENT SUMMARIES]"]
        for s in summaries:
            fname = doc_map.get(s.document_id, "unknown")
            lines.append(f"  {fname}: {s.headline}")
            if s.key_points:
                for kp in s.key_points[:4]:
                    lines.append(f"    - {kp}")
        parts.append("\n".join(lines))

    # ── Entities — grouped by type ─────────────────────────────────────────
    entities = (
        DocumentEntity.query
        .filter(
            DocumentEntity.document_id.in_(doc_ids),
            DocumentEntity.entity_type != "doc_type",
        )
        .order_by(DocumentEntity.entity_type, DocumentEntity.document_id)
        .all()
    )
    if entities:
        by_type: dict[str, list] = {}
        for e in entities:
            by_type.setdefault(e.entity_type, []).append(e)

        lines = ["[EXTRACTED ENTITIES]"]
        for etype, ents in by_type.items():
            lines.append(f"  {etype.upper()}:")
            for e in ents[:12]:
                fname = doc_map.get(e.document_id, "?")
                lines.append(f"    - {e.label}: {e.value}  [{fname}]")
        parts.append("\n".join(lines))

    # ── Predictions ────────────────────────────────────────────────────────
    preds = DocumentPrediction.query.filter(
        DocumentPrediction.document_id.in_(doc_ids)
    ).all()
    if preds:
        lines = ["[RISK ASSESSMENTS]"]
        for p in preds:
            fname = doc_map.get(p.document_id, "?")
            lines.append(
                f"  {fname}: risk={p.risk_level}, confidence={p.confidence:.0%}, "
                f"urgency={p.timeline_urgency}"
            )
            if p.risk_factors:
                lines.append("    Risk factors: " + "; ".join(p.risk_factors[:3]))
            if p.recommended_actions:
                lines.append("    Recommended: " + "; ".join(p.recommended_actions[:2]))
        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def _compute_confidence(chunks: list[dict], has_structured: bool) -> str:
    best = max((c["score"] for c in chunks), default=0.0)
    if best >= 0.75 and has_structured:
        return "high"
    if best >= 0.5 or has_structured:
        return "medium"
    return "low"


def _build_sources(chunks: list[dict]) -> list[dict]:
    from models import Document

    doc_ids = list({c["document_id"] for c in chunks if c.get("document_id")})
    doc_meta: dict[str, dict] = {}
    for doc in Document.query.filter(Document.id.in_(doc_ids)).all():
        doc_meta[doc.id] = {
            "chunk_count": len(doc.chunks),
            "page_count": doc.text.page_count if doc.text else None,
        }

    sources = []
    for c in chunks:
        doc_id = c.get("document_id") or ""
        meta = doc_meta.get(doc_id, {})
        chunk_count = meta.get("chunk_count") or 0
        page_count = meta.get("page_count")

        if page_count and chunk_count > 0:
            progress = c["chunk_index"] / max(chunk_count - 1, 1)
            page_number = round(progress * (page_count - 1)) + 1
        else:
            page_number = None

        snippet = c["text"][:350] + ("..." if len(c["text"]) > 350 else "")
        sources.append({
            "document_id": doc_id,
            "filename": c["filename"],
            "chunk_index": c["chunk_index"],
            "page_number": page_number,
            "text": snippet,
            "score": c["score"],
        })

    return sources


def answer_question(session_id: str, question: str) -> dict:
    """Retrieve structured facts + top-K chunks, build a grounded prompt, return answer."""

    verified_facts = _fetch_verified_facts(session_id)
    chunks = search_chunks(question, session_id=session_id, top_k=TOP_K)

    if not chunks and not verified_facts:
        return {
            "answer": (
                "No indexed documents found for this session. "
                "Upload documents and wait for them to finish processing (status = ready)."
            ),
            "sources": [],
            "confidence": "low",
        }

    prompt_parts = [_SYSTEM_PROMPT]

    if verified_facts:
        prompt_parts.append(
            "=== VERIFIED STRUCTURED DATA ===\n"
            "(Pre-extracted facts — prefer these for factual questions)\n\n"
            + verified_facts
        )

    if chunks:
        context_parts = [
            f"[Excerpt {i + 1}: {c['filename']}, chunk {c['chunk_index']}]\n{c['text']}"
            for i, c in enumerate(chunks)
        ]
        prompt_parts.append(
            "=== DOCUMENT EXCERPTS ===\n\n" + "\n\n---\n\n".join(context_parts)
        )

    prompt_parts.append(f"Question: {question}\n\nAnswer:")
    prompt = "\n\n".join(prompt_parts)

    answer = generate(prompt)
    sources = _build_sources(chunks)
    confidence = _compute_confidence(chunks, bool(verified_facts))

    return {"answer": answer, "sources": sources, "confidence": confidence}
