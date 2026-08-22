# Technology Transformation Intelligence

Enterprise platform for AI-powered project analytics and data intelligence. Connects to multiple data sources, ingests documents, and provides AI-driven insights with full source attribution and evidence tracing.

## Architecture

The platform is a **modular monolith** with:

- **Frontend**: React/TypeScript with Tailwind CSS and shadcn/ui
- **Backend**: Python/FastAPI with layered architecture (API → Service → Repository/Connector)
- **Databases**: Two internal PostgreSQL databases — App_DB (application state) and RAG_DB (document embeddings via pgvector)
- **AI Orchestration**: Strands framework with domain-scoped tools (no direct DB access from agent)
- **External Data Sources**: Read-only connectors for PostgreSQL and MongoDB

## Prerequisites

- **Node.js ≥18** (with npm)
- **Python ≥3.11** (with pip)
- **PostgreSQL ≥15** with pgvector extension

## Quick Start

```bash
# Backend setup
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux

# Frontend setup
cd frontend
npm install

# Database setup (requires running PostgreSQL)
cd backend
alembic -c alembic.ini upgrade head
alembic -c alembic_rag.ini upgrade head
python scripts/seed_data.py

# Start backend (Demo Mode)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (separate terminal)
cd frontend
npm run dev
```

- Backend API: http://localhost:8000/api/v1/
- Frontend: http://localhost:5173
- Health check: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/api/docs

## Project Structure

```
├── backend/              # Python/FastAPI backend
│   ├── app/
│   │   ├── api/v1/       # Thin route handlers
│   │   ├── config/       # Settings, feature flags
│   │   ├── models/       # ORM entities
│   │   ├── schemas/      # Pydantic request/response DTOs
│   │   ├── repositories/ # Database access layer
│   │   ├── services/     # Business logic layer
│   │   ├── connectors/   # External data source access
│   │   ├── ai/           # Orchestration, tools, prompts, providers
│   │   ├── documents/    # Ingestion pipeline
│   │   ├── errors/       # Domain error types
│   │   └── utils/        # Focused utilities
│   ├── alembic/          # App_DB migrations
│   └── tests/            # Backend test suite
├── frontend/             # React/TypeScript frontend
│   └── src/
│       ├── app/          # Shell, router, providers
│       ├── pages/        # Route-level components
│       ├── features/     # Self-contained domain features
│       ├── components/   # Shared UI components
│       ├── services/     # Typed API client
│       ├── hooks/        # Shared custom hooks
│       ├── stores/       # Global state
│       ├── config/       # Environment, flags, API URL
│       ├── types/        # Shared TypeScript types
│       └── constants/    # Application constants
├── database/             # Migration and seed scripts
├── docs/                 # Architecture documentation
│   ├── architecture/     # System diagrams and overviews
│   ├── decisions/        # Architecture Decision Records (ADRs)
│   └── setup/            # Development environment guides
└── scripts/              # Operational utilities
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DEMO_MODE` | `true` or `false` — switches between Demo and Live mode | Yes (defaults to `true`) |
| `APP_DB_URL` | App_DB PostgreSQL connection string | Yes |
| `RAG_DATABASE_URL` | RAG_DB PostgreSQL connection string | Conditional (Live Mode) |
| `LLM_PROVIDER` | Text generation provider (`azure_foundry`, `azure_openai`, `groq`, `mock`) | Conditional (Live Mode) |
| `EMBEDDING_PROVIDER` | Embedding provider identifier | Conditional (Live Mode) |
| `EMBEDDING_MODEL` | Embedding model name | Conditional (Live Mode) |
| `EMBEDDING_DIMENSION` | Vector dimension for embeddings (default: 1536) | Optional |

See `backend/.env.example` and `frontend/.env.example` for the full list with descriptions.

## Demo Mode

Set `DEMO_MODE=true` to run with deterministic seed data and `MockTextGenerationProvider`. Demo Mode uses the same APIs, services, and UI components as Live Mode — only the underlying data and LLM provider differ. No external credentials are required.

## Running Tests

```bash
# Backend tests (309 tests)
cd backend
python -m pytest tests/ -v

# Frontend type check + production build
cd frontend
npm run build
```

## Documentation

- [Local Development Setup](docs/setup/local-development.md)
- [System Architecture Overview](docs/architecture/system-overview.md)
- [Database Architecture](docs/architecture/database-architecture.md)
- [Connector Architecture](docs/architecture/connector-architecture.md)
- [AI Architecture](docs/architecture/ai-architecture.md)
- [Demo/Live Architecture](docs/architecture/demo-live-architecture.md)

### Architecture Decision Records

- [ADR-001: Modular Monolith](docs/decisions/ADR-001-modular-monolith.md)
- [ADR-002: Database Separation](docs/decisions/ADR-002-database-separation.md)
- [ADR-003: Alembic Migrations](docs/decisions/ADR-003-alembic-migrations.md)
- [ADR-004: Connector Architecture](docs/decisions/ADR-004-connector-architecture.md)
- [ADR-005: LLM Provider Abstraction](docs/decisions/ADR-005-llm-provider-abstraction.md)
- [ADR-006: Demo Mode Architecture](docs/decisions/ADR-006-demo-mode-architecture.md)
- [ADR-007: Strands Tool Architecture](docs/decisions/ADR-007-strands-tool-architecture.md)
- [ADR-008: Project Primary Context](docs/decisions/ADR-008-project-primary-context.md)
- [ADR-009: Document Ingestion Pipeline](docs/decisions/ADR-009-document-ingestion-pipeline.md)

## License

Proprietary — internal use only.
