"""Celery worker entry point.

Start the worker with:
    celery -A celery_worker worker --loglevel=info

For concurrent processing of heavy OCR jobs use:
    celery -A celery_worker worker --loglevel=info --concurrency=2

The call to create_app() below configures the Celery singleton (via
init_celery) so the 'celery' name exported here is fully ready.
"""

from app import create_app
from celery_app import celery  # re-exported for `celery -A celery_worker`

_flask_app = create_app()

# Importing tasks registers them with the now-configured celery instance.
import tasks as _tasks  # noqa: F401, E402

__all__ = ["celery"]
