"""Celery tasks for document processing.

Two-phase pipeline:
  1. process_document  — download → OCR/extract → chunk → embed → index
                         Sets status="ready" so the doc is immediately searchable.
  2. run_analysis      — LLM calls: entities + summary + prediction + checklist + eligibility
                         Runs after phase 1; failures here don't affect searchability.
"""

import logging
import os

from analyzer import analyze_document
from celery_app import celery
from checklist import build_checklist
from chunker import chunk_text
from eligibility import check_eligibility
from models import (
    CompanyProfile,
    Document,
    DocumentChunk,
    DocumentChecklist,
    DocumentEntity,
    DocumentPrediction,
    DocumentSummary,
    DocumentText,
    EligibilityCheck,
    db,
)
from processors import dispatch
from qdrant_client.models import PointStruct
from storage.minio_client import get_client
from vector import delete_doc_vectors, embed_passages, upsert_chunks

logger = logging.getLogger(__name__)


def _unload_ollama() -> None:
    """Ask Ollama to evict its model from VRAM so OCR has full GPU access.
    Ollama reloads the model automatically on the next LLM call (run_analysis).
    No-op when LLM_PROVIDER != ollama or Ollama is unreachable.
    """
    import os
    if os.getenv("LLM_PROVIDER", "ollama") != "ollama":
        return
    try:
        import requests
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        requests.post(
            f"{host}/api/generate",
            json={"model": model, "keep_alive": 0},
            timeout=5,
        )
        logger.info("Ollama model unloaded from VRAM — GPU free for OCR")
    except Exception as exc:
        logger.debug("Could not unload Ollama model: %s", exc)


# ── Phase 1: parse + index ────────────────────────────────────────────────────

@celery.task(bind=True, name="process_document", max_retries=3, default_retry_delay=15)
def process_document(self, doc_id: str) -> None:  # type: ignore[misc]
    with celery.flask_app.app_context():  # type: ignore[attr-defined]
        _process(self, doc_id)


def _process(task, doc_id: str) -> None:
    doc = Document.query.get(doc_id)
    if not doc:
        logger.warning("process_document: document %s not found", doc_id)
        return

    doc.status = "processing"
    db.session.commit()

    try:
        # ── Download ──────────────────────────────────────────────────────────
        client = get_client()
        response = client.get_object(doc.bucket, doc.object_key)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()

        # ── Free GPU before OCR (only needed when OCR uses local GPU) ─────────
        from config import get_ocr_engine
        if get_ocr_engine() == "easyocr":
            _unload_ollama()
            from ocr.engine import reset_reader
            reset_reader()

        # ── Extract text / OCR ────────────────────────────────────────────────
        result = dispatch(doc.filetype, data)

        # Re-check document still exists — user may have deleted it during slow OCR
        db.session.expire(doc)
        if not Document.query.get(doc_id):
            logger.warning("Document %s was deleted during OCR — aborting task", doc_id)
            return

        # ── Persist text ──────────────────────────────────────────────────────
        existing = DocumentText.query.filter_by(document_id=doc_id).first()
        if existing:
            existing.raw_text = result.text
            existing.word_count = result.word_count
            existing.page_count = result.page_count
            existing.method = result.method
            existing.ocr_confidence = result.confidence
            existing.ocr_engine = result.ocr_engine
        else:
            db.session.add(DocumentText(
                document_id=doc_id,
                raw_text=result.text,
                word_count=result.word_count,
                page_count=result.page_count,
                method=result.method,
                ocr_confidence=result.confidence,
                ocr_engine=result.ocr_engine,
            ))

        # ── Chunk ─────────────────────────────────────────────────────────────
        raw_chunks = chunk_text(result.text)
        DocumentChunk.query.filter_by(document_id=doc_id).delete()
        db_chunks: list[DocumentChunk] = []
        for ch in raw_chunks:
            obj = DocumentChunk(
                document_id=doc_id,
                chunk_index=ch.index,
                text=ch.text,
                token_count=ch.token_count,
            )
            db.session.add(obj)
            db_chunks.append(obj)
        db.session.flush()

        # ── Embed + index to Qdrant ───────────────────────────────────────────
        if db_chunks:
            vecs = embed_passages([c.text for c in db_chunks])
            delete_doc_vectors(doc_id)
            upsert_chunks([
                PointStruct(
                    id=c.id,
                    vector=vecs[i],
                    payload={
                        "document_id": doc_id,
                        "chunk_id": c.id,
                        "chunk_index": c.chunk_index,
                        "session_id": doc.session_id,
                        "filename": doc.filename,
                        "text": c.text,
                    },
                )
                for i, c in enumerate(db_chunks)
            ])

        # ── Mark ready — doc is now searchable ────────────────────────────────
        doc.status = "ready"
        db.session.commit()
        logger.info(
            "Document %s ready — %d words, %d chunks, method=%s, ocr_confidence=%s",
            doc_id, result.word_count, len(db_chunks), result.method,
            f"{result.confidence:.2f}" if result.confidence else "n/a",
        )

        # ── Chain to LLM analysis (phase 2) ───────────────────────────────────
        run_analysis.delay(doc_id)

    except Exception as exc:
        logger.exception("Processing failed for document %s", doc_id)
        try:
            doc.status = "failed"
            db.session.commit()
        except Exception:
            db.session.rollback()
        raise task.retry(exc=exc)


