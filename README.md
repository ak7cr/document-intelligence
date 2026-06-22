# Document Intelligence

A full-stack document intelligence platform for tender and procurement analysis. Upload PDF, Word, Excel, or scanned documents (including Hindi/multilingual) and get AI-powered entity extraction, summarization, risk prediction, eligibility checking, deadline tracking, semantic chat, and cross-document entity graphs — all in a session-based workspace.

---

## Features

### Document Processing
- **Multi-format support** — PDF (native + scanned), DOCX, XLSX, CSV, PNG/JPG/TIFF
- **Two-phase async pipeline** — OCR/extraction → indexed and searchable immediately; LLM analysis fills in metadata after
- **Multilingual OCR** — Hindi (Devanagari) + English in the same document
- **Switchable OCR engine** — Gemini Vision (best quality), EasyOCR (local GPU), Tesseract (CPU-only)
- **OCR fallback chain** — Gemini → EasyOCR → Tesseract; fallback shown as a badge on the document card
- **Table extraction** — PyMuPDF table finder extracts structured tables as markdown before OCR text
- **Scanned PDF tiling** — tall pages split into strips to stay within GPU VRAM limits

### AI Analysis
- **Entity extraction** — document type, dates, deadlines, parties, amounts, reference numbers; 10+ entities per document targeted
- **Smart summarization** — headline, paragraph summary, key bullet points
- **Risk prediction** — low/medium/high risk, confidence score, timeline urgency, risk factors, opportunities, recommended actions
- **All three in one LLM call** per document (structured output with JSON Schema for Ollama)
- **Hindi/multilingual** — analysis responds in English with proper nouns preserved in source language

### Verification Layer (Chat)
- **DB-first grounding** — entities, summaries, and predictions are injected as verified facts before chunk context
- **Cross-encoder reranking** — `cross-encoder/ms-marco-MiniLM-L-6-v2` reranks Qdrant results before the LLM sees them
- **Confidence scoring** — high/medium/low badge on every AI answer
- **Persistent chat history** — messages saved per session, survive page refresh, cleared per session
- **Markdown rendering** — bullet points, bold, headings rendered natively in the chat UI

### Eligibility & Compliance (Phase B)
- **Company profile** — set once per session; stored and reused across all documents
- **Eligibility checker** — compares company profile against each tender's criteria; scores 0–100 with met/missing breakdown and document checklist
- **Bid submission checklist** — auto-generated per document (Technical / Financial / Legal / Administrative categories)
- **Auto-run** — eligibility and checklist run automatically on every new document upload if a profile exists

### Deadline Tracker
- **Timeline tab** — all date/deadline entities across the session, sorted chronologically, color-coded by urgency (critical <7 days, soon <30 days, future, past)

### Cross-Document Entity Graph
- **Graph tab** — entities appearing in 2+ documents shown as clusters (parties, amounts, dates, references)
- **Run All Analysis** button — retroactively runs checklist + eligibility on all ready documents

### Export
- **Excel (.xlsx)** — Documents, Summaries, Entities sheets
- **CSV** — entities or summaries
- **JSON** — full structured data dump

### OCR Quality
- **OCR Review Banner** — amber warning above document list for any OCR-processed document below 70% confidence
- **OCR engine selector** — pill buttons in the session header to switch Gemini / EasyOCR / Tesseract without restarting

---

## Architecture

```
frontend/              React 19 + TypeScript + Tailwind CSS v4 + Vite
backend/
  app.py               Flask app factory + idempotent DB migration
  tasks.py             Two-phase Celery pipeline:
                         process_document  → OCR + chunk + embed → ready
                         run_analysis      → LLM entities/summary/risk/checklist/eligibility
  analyzer.py          Combined LLM call (entities + summary + prediction), JSON Schema constrained
  rag.py               RAG: verified DB facts + cross-encoder reranking + Gemini/Ollama
  reranker.py          cross-encoder/ms-marco-MiniLM-L-6-v2 reranker
  checklist.py         Bid submission checklist LLM module
  eligibility.py       Eligibility/compliance checker LLM module
  config.py            Runtime config store (OCR engine switchable via API)
  routes/
    sessions.py        Sessions, analytics, compare, timeline, entity-graph, run-analysis, OCR review
    documents.py       Documents, entities, summary, prediction, eligibility, checklist
    chat.py            Chat (RAG), persistent message history, clear
    config.py          GET/POST /config/ocr-engine
    export.py          XLSX, CSV, JSON exports
  ocr/
    engine.py          OCR dispatcher + EasyOCR backend (GPU tiling + CPU fallback)
    gemini_engine.py   Gemini Vision OCR with retry + EasyOCR/Tesseract fallback chain
    tesseract_engine.py Tesseract backend (hin+eng)
    enhancer.py        Image preprocessing for scanned PDFs
  processors/          PDF / DOCX / XLSX / CSV / image extractors + table finder
  vector/              Qdrant embedding (bge-small-en-v1.5, CPU) + cross-encoder reranking
  llm/client.py        Ollama + Gemini dispatch layer
  models.py            SQLAlchemy: Session, Document, DocumentText, ChatHistory,
                                   DocumentChunk, DocumentEntity, DocumentSummary,
                                   DocumentPrediction, DocumentChecklist, EligibilityCheck,
                                   CompanyProfile, DocumentChecklist
```

**Infrastructure:**
- PostgreSQL 16 — all structured data
- MinIO — object storage for uploaded files
- Redis — Celery task broker
- Qdrant — vector database for semantic search

---

## Prerequisites

- Python 3.10+ (3.14 tested)
- Node.js 18+
- Docker + Docker Compose
- GPU recommended (NVIDIA, 6+ GB VRAM) — OCR runs on CPU if VRAM is insufficient
- A Gemini API key (free at [aistudio.google.com](https://aistudio.google.com)) **or** Ollama installed locally

---

## Setup

### 1. Start infrastructure

```bash
docker compose up -d
```

Starts PostgreSQL, MinIO, Redis, and Qdrant.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

For Tesseract OCR (optional, CPU-only):
```bash
apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng
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

# LLM provider — choose one:
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.0-flash

# LLM_PROVIDER=ollama
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=qwen2:7b        # qwen2 recommended for Hindi/multilingual

# OCR engine — choose one:
# OCR_ENGINE=gemini             # Best quality, uses GEMINI_API_KEY, 1 call/page
# OCR_ENGINE=easyocr            # Local GPU (default)
# OCR_ENGINE=tesseract          # Local CPU, needs apt packages above
OCR_ENGINE=gemini

# Optional performance tuning:
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
HF_TOKEN=hf_your_token_here    # Suppresses HuggingFace rate-limit warnings
```

### 3. Start the Flask API

```bash
flask --app app run --port 5001 --debug
```

Schema is created automatically on first start (`db.create_all()` + idempotent `_migrate()`).

### 4. Start the Celery worker

In a separate terminal:

```bash
celery -A celery_worker worker --loglevel=info
```

> `solo` pool is configured automatically in `celery_app.py` (required for PaddleOCR/EasyOCR compatibility on all platforms).

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## LLM Provider Comparison

| | Gemini | Ollama (qwen2:7b) |
|---|---|---|
| Cost | 1500 req/day free | Free, unlimited |
| Speed | Fast | Slower (local hardware) |
| Privacy | Data sent to Google | 100% local |
| Hindi quality | Excellent | Good |
| JSON schema | Native | Constrained decoding |
| Best for | Production, Hindi docs | Offline, high-volume |

**Recommended for Hindi/multilingual documents:** `OCR_ENGINE=gemini` + `LLM_PROVIDER=gemini`

---

## OCR Engine Comparison

| Engine | Accuracy | VRAM | Hindi | Notes |
|---|---|---|---|---|
| Gemini | Best | None (cloud) | Native | 1 API call per page; retries on 503 with EasyOCR→Tesseract fallback |
| EasyOCR | Good | ~1 GB | Good | GPU tiling for large pages; moves to CPU if VRAM full |
| Tesseract | Decent | None | Requires `tesseract-ocr-hin` | Fast, CPU-only |

The active engine can be switched from the **session header** without restarting the worker.

---

## API Reference

All endpoints are prefixed with `/api`.

### Sessions
| Method | Path | Description |
|---|---|---|
| GET | `/sessions` | List all sessions |
| POST | `/sessions` | Create a session |
| DELETE | `/sessions/<id>` | Delete session and all its data |
| POST | `/sessions/<id>/chat` | Chat with documents (RAG) |
| GET | `/sessions/<id>/messages` | Get persistent chat history |
| DELETE | `/sessions/<id>/messages` | Clear chat history |
| GET | `/sessions/<id>/search` | Semantic search (`?q=query`) |
| POST | `/sessions/<id>/compare` | Compare 2–8 documents |
| GET | `/sessions/<id>/analytics` | Session analytics |
| GET | `/sessions/<id>/timeline` | Deadline/date timeline |
| GET | `/sessions/<id>/entity-graph` | Cross-document entity clusters |
| POST | `/sessions/<id>/run-analysis` | Batch run checklist + eligibility |
| GET | `/sessions/<id>/ocr-review` | Documents with low OCR confidence |
| GET | `/sessions/<id>/profile` | Get company profile |
| POST | `/sessions/<id>/profile` | Upsert company profile |

### Documents
| Method | Path | Description |
|---|---|---|
| POST | `/documents` | Upload a document (multipart) |
| GET | `/documents/<session_id>` | List documents in a session |
| DELETE | `/documents/<id>` | Delete document + vectors |
| GET | `/documents/<id>/entities` | Get extracted entities |
| POST | `/documents/<id>/extract` | Re-run entity extraction |
| GET | `/documents/<id>/summary` | Get summary |
| POST | `/documents/<id>/summarize` | Re-run summarization |
| GET | `/documents/<id>/prediction` | Get risk prediction |
| POST | `/documents/<id>/predict` | Re-run risk prediction |
| GET | `/documents/<id>/eligibility` | Get eligibility check result |
| POST | `/documents/<id>/eligibility` | Run eligibility check |
| GET | `/documents/<id>/checklist` | Get bid submission checklist |
| POST | `/documents/<id>/checklist` | Generate bid submission checklist |
| GET | `/documents/<id>/url` | Get presigned download URL |

### Config
| Method | Path | Description |
|---|---|---|
| GET | `/config/ocr-engine` | Get active OCR engine |
| POST | `/config/ocr-engine` | Switch OCR engine at runtime |

### Export
| Method | Path | Description |
|---|---|---|
| GET | `/sessions/<id>/export/xlsx` | Excel workbook |
| GET | `/sessions/<id>/export/csv` | CSV (`?sheet=entities\|summaries`) |
| GET | `/sessions/<id>/export/json` | Full JSON dump |

---

## Tech Stack

**Backend:** Flask · SQLAlchemy · PostgreSQL · Celery + Redis · MinIO · Qdrant · EasyOCR · Tesseract · PyMuPDF · sentence-transformers (`BAAI/bge-small-en-v1.5`, CPU) · `cross-encoder/ms-marco-MiniLM-L-6-v2` · google-genai · python-docx · openpyxl

**Frontend:** React 19 · TypeScript · Tailwind CSS v4 · Vite · TanStack Query v5 · Axios · react-markdown
