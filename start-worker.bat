@echo off
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
celery -A celery_worker worker --loglevel=info
