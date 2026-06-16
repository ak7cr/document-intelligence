"""Background document processing — runs in a daemon thread per upload."""

import logging
import threading

from flask import current_app

from models import Document, DocumentText, db
from processors import dispatch
from storage.minio_client import get_client

logger = logging.getLogger(__name__)


def _do_process(doc_id: str) -> None:
    doc = Document.query.get(doc_id)
    if not doc:
        logger.warning("process: document %s not found", doc_id)
        return

    doc.status = "processing"
    db.session.commit()

    try:
        # Stream file from MinIO
        client = get_client()
        response = client.get_object(doc.bucket, doc.object_key)
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()

        result = dispatch(doc.filetype, data)

        # Upsert extracted text
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
            "Document %s processed: %d words via %s",
            doc_id,
            result.word_count,
            result.method,
        )

    except Exception:
        logger.exception("Processing failed for document %s", doc_id)
        doc.status = "failed"
        db.session.commit()


def trigger_processing(doc_id: str) -> None:
    """Start processing in a daemon thread with a fresh app context."""
    app = current_app._get_current_object()

    def run() -> None:
        with app.app_context():
            _do_process(doc_id)

    threading.Thread(target=run, daemon=True).start()
