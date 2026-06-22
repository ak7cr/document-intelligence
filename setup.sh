#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "  Document Intelligence — First-time Setup"
echo "========================================"
echo

echo "▶ Starting infrastructure (PostgreSQL, Redis, MinIO, Qdrant)..."
docker compose up -d
echo

echo "▶ Setting up Python virtual environment..."
cd "$ROOT/backend"
if command -v python3 &>/dev/null; then
    python3 -m venv venv
else
    python -m venv venv
fi
source venv/bin/activate
pip install --quiet --upgrade pip
pip install -r requirements.txt
deactivate
echo

echo "▶ Installing frontend dependencies..."
cd "$ROOT/frontend"
npm install
echo

echo "▶ Checking .env..."
cd "$ROOT/backend"
if [ ! -f ".env" ]; then
    cp rename.env .env
    echo
    echo "  ⚠️  .env created from rename.env"
    echo "  Open backend/.env and set your GEMINI_API_KEY before starting."
else
    echo "  .env already exists — skipping."
fi

echo
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo
echo "Open 3 separate terminals and run:"
echo
echo "  Terminal 1 — Flask API:"
echo "    ./start-api.sh"
echo
echo "  Terminal 2 — Celery worker:"
echo "    ./start-worker.sh"
echo
echo "  Terminal 3 — Frontend:"
echo "    ./start-frontend.sh"
echo
echo "Then open: http://localhost:5173"
echo
