@echo off
setlocal
set ROOT=%~dp0

echo ========================================
echo   Document Intelligence - First-time Setup
echo ========================================
echo.

echo Starting infrastructure (PostgreSQL, Redis, MinIO, Qdrant)...
docker compose up -d
echo.

echo Setting up Python virtual environment...
cd /d "%ROOT%backend"
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        python3 -m venv venv
    )
)
call venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install -r requirements.txt
call venv\Scripts\deactivate.bat
echo.

echo Installing frontend dependencies...
cd /d "%ROOT%frontend"
npm install
echo.

echo Checking .env...
cd /d "%ROOT%backend"
if not exist .env (
    copy rename.env .env
    echo.
    echo   WARNING: .env created from rename.env
    echo   Open backend\.env and set your GEMINI_API_KEY before starting.
) else (
    echo   .env already exists - skipping.
)

echo.
echo ========================================
echo   Setup complete!
echo ========================================
echo.
echo Open 3 separate Command Prompt windows and run:
echo.
echo   Window 1 - Flask API:
echo     start-api.bat
echo.
echo   Window 2 - Celery worker:
echo     start-worker.bat
echo.
echo   Window 3 - Frontend:
echo     start-frontend.bat
echo.
echo Then open: http://localhost:5173
echo.
pause
