"""Celery tasks for document processing."""

import logging

from analyzer import analyze_document
from celery_app import celery
from chunker import chunk_text
from models import Document, DocumentChunk, DocumentEntity, DocumentPrediction, DocumentSummary, DocumentText, db
from processors import dispatch
from qdrant_client.models import PointStruct
from storage.minio_client import get_client
from vector import delete_doc_vectors, embed_passages, upsert_chunks

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="process_document", max_retries=3, default_retry_delay=15)
def process_document(self, doc_id: str) -> None:  # type: ignore[misc]
    """Download a document from MinIO, extract text (or OCR), persist results."""
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
        # ── Download from MinIO ───────────────────────────────────────────
        client = get_client()
        response = client.get_object(doc.bucket, doc.object_key)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()

        # ── Extract text / OCR ───────────────────────────────────────────
        result = dispatch(doc.filetype, data)

        # ── Persist text ──────────────────────────────────────────────────
        existing = DocumentText.query.filter_by(document_id=doc_id).first()
        if existing:
            existing.raw_text = result.text
            existing.word_count = result.word_count
            existing.page_count = result.page_count
            existing.method = result.method
            existing.ocr_confidence = result.confidence
        else:
            db.session.add(
                DocumentText(
                    document_id=doc_id,
                    raw_text=result.text,
                    word_count=result.word_count,
                    page_count=result.page_count,
                    method=result.method,
                    ocr_confidence=result.confidence,
                )
            )

        # ── Chunk text ───────────────────────────────────────────────────
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
        db.session.flush()  # assign UUIDs before embedding

        # ── Embed and upsert to Qdrant ────────────────────────────────────
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

        # ── Combined LLM analysis (1 call: entities + summary + prediction) ──
        try:
            analysis = analyze_document(result.text)

            # entities
            DocumentEntity.query.filter_by(document_id=doc_id).delete()
            if analysis.get("doc_type"):
                db.session.add(DocumentEntity(
                    document_id=doc_id,
                    entity_type="doc_type",
                    label="Document Type",
                    value=analysis["doc_type"],
                ))
            for ent in analysis.get("entities", []):
                if ent.get("type") and ent.get("label") and ent.get("value"):
                    db.session.add(DocumentEntity(
                        document_id=doc_id,
                        entity_type=ent["type"],
                        label=ent["label"],
                        value=ent["value"],
                    ))
            logger.info(
                "Extracted %d entities for document %s",
                len(analysis.get("entities", [])) + bool(analysis.get("doc_type")),
                doc_id,
            )

            # summary
            existing_summary = DocumentSummary.query.filter_by(document_id=doc_id).first()
            if existing_summary:
                existing_summary.headline = analysis["headline"]
                existing_summary.summary_text = analysis["summary_text"]
                existing_summary.key_points = analysis["key_points"]
            else:
                db.session.add(DocumentSummary(
                    document_id=doc_id,
                    headline=analysis["headline"],
                    summary_text=analysis["summary_text"],
                    key_points=analysis["key_points"],
                ))
            logger.info("Summary generated for document %s", doc_id)

            # prediction
            pred_fields = {
                "risk_level": analysis["risk_level"],
                "confidence": analysis["confidence"],
                "timeline_urgency": analysis["timeline_urgency"],
                "risk_factors": analysis["risk_factors"],
                "opportunities": analysis["opportunities"],
                "recommended_actions": analysis["recommended_actions"],
            }
            existing_pred = DocumentPrediction.query.filter_by(document_id=doc_id).first()
            if existing_pred:
                for k, v in pred_fields.items():
                    setattr(existing_pred, k, v)
            else:
                db.session.add(DocumentPrediction(document_id=doc_id, **pred_fields))
            logger.info("Risk prediction for document %s: %s", doc_id, analysis["risk_level"])

        except Exception:
            logger.exception("Combined analysis failed for document %s — skipping", doc_id)

        doc.status = "ready"
        db.session.commit()
        logger.info(
            "Document %s ready — %d words, %d chunks, method=%s, confidence=%s",
            doc_id,
            result.word_count,
            len(db_chunks),
            result.method,
            f"{result.confidence:.2f}" if result.confidence else "n/a",
        )

    except Exception as exc:
        logger.exception("Processing failed for document %s", doc_id)
        try:
            doc.status = "failed"
            db.session.commit()
        except Exception:
            db.session.rollback()
        raise task.retry(exc=exc)
