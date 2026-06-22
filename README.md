# Document Intelligence

A full-stack document intelligence platform for tender and procurement analysis. Upload PDF, Word, Excel, or scanned documents (including Hindi/multilingual) and get AI-powered entity extraction, summarization, deadline tracking, semantic chat, and cross-document entity graphs — all in a session-based workspace.

---

## Getting Started

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — for PostgreSQL, Redis, MinIO, Qdrant
- Python 3.10+
- Node.js 18+
- A Gemini API key — get one free at [aistudio.google.com](https://aistudio.google.com)

---

### Mac / Linux

**Step 1 — One-time setup** (run once):
```bash
./setup.sh
```
This starts the infrastructure, creates the Python venv, installs all dependencies, and copies the env file.

**Step 2 — Add your API key:**
```
Open backend/.env and set GEMINI_API_KEY=your-key-here
```

**Step 3 — Open 3 terminals:**

| Terminal | Command |
|---|---|
| 1 — Flask API | `./start-api.sh` |
| 2 — Celery worker | `./start-worker.sh` |
| 3 — Frontend | `./start-frontend.sh` |

Open **http://localhost:5173** in your browser.

---

### Windows

**Step 1 — One-time setup** (double-click or run in Command Prompt):
```
setup.bat
```

**Step 2 — Add your API key:**
```
Open backend\.env and set GEMINI_API_KEY=your-key-here
```

**Step 3 — Open 3 Command Prompt windows:**

| Window | Command |
|---|---|
| 1 — Flask API | `start-api.bat` |
| 2 — Celery worker | `start-worker.bat` |
| 3 — Frontend | `start-frontend.bat` |

Open **http://localhost:5173** in your browser.

---

## Features

### Document Processing
- **Multi-format** — PDF (native text + scanned), DOCX, XLSX, CSV, PNG/JPG/TIFF
- **Two-phase async pipeline** — OCR/extraction completes first; document is immediately searchable. LLM analysis (entities, summary, checklist) runs after in the background.
- **Multilingual OCR** — Hindi (Devanagari) + English in the same document
- **Switchable OCR engine** — Gemini Vision (best), EasyOCR (local GPU), Tesseract (CPU-only). Switch via pill buttons in the session header — no restart needed.
- **OCR fallback chain** — Gemini → EasyOCR → Tesseract. Fallback shown as a warning badge on the document card.
- **Table extraction** — PyMuPDF table finder converts tables to markdown before OCR for better LLM understanding

### AI Analysis (auto-runs on every upload)
- **Entity extraction** — document type, dates, deadlines, parties, amounts, reference numbers (10+ entities targeted)
- **Summarization** — headline, paragraph summary, key bullet points
- **Bid submission checklist** — items grouped by Technical / Financial / Legal / Administrative categories; shown in the document's Checklist tab
- **Hindi/multilingual** — analysis responds in English, proper nouns preserved in original script

### Chat (RAG)
- **Ask questions** about any document in the session
- **Verified facts grounding** — entities and summaries are injected before chunk context so factual answers (amounts, dates, names) come from structured data, not guesswork
- **Cross-encoder reranking** — `cross-encoder/ms-marco-MiniLM-L-6-v2` reranks retrieved chunks before the LLM sees them
- **Confidence badge** — high / medium / low on every answer
- **Persistent history** — chat saved per session, survives page refresh; Clear button to wipe it
- **Markdown rendering** — bullet points, bold, headings render natively

### Document Tabs
- **Documents** — upload, view, delete; OCR engine selector; per-document insights (Summary / Entities / Checklist)
- **Chat** — ask questions, get grounded answers with source citations
- **Compare** — compare 2–8 documents side-by-side (AI-generated differences, similarities, recommendation)
- **Timeline** — all dates and deadlines across the session, sorted chronologically, color-coded by urgency
- **Graph** — entities appearing in 2+ documents shown as clusters (cross-document connections)

### Export
- **Excel (.xlsx)** — Documents, Summaries, Entities sheets
- **CSV** — entities or summaries
- **JSON** — full structured data dump

---

## Architecture

```
frontend/              React 19 + TypeScript + Tailwind CSS v4 + Vite
                       Served via nginx on port 80; /api/* proxied to backend

backend/
  app.py               Flask app factory + idempotent DB column migrations
  tasks.py             Two-phase Celery pipeline:
                         process_document → OCR + chunk + embed → status "ready"
                         run_analysis     → entities + summary + checklist (LLM)
  analyzer.py          Single LLM call: entities + summary (JSON Schema constrained)
  checklist.py         Bid submission checklist LLM module
  rag.py               RAG: DB verified facts + cross-encoder reranking + LLM answer
  reranker.py          cross-encoder/ms-marco-MiniLM-L-6-v2
  config.py            Runtime OCR engine config (switchable without restart)
  routes/
    sessions.py        Sessions, compare, timeline, entity-graph, OCR review
    documents.py       Documents, entities, summary, checklist
    chat.py            Chat (RAG) + persistent message history
    config.py          GET/POST /config/ocr-engine
    export.py          XLSX, CSV, JSON
  ocr/
    engine.py          OCR dispatcher + EasyOCR (GPU tiling, CPU fallback)
    gemini_engine.py   Gemini Vision OCR — retry on 503 + EasyOCR/Tesseract fallback
    tesseract_engine.py Tesseract (hin+eng)
    enhancer.py        Image preprocessing for scanned PDFs
  processors/          PDF / DOCX / XLSX / CSV / image extractors + table finder
  vector/              Qdrant embedding (bge-small-en-v1.5, CPU) + reranking
  llm/client.py        Ollama + Gemini dispatch

Infrastructure (Docker):
  PostgreSQL 16        All structured data
  MinIO                Object storage for uploaded files
  Redis                Celery task broker
  Qdrant               Vector database for semantic search
```

---


## LLM Provider Comparison

| | Gemini | Ollama (qwen2:7b) |
|---|---|---|
| Cost | 1500 req/day free | Free, unlimited |
| Speed | Fast | Slower (depends on hardware) |
| Privacy | Data sent to Google | 100% local |
| Hindi / multilingual | Excellent | Good |
| JSON schema compliance | Native | Constrained decoding |
| Best for | Production, Hindi docs | Offline, high-volume |

**Recommended for Hindi documents:** `OCR_ENGINE=gemini` + `LLM_PROVIDER=gemini`

For Ollama, install from [ollama.com](https://ollama.com) and pull a model:
```bash
ollama pull qwen2:7b
```
On Windows with Docker, Ollama on the host is reachable at `http://host.docker.internal:11434`.

---

## OCR Engine Comparison

| Engine | Quality | GPU | Hindi | Notes |
|---|---|---|---|---|
| Gemini | Best | No (cloud) | Native | 1 API call per page; fallback to EasyOCR → Tesseract on error |
| EasyOCR | Good | Optional | Good | GPU tiling prevents OOM; moves to CPU if VRAM full |
| Tesseract | Decent | No (CPU) | Needs `tesseract-ocr-hin` | Fast, works everywhere |

Switch engine via the pill buttons in the session header — takes effect immediately for the next upload.

---

## API Reference

All endpoints are prefixed with `/api`.

### Sessions
| Method | Path | Description |
|---|---|---|
| GET | `/sessions` | List all sessions |
| POST | `/sessions` | Create a session `{"name": "...", "description": "..."}` |
| DELETE | `/sessions/<id>` | Delete session and all its data |
| POST | `/sessions/<id>/chat` | Chat with documents `{"question": "..."}` |
| GET | `/sessions/<id>/messages` | Persistent chat history |
| DELETE | `/sessions/<id>/messages` | Clear chat history |
| GET | `/sessions/<id>/search` | Semantic search `?q=query` |
| POST | `/sessions/<id>/compare` | Compare docs `{"doc_ids": [...]}` |
| GET | `/sessions/<id>/timeline` | Date/deadline timeline |
| GET | `/sessions/<id>/entity-graph` | Cross-document entity clusters |
| GET | `/sessions/<id>/ocr-review` | Docs with low OCR confidence |

### Documents
| Method | Path | Description |
|---|---|---|
| POST | `/documents` | Upload a document (multipart `file` + `session_id`) |
| GET | `/documents/<session_id>` | List documents in a session |
| DELETE | `/documents/<id>` | Delete document + vectors |
| GET | `/documents/<id>/entities` | Extracted entities |
| POST | `/documents/<id>/extract` | Re-run entity extraction |
| GET | `/documents/<id>/summary` | Document summary |
| POST | `/documents/<id>/summarize` | Re-run summarization |
| GET | `/documents/<id>/checklist` | Bid submission checklist |
| POST | `/documents/<id>/checklist` | Generate / regenerate checklist |
| GET | `/documents/<id>/url` | Presigned download URL |

### Config
| Method | Path | Description |
|---|---|---|
| GET | `/config/ocr-engine` | Get active OCR engine |
| POST | `/config/ocr-engine` | Switch engine `{"ocr_engine": "gemini"}` |

### Export
| Method | Path | Description |
|---|---|---|
| GET | `/sessions/<id>/export/xlsx` | Excel workbook |
| GET | `/sessions/<id>/export/csv` | CSV `?sheet=entities\|summaries` |
| GET | `/sessions/<id>/export/json` | Full JSON dump |

---

## Tech Stack

**Backend:** Flask · SQLAlchemy · PostgreSQL · Celery + Redis · MinIO · Qdrant · EasyOCR · Tesseract · PyMuPDF · sentence-transformers (`BAAI/bge-small-en-v1.5`, CPU) · `cross-encoder/ms-marco-MiniLM-L-6-v2` · google-genai · python-docx · openpyxl · pymupdf_layout

**Frontend:** React 19 · TypeScript · Tailwind CSS v4 · Vite · TanStack Query v5 · Axios · react-markdown

**Deployment:** Docker Compose · nginx (reverse proxy + SPA serving)
