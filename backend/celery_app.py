"""Celery singleton.

The instance is created here and configured later by init_celery(flask_app),
which is called inside create_app().  Tasks import `celery` from this module
and access the Flask app via `celery.flask_app` (set by init_celery).
"""

from celery import Celery

celery = Celery("document_intelligence")


def init_celery(flask_app) -> None:  # type: ignore[no-untyped-def]
    """Bind the Celery singleton to a Flask app.

    Called once during create_app() so every task can push a fresh app
    context via ``with celery.flask_app.app_context()``.
    """
    celery.flask_app = flask_app  # type: ignore[attr-defined]

    redis_url = flask_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    celery.conf.update(
        broker_url=redis_url,
        result_backend=redis_url,
        task_ignore_result=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Prevent worker from prefetching more tasks than it can handle
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )
