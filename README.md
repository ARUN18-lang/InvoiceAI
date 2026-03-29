# SmartInvoiceAI

Monorepo for an invoice-focused app: **FastAPI** backend, **React (Vite)** frontend, and an optional **Docling** microservice for document extraction.

## Repository layout

| Directory | Role |
|-----------|------|
| `backend/` | REST API, RAG/chat, invoice storage (MongoDB), optional Neo4j graph |
| `frontend/` | Web UI |
| `docling_service/` | Optional PDF extraction service consumed by the backend |

## Prerequisites

- Python 3.11+ (recommended)
- Node.js 18+ and npm
- MongoDB (local or Atlas)
- OpenAI API key (see `backend/.env.example`)
- Optional: Neo4j, Docling service for enhanced extraction

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit .env with your keys and URIs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env        # point VITE_* vars at your API if needed
npm run dev
```

### Docling service (optional)

```bash
cd docling_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

Set `DOCLING_SERVICE_URL` in `backend/.env` to match (see `backend/.env.example`).

## Environment

Do not commit real `.env` files. Use the `*.env.example` files in `backend/` and `frontend/` as templates.

## Remote

Upstream: [github.com/ARUN18-lang/InvoiceAI](https://github.com/ARUN18-lang/InvoiceAI)
