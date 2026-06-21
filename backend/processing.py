"""Thin wrapper — enqueues document processing to the Celery task queue."""

from tasks import process_document, run_analysis  # noqa: F401 — registers both tasks


def trigger_processing(doc_id: str) -> None:
    """Enqueue phase 1 (parse + index). Phase 2 (LLM analysis) is chained automatically."""
    process_document.delay(doc_id)
