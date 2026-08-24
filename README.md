# Technology Transformation Intelligence (TTI) Platform

Enterprise intelligence platform that connects to multiple data sources, discovers and catalogs data semantically, and provides AI-powered cross-source analytics with full evidence attribution.

## Architecture

```
Enterprise Data Sources (PostgreSQL, MongoDB, Documents)
         ↓
    Data Discovery & Semantic Catalog
         ↓
    Strands AI Agent (Groq LLM + Dynamic Tool Selection)
         ↓
    Cross-Source Intelligence (RAG + Structured Queries)
         ↓
    Grounded Answers + Evidence + Data Lineage
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.0, asyncpg |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Recharts |
| Database | PostgreSQL 16 + pgvector |
| AI/LLM | Strands Agents SDK, Groq (GPT-oss-120b) |
| Embeddings | pgvector cosine similarity (deterministic for POC) |
| Document Processing | Content-aware ingestion (PDF, DOCX, XLSX, CSV, TXT) |

---

## Prerequisites

- **Python 3.11+** (tested with 3.14)
- **Node.js 18+** (for frontend)
- **PostgreSQL 16+** with pgvector extension
- **Git**

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/GauravByteridge/technology-transformation-intelligence.git
cd technology-transformation-intelligence
```

### 2. PostgreSQL Setup

Create the databases:

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create databases
CREATE DATABASE app_db;
CREATE DATABASE rag_db;

-- Enable pgvector extension in both
\c app_db
CREATE EXTENSION IF NOT EXISTS vector;

\c rag_db
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

Copy and edit the `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database — update password to match your PostgreSQL
APP_DB_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/app_db
RAG_DB_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/rag_db

# Required keys
SECRET_KEY=dev-secret-key-for-local-development
FERNET_KEY=nCDAYBmW-Gj8HRIs-dKZHETxkJSpKGYfrXLuiPwtHwU=

# Mode
DEMO_MODE=false

# LLM Provider (Groq recommended for POC)
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b

# Embeddings (use mock for POC, azure_openai for production)
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=deterministic-stub
EMBEDDING_DIMENSION=1536

# CORS
CORS_ORIGINS=http://localhost:5173
```

### 5. Run Database Migrations

```bash
cd backend

# App DB migrations
python -m alembic upgrade head

# RAG DB migrations
python -m alembic -c alembic_rag.ini upgrade head
```

### 6. Create RAG Tables in App DB (POC shortcut)

For the POC, RAG tables are co-located in `app_db`:

```sql
psql -U postgres -d app_db

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    source_id UUID,
    file_name VARCHAR(512) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size INTEGER NOT NULL,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    processing_error TEXT,
    uploaded_by UUID,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_documents_project_id ON documents(project_id);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    section VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks(document_id);

CREATE TABLE IF NOT EXISTS document_metadata (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value VARCHAR(2048) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY,
    chunk_id UUID NOT NULL UNIQUE REFERENCES document_chunks(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    dimension INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_embeddings_chunk_id ON embeddings(chunk_id);
```

### 7. Seed Demo Data

```bash
cd backend

# Run the seed script (creates projects, users, sample data)
python -m app.seed.run
```

Or manually create the system user required for file uploads:

```sql
psql -U postgres -d app_db

INSERT INTO users (id, email, name, role)
VALUES ('00000000-0000-0000-0000-000000000001', 'system@tti.internal', 'System', 'system')
ON CONFLICT (id) DO NOTHING;
```

### 8. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 9. Update Launcher Config (if using Launcher)

Edit `scripts/launcher-ui/launcher-config.json` and update the password:

```json
{
  "environment": {
    "APP_DB_URL": "postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/app_db",
    "RAG_DB_URL": "postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/rag_db"
  }
}
```

---

## Running

### Option A: Using the Launcher (recommended)

```bash
# From project root
Launcher.bat
# Opens dashboard at http://localhost:9001
# Start Backend and Frontend from the dashboard
```

### Option B: Manual Start

Terminal 1 — Backend:
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 — Frontend:
```bash
cd frontend
npm run dev
```

### Access

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Launcher**: http://localhost:9001 (if using Launcher.bat)

---

## Key Features

### Data Sources
- Connect PostgreSQL and MongoDB sources
- Automatic schema discovery and semantic profiling
- Enterprise Data Catalog with domain tagging

### Document Upload (RAG)
- Upload PDF, DOCX, XLSX, CSV, TXT files
- Content-aware processing: structured → datasets, unstructured → RAG
- Chunking with page/section tracking
- pgvector cosine similarity search

### AI Query (Analytics Canvas)
- Project-scoped conversational AI
- Strands Agent with dynamic tool selection
- Cross-source intelligence (DB + Documents + Catalog)
- Evidence panel with source attribution
- Chart/Table toggle for analytical results
- Data lineage tracing

### Project 360
- Per-project dashboard with KPIs
- Financial, JIRA, Resource, Audit, Risk tabs
- Inline AI assistant scoped to project

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── ai/              # Strands agent, tools, prompts
│   │   ├── api/v1/          # FastAPI route handlers
│   │   ├── config/          # Settings, logging
│   │   ├── connectors/      # PostgreSQL, MongoDB connectors
│   │   ├── documents/       # RAG pipeline (chunker, embedder, orchestrator)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── processors/      # File type processors (Excel, CSV, PDF, etc.)
│   │   ├── repositories/    # Database access layer
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Business logic layer
│   ├── alembic/             # App DB migrations
│   ├── alembic_rag/         # RAG DB migrations
│   └── .env                 # Environment configuration
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── features/        # Feature modules (ai-chat, catalog, etc.)
│   │   ├── pages/           # Route pages
│   │   ├── hooks/           # React Query hooks
│   │   └── types/           # TypeScript interfaces
│   └── package.json
├── scripts/
│   └── launcher-ui/         # Development launcher
└── README.md
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_DB_URL` | Yes | PostgreSQL connection for app state |
| `RAG_DB_URL` | Yes (Live) | PostgreSQL connection for RAG/vectors |
| `SECRET_KEY` | Yes | Signing key for tokens |
| `FERNET_KEY` | Yes | Encryption key for credentials |
| `DEMO_MODE` | No | `true` for mock data, `false` for real |
| `LLM_PROVIDER` | Yes (Live) | `groq`, `azure_openai`, or `azure_foundry` |
| `GROQ_API_KEY` | If Groq | Groq API key |
| `EMBEDDING_PROVIDER` | No | `mock`, `azure_openai` |
| `CORS_ORIGINS` | No | Allowed frontend origins |

---

## Troubleshooting

### PostgreSQL password error
- Check `.env` has the correct password
- If using Launcher, also update `scripts/launcher-ui/launcher-config.json`
- The Launcher env vars override `.env` file values

### Windows asyncpg errors
- The app uses `WindowsSelectorEventLoopPolicy` for asyncpg compatibility
- Ensure Python 3.11+ is installed

### Port already in use
- Kill existing processes: `Get-NetTCPConnection -LocalPort 8000 | Stop-Process`
- Or use a different port: `--port 8001`

### CORS errors
- Ensure `CORS_ORIGINS` in `.env` includes `http://localhost:5173`
- Restart the backend after changing CORS settings
