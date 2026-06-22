#!/bin/bash
cd "$(cd "$(dirname "$0")" && pwd)/backend"
source venv/bin/activate
celery -A celery_worker worker --loglevel=info
