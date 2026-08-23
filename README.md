# Automotive AI Diagnostic Engine

A provider-agnostic, RAG-backed diagnostic reasoning API for automotive symptoms and DTC codes.

## Overview

The engine accepts vehicle symptoms and optional diagnostic trouble codes (DTCs), retrieves relevant knowledge using vector similarity search, and uses a local or cloud LLM to generate structured diagnostic hypotheses with supporting evidence, severity, recommended checks, and repair suggestions.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  FastAPI API    │────▶│ Diagnostic Service│────▶│ Embedding Service│
│  /api/v1/...    │     │ (RAG reasoning)  │     │ (sentence-     │
└─────────────────┘     └──────────────────┘     │  transformers  │
                             │                    │  or OpenAI)    │
                             ▼                    └─────────────────┘
                      ┌──────────────────┐
                      │  LLM Service     │
                      │  Ollama / OpenAI │
                      └──────────────────┘
                             │
                             ▼
                      ┌──────────────────┐
                      │ PostgreSQL +     │
                      │ pgvector         │
                      └──────────────────┘
```

## Tech Stack

- **FastAPI** - Web framework
- **SQLAlchemy 2.0** - ORM
- **PostgreSQL + pgvector** - Vector database
- **Alembic** - Database migrations
- **sentence-transformers** - Local embedding model (default: `all-MiniLM-L6-v2`, 384-dim)
- **Ollama** - Default local LLM (default model: `llama3.1:latest`)
- **OpenAI** - Optional cloud LLM / embedding provider
- **pytest** - Testing
- **React + TypeScript + Vite** - Frontend framework

## Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- PostgreSQL 12+ with pgvector extension
- Ollama (for local LLM, optional if using OpenAI)

## Project Structure

```
automotive-diagnostic-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/           # API routers
│   │   ├── config.py         # Pydantic settings
│   │   ├── db/               # SQLAlchemy models, session, migrations
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   └── services/         # Embedding, LLM, diagnostic services
│   ├── tests/                # pytest suite
│   ├── alembic/              # Alembic migrations
│   ├── .env                  # Local environment variables
│   └── requirements.txt
├── frontend/
│   ├── src/                  # Frontend source code
│   ├── public/               # Static assets
│   ├── .env                  # Frontend environment variables
│   ├── package.json          # npm dependencies
│   └── vite.config.ts        # Vite configuration
├── .env.example
└── README.md
```

## Environment Variables

Copy `.env.example` to `backend/.env` and adjust for your environment.

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `POSTGRES_SERVER` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `automotive_diagnostic` | Database name |
| `DATABASE_URL` | auto-built | Optional full SQLAlchemy URL |

### Embedding

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `sentence-transformers` | `sentence-transformers` or `openai` |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local model name |
| `EMBEDDING_DIMENSIONS` | `384` | Vector dimension |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |

### LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` |
| `LLM_MODEL` | `llama3.1:latest` | Model tag/name |
| `LLM_BASE_URL` | `http://localhost:11434` | Ollama base URL |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_MAX_TOKENS` | `2048` | Max response tokens |
| `OPENAI_API_KEY` | | Required when using OpenAI |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

## Setup

### 1. Install Python dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install Node.js dependencies

```bash
cd frontend
npm install
```

### 3. Start PostgreSQL with pgvector

Ensure PostgreSQL is running and the `vector` extension is available in the target database.

To install pgvector extension:
```bash
# For Ubuntu/Debian
sudo apt-get install postgresql-postgis-12  # Version may vary

# For macOS with Homebrew
brew install postgis

# Then enable the extension in your database:
psql -U postgres -d automotive_diagnostic -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 4. Run migrations

```bash
cd backend
alembic upgrade head
```

### 5. Start Ollama (default LLM)

```bash
ollama run llama3.1:latest
```

### 6. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### 7. Start the frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## API Usage

### Analyze symptoms

```bash
curl -X POST http://localhost:8000/api/v1/diagnostics/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "vin": "1HGCM82633A123456",
    "make": "Toyota",
    "model": "Camry",
    "year": 2020,
    "symptom_text": "Engine hesitates during acceleration and idles roughly",
    "dtc_codes": ["P0300", "P0171"]
  }'
```

### Response

```json
{
  "session_id": "uuid",
  "vehicle": {
    "vin": "1HGCM82633A123456",
    "make": "Toyota",
    "model": "Camry",
    "year": 2020
  },
  "query": "Engine hesitates during acceleration and idles roughly DTC codes: P0300,P0171",
  "evidence": [
    {
      "id": "uuid",
      "category": "symptom",
      "entry_key": "rough_idle",
      "content": "Rough idle can be caused by vacuum leaks...",
      "source": "automotive-diagnostics-v1",
      "similarity_score": 0.72
    }
  ],
  "hypotheses": [
    {
      "fault_description": "Vacuum leak causing lean condition and rough idle",
      "confidence_score": 0.85,
      "severity": "high",
      "supporting_evidence": [
        "[symptom] rough_idle"
      ],
      "recommended_checks": [
        "Smoke test intake manifold and vacuum lines",
        "Inspect MAF sensor readings"
      ],
      "repair_suggestion": "Replace cracked vacuum hose and verify fuel trims"
    }
  ]
}
```

## Knowledge management

Knowledge documents can be loaded into the vector store via the seed scripts or API. The diagnostic pipeline retrieves the top-k most similar chunks using cosine distance and includes them as evidence in the LLM prompt.

### Seed knowledge from files

Place JSON arrays or JSON Lines (`.jsonl`) files under `knowledge_base/` and run:

```bash
cd backend
PYTHONPATH=. .venv/Scripts/python scripts/seed_knowledge.py
```

Use `--reset` to truncate existing entries before reseeding, or `--path <dir>` to load from a different directory.

### Bulk upload via API

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "entries": [
      {
        "category": "symptom",
        "entry_key": "rough_idle",
        "content": "Rough idle can be caused by vacuum leaks...",
        "source": "service-manual"
      }
    ]
  }'
```

Duplicate `(category, entry_key)` pairs are skipped by default.

## Testing

### Backend tests

```bash
cd backend
pytest -q
```

The test suite uses:
- `FakeEmbeddingService` to avoid loading the transformer model
- `FakeLLMService` to avoid network calls
- A separate test database engine to prevent connection pool contention

### Frontend tests

```bash
cd frontend
npm test -- --run
```

### TypeScript checking

```bash
cd frontend
npx tsc --noEmit
```

### Frontend build

```bash
cd frontend
npm run build
```

## Evaluation harness

To run the full diagnostic evaluation suite:

```bash
cd backend
python -m evaluation
```

This runs the system against 25 benchmark cases using a deterministic mock LLM provider for consistent results.

The evaluation report is available at:
`backend/evaluation/EVALUATION_REPORT.md`

## Provider Switching

To use OpenAI instead of Ollama:

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export LLM_MODEL=gpt-4o-mini
```

To use OpenAI embeddings:

```bash
export EMBEDDING_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export EMBEDDING_DIMENSIONS=1536
```

No application code changes are required when switching providers.