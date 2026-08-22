# Local Development Setup

## Prerequisites

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Node.js | ≥18 | Frontend build and development server |
| Python | ≥3.11 | Backend application runtime |
| PostgreSQL | ≥15 | Application and RAG databases |
| pgvector | ≥0.5.0 | Vector similarity search extension for RAG_DB |
| pip | Latest | Python package management |
| npm | Latest (bundled with Node.js) | Frontend package management |

## Installation Steps

### 1. Backend Setup

```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

### 3. Environment Configuration

```bash
# Backend — copy example and edit with your local values
cd backend
cp .env.example .env

# Frontend — copy example and edit with your local values
cd frontend
cp .env.example .env
```

Required backend environment variables for Demo Mode:
- `APP_DB_URL` — PostgreSQL connection string (e.g., `postgresql+asyncpg://postgres:postgres@localhost:5432/app_db`)
- `SECRET_KEY` — Application secret key (generate with `openssl rand -hex 32`)

Optional (defaults provided): `DEMO_MODE=true`, `LOG_LEVEL=info`, `CORS_ORIGINS=http://localhost:5173`

## Database Setup

### Create Databases

```sql
CREATE DATABASE app_db;
CREATE DATABASE rag_db;
```

### Enable pgvector Extension

```sql
-- Connect to rag_db
\c rag_db
CREATE EXTENSION IF NOT EXISTS vector;
```

### Run Migrations

```bash
cd backend
alembic -c alembic.ini upgrade head
alembic -c alembic_rag.ini upgrade head
```

### Seed Demo Data

```bash
cd backend
python scripts/seed_data.py
```

Seed scripts are idempotent — running multiple times produces the same state.

## Startup Commands

### Start Backend (Demo Mode)

```bash
cd backend
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at:
- API base: http://localhost:8000/api/v1/
- Health check: http://localhost:8000/api/v1/health
- OpenAPI docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Start Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at http://localhost:5173.

The Vite dev server proxies `/api` requests to `http://localhost:8000`, so the frontend can reach the backend through the proxy without CORS issues during development.

### Run Tests

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Frontend type check and build
cd frontend
npm run build
```

## Verifying the Setup

1. **Health check:**
   ```bash
   curl http://localhost:8000/api/v1/health
   # Expected: {"status": "ok"}
   ```

2. **Project endpoint (in-memory stub):**
   ```bash
   curl http://localhost:8000/api/v1/projects/11111111-1111-1111-1111-111111111111
   # Expected: 200 with project JSON
   ```

3. **Frontend** loads at http://localhost:5173 and proxies API calls to the backend.

## Troubleshooting

### PostgreSQL Connection Fails

- Verify PostgreSQL is running: `pg_isready`
- Check `APP_DB_URL` in `.env` matches your local PostgreSQL credentials
- Ensure `app_db` and `rag_db` databases exist

### pgvector Extension Not Found

- Install pgvector for your PostgreSQL version: https://github.com/pgvector/pgvector#installation
- Run `CREATE EXTENSION vector;` while connected to `rag_db`

### Python Virtual Environment Issues

- Verify Python ≥3.11: `python --version`
- Recreate if corrupt: `rm -rf .venv && python -m venv .venv`

### Frontend Build Errors

- Verify Node.js ≥18: `node --version`
- Clear and reinstall: `rm -rf node_modules && npm install`
