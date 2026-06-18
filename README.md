# Tender Intelligence

A document intelligence platform for procurement and tender analysis. Upload PDF, Word, Excel, or scanned documents and get AI-powered entity extraction, summarization, risk prediction, semantic search, and multi-document comparison — all in one session-based workspace.

---

## Features

### Document Processing
- **Multi-format support** — PDF (native text + scanned/image-based via OCR), DOCX, XLSX, XLS, plain text
- **PaddleOCR** for scanned documents — auto-detects image-based pages and OCRs them
- **Async pipeline** — upload is instant; processing (OCR → chunking → embedding → AI analysis) runs in the background via Celery

### AI Analysis (1 LLM call per document)
- **Entity extraction** — document type, dates, deadlines, parties, amounts, reference numbers
- **Smart summarization** — headline, 2-3 sentence summary, key bullet points
- **Risk prediction** — low/medium/high risk level, confidence score, timeline urgency, risk factors, opportunities, recommended actions

### Session Workspace
- **Sessions** organize documents into projects (e.g. one session per tender)
- **Semantic search** — vector search across all documents in a session (RAG with source citations)
- **Chat** — ask questions about documents; answers are grounded with `[Source N]` citations and page number estimates
- **Multi-document comparison** — compare 2–8 documents side-by-side with AI-generated differences table, similarities, and recommendation
- **Analytics** — totals, document type breakdown, entity type breakdown, top entities, upload timeline
- **Predictions panel** — risk cards for every document with expandable details

### Export
- **Excel (.xlsx)** — 3-sheet workbook: Documents, Summaries, Entities
- **CSV** — separate exports for entities, summaries, or document list
- **JSON** — full structured data dump for the session

### LLM Providers
- **Gemini** (cloud) — `gemini-2.0-flash` recommended (1500 req/day free tier)
- **Ollama** (local) — fully offline, no quota, supports any model (`llama3.2`, `mistral`, etc.)

---

## Architecture

```
frontend/          React 19 + TypeScript + Tailwind CSS v4 + Vite
backend/
  app.py           Flask app factory
  tasks.py         Celery task: OCR → chunk → embed → analyze
  analyzer.py      Combined LLM call (entities + summary + prediction)
  rag.py           RAG pipeline for chat (embed query → Qdrant → Gemini)
  routes/          Flask Blueprints (sessions, documents, chat, export)
  ocr/             PaddleOCR wrapper
  processors/      PDF / DOCX / XLSX / text extractors
  vector/          Qdrant embedding + search
  models.py        SQLAlchemy models
```

**Infrastructure (Docker Compose):**
- PostgreSQL 16 — sessions, documents, entities, summaries, predictions
- MinIO — object storage for uploaded files
- Redis — Celery broker
- Qdrant — vector database for semantic search

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com)) **or** Ollama installed locally

---

## Setup

### 1. Start infrastructure

```bash
docker compose up -d
```

This starts PostgreSQL, MinIO, Redis, and Qdrant.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy and configure the environment file:

```bash
cp rename.env .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://admin:adminpassword@localhost:5432/tender_rag
SECRET_KEY=change-me-in-production

REDIS_URL=redis://localhost:6379/0

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=tender-documents
MINIO_SECURE=false

QDRANT_HOST=localhost
QDRANT_PORT=6333

# Choose one LLM provider:
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash

# --- OR ---
# LLM_PROVIDER=ollama
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=llama3.2
```

Run database migrations and create the MinIO bucket:

```bash
flask --app app db upgrade
python -c "
from storage.minio_client import get_client
from minio import Minio
import os
from dotenv import load_dotenv
load_dotenv()
c = get_client()
if not c.bucket_exists(os.getenv('MINIO_BUCKET','tender-documents')):
    c.make_bucket(os.getenv('MINIO_BUCKET','tender-documents'))
    print('Bucket created')
"
```

### 3. Start the Flask API

```bash
cd backend
source venv/bin/activate
flask --app app run --port 5001 --debug
```

### 4. Start the Celery worker

In a separate terminal:

```bash
cd backend
source venv/bin/activate
celery -A celery_worker worker --loglevel=info --pool=solo
```

> `--pool=solo` is required on macOS. Use `--concurrency=2` on Linux for parallel processing.

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Using Ollama (local, offline)

1. Install Ollama from [ollama.com](https://ollama.com)
2. Pull a model: `ollama pull llama3.2`
3. Start the server: `ollama serve`
4. Set in `.env`:
   ```env
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3.2
   ```
5. Restart the Flask server and Celery worker

**When to use Ollama vs Gemini:**

| | Ollama | Gemini |
|---|---|---|
| Cost | Free, unlimited | 1500 req/day free |
| Speed | Slower (local hardware) | Fast |
| Privacy | 100% local | Data sent to Google |
| Quality | Good | Better on complex docs |
| Best for | Development, high-volume testing | Demos, production |

---

## API Reference

All endpoints are prefixed with `/api`.

### Sessions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/sessions` | List all sessions |
| POST | `/sessions` | Create a session |
| DELETE | `/sessions/<id>` | Delete a session and all its documents |

### Documents
| Method | Path | Description |
|--------|------|-------------|
| POST | `/documents` | Upload a document (multipart) |
| GET | `/documents/<session_id>` | List documents in a session |
| DELETE | `/documents/<id>` | Delete a document |
| GET | `/documents/<id>/entities` | Get extracted entities |
| POST | `/documents/<id>/extract` | Re-run entity extraction |
| GET | `/documents/<id>/summary` | Get document summary |
| POST | `/documents/<id>/summarize` | Re-run summarization |
| GET | `/documents/<id>/prediction` | Get risk prediction |
| POST | `/documents/<id>/predict` | Re-run risk prediction |
| GET | `/documents/<id>/url` | Get presigned download URL |

### Session Intelligence
| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions/<id>/chat` | Chat with documents (RAG) |
| GET | `/sessions/<id>/search` | Semantic search (`?q=query`) |
| POST | `/sessions/<id>/compare` | Compare 2–8 documents |
| GET | `/sessions/<id>/analytics` | Session analytics |

### Export
| Method | Path | Description |
|--------|------|-------------|
| GET | `/sessions/<id>/export/xlsx` | Download Excel workbook |
| GET | `/sessions/<id>/export/csv` | Download CSV (`?sheet=entities\|summaries\|documents`) |
| GET | `/sessions/<id>/export/json` | Download full JSON dump |

---

## Tech Stack

**Backend:** Flask · SQLAlchemy · Celery · PostgreSQL · MinIO · Qdrant · PaddleOCR · sentence-transformers (`BAAI/bge-small-en-v1.5`) · google-genai · PyMuPDF · python-docx · openpyxl

**Frontend:** React 19 · TypeScript · Tailwind CSS v4 · Vite · TanStack Query v5 · Axios
