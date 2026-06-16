"""Thin wrapper — enqueues document processing to the Celery task queue."""

from tasks import process_document


def trigger_processing(doc_id: str) -> None:
    """Send a process_document task to the Celery worker via Redis."""
    process_document.delay(doc_id)