# ── Phase 2: LLM analysis ─────────────────────────────────────────────────────

@celery.task(bind=True, name="run_analysis", max_retries=2, default_retry_delay=30)
def run_analysis(self, doc_id: str) -> None:  # type: ignore[misc]
    with celery.flask_app.app_context():  # type: ignore[attr-defined]
        _analyse(self, doc_id)


def _analyse(task, doc_id: str) -> None:
    doc = Document.query.get(doc_id)
    if not doc:
        logger.warning("run_analysis: document %s not found", doc_id)
        return

    doc_text = DocumentText.query.filter_by(document_id=doc_id).first()
    if not doc_text:
        logger.warning("run_analysis: no text for document %s", doc_id)
        return

    text = doc_text.raw_text

    # ── Entities + summary + prediction (1 LLM call) ──────────────────────────
    try:
        analysis = analyze_document(text)

        DocumentEntity.query.filter_by(document_id=doc_id).delete()
        if analysis.get("doc_type"):
            db.session.add(DocumentEntity(
                document_id=doc_id, entity_type="doc_type",
                label="Document Type", value=analysis["doc_type"],
            ))
        for ent in analysis.get("entities", []):
            if ent.get("type") and ent.get("label") and ent.get("value"):
                db.session.add(DocumentEntity(
                    document_id=doc_id, entity_type=ent["type"],
                    label=ent["label"], value=ent["value"],
                ))

        existing_s = DocumentSummary.query.filter_by(document_id=doc_id).first()
        if existing_s:
            existing_s.headline = analysis["headline"]
            existing_s.summary_text = analysis["summary_text"]
            existing_s.key_points = analysis["key_points"]
        else:
            db.session.add(DocumentSummary(
                document_id=doc_id,
                headline=analysis["headline"],
                summary_text=analysis["summary_text"],
                key_points=analysis["key_points"],
            ))

        pred_fields = {
            "risk_level": analysis["risk_level"],
            "confidence": analysis["confidence"],
            "timeline_urgency": analysis["timeline_urgency"],
            "risk_factors": analysis["risk_factors"],
            "opportunities": analysis["opportunities"],
            "recommended_actions": analysis["recommended_actions"],
        }
        existing_p = DocumentPrediction.query.filter_by(document_id=doc_id).first()
        if existing_p:
            for k, v in pred_fields.items():
                setattr(existing_p, k, v)
        else:
            db.session.add(DocumentPrediction(document_id=doc_id, **pred_fields))

        db.session.commit()
        logger.info(
            "Analysis done for document %s — %d entities, risk=%s",
            doc_id, len(analysis.get("entities", [])), analysis.get("risk_level"),
        )
    except Exception:
        db.session.rollback()
        logger.exception("Analysis (entities/summary/prediction) failed for document %s", doc_id)

    # ── Checklist ─────────────────────────────────────────────────────────────
    try:
        cl_result = build_checklist(text)
        existing_cl = DocumentChecklist.query.filter_by(document_id=doc_id).first()
        if existing_cl:
            existing_cl.items = cl_result["items"]
        else:
            db.session.add(DocumentChecklist(document_id=doc_id, items=cl_result["items"]))
        db.session.commit()
        logger.info("Checklist done for document %s (%d items)", doc_id, len(cl_result["items"]))
    except Exception:
        db.session.rollback()
        logger.exception("Checklist failed for document %s", doc_id)

    # ── Eligibility (only if profile exists) ──────────────────────────────────
    try:
        profile = CompanyProfile.query.filter_by(session_id=doc.session_id).first()
        if profile:
            elig_result = check_eligibility(text, profile.to_dict())
            existing_e = EligibilityCheck.query.filter_by(document_id=doc_id).first()
            if existing_e:
                existing_e.profile_id = profile.id
                existing_e.score = elig_result["score"]
                existing_e.met = elig_result["met"]
                existing_e.missing = elig_result["missing"]
                existing_e.documents_required = elig_result["documents_required"]
                existing_e.recommendation = elig_result["recommendation"]
            else:
                db.session.add(EligibilityCheck(
                    document_id=doc_id, profile_id=profile.id, **elig_result
                ))
            db.session.commit()
            logger.info("Eligibility done for document %s: score=%d", doc_id, elig_result["score"])
    except Exception:
        db.session.rollback()
        logger.exception("Eligibility failed for document %s", doc_id)
