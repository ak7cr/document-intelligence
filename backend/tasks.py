"""Celery tasks for document processing."""

import logging

from celery_app import celery
from models import Document, DocumentText, db
from processors import dispatch
from storage.minio_client import get_client

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

        # ── Persist ──────────────────────────────────────────────────────
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

        doc.status = "ready"
        db.session.commit()
        logger.info(
            "Document %s ready — %d words, method=%s, confidence=%s",
            doc_id,
            result.word_count,
            result.method,
            f"{result.confidence:.2f}" if result.confidence else "n/a",
        )

    except Exception as exc:
        logger.exception("Processing failed for document %s", doc_id)
        # Mark as failed; retry will attempt again up to max_retries
        try:
            doc.status = "failed"
            db.session.commit()
        except Exception:
            db.session.rollback()
        raise task.retry(exc=exc)
