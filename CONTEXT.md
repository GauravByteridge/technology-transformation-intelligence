# Project Intelligence Hub — Context

## What This Project Does

A RAG-based (Retrieval-Augmented Generation) proof-of-concept application that lets users:

1. **Create a single project** with a name and description
2. **Upload files** (PDF, Excel, CSV, JSON) tagged with categories
3. **Automatically process** files — extract text, chunk it, generate embeddings, and store in a vector database
4. **Ask questions** about the combined data via an AI chatbot that retrieves relevant context and generates answers
5. **Generate visualizations** from natural language queries (bar, line, pie charts)
6. **View a dashboard** with file statistics, distribution charts, and recent uploads
7. **Reset everything** to start fresh

It's a lightweight POC — no auth, no multi-user, no multi-project. One project at a time.

---

## Architecture

```
┌─────────────────┐       ┌──────────────────────────────────┐
│  React Frontend │──API──▶│       FastAPI Backend             │
│  (TypeScript)   │       │                                  │
│  Port 5173      │       │  Port 8000                       │
└─────────────────┘       │                                  │
                          │  ┌────────────┐  ┌────────────┐  │
                          │  │ PostgreSQL │  │  ChromaDB   │  │
                          │  │ (metadata) │  │ (vectors)   │  │
                          │  └────────────┘  └────────────┘  │
                          │                                  │
                          │  ┌────────────────────────────┐  │
                          │  │  Groq API (LLM inference)  │  │
                          │  └────────────────────────────┘  │
                          └──────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Recharts, Axios, React Router |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic |
| Metadata DB | PostgreSQL |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2 via ChromaDB default) |
| LLM | Groq API (llama3-8b-8192) |
| PDF Processing | PyMuPDF |
| Data Processing | pandas |

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app entry point, CORS, router registration
│   ├── requirements.txt         # Python dependencies
│   ├── api/                     # API route handlers
│   │   ├── project.py           # POST/GET/DELETE /api/project
│   │   ├── files.py             # Upload, list, download, delete files
│   │   ├── dashboard.py         # GET /api/dashboard (stats)
│   │   ├── chat.py              # POST /api/chat (RAG Q&A)
│   │   └── visualize.py         # POST /api/visualize (chart generation)
│   ├── db/
│   │   ├── database.py          # SQLAlchemy engine, session, get_db dependency
│   │   ├── chroma_client.py     # ChromaDB client, collection, CRUD helpers
│   │   └── init_db.py           # Creates PostgreSQL tables
│   ├── models/
│   │   ├── database_models.py   # SQLAlchemy ORM (Project, File)
│   │   └── schemas.py           # Pydantic request/response models
│   ├── services/
│   │   ├── file_processor.py    # Text extraction (PDF, Excel, CSV, JSON)
│   │   ├── chunker.py           # Text chunking (800-1000 chars, overlap)
│   │   ├── embeddings.py        # Embedding generation
│   │   ├── rag_pipeline.py      # Question → embed → search → prompt → LLM → answer
│   │   └── visualization.py     # Query → data retrieval → LLM → chart config
│   └── tests/                   # pytest + hypothesis property-based tests
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts           # Dev server on 5173, proxy /api → localhost:8000
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx             # React entry, BrowserRouter
│       ├── App.tsx              # Router config, project existence check
│       ├── api/client.ts        # Axios API client (all endpoint wrappers)
│       ├── types/index.ts       # TypeScript interfaces
│       ├── components/
│       │   └── NavigationBar.tsx
│       └── screens/
│           ├── CreateProjectScreen.tsx
│           ├── DashboardScreen.tsx
│           ├── DataManagementScreen.tsx
│           ├── AIChatScreen.tsx
│           └── AIVisualizationScreen.tsx
│
└── .kiro/specs/                 # Spec documents (requirements, design, tasks)
```

---

## How to Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running on localhost:5432
- A Groq API key

### Backend
```bash
cd backend
pip install -r requirements.txt
# Create the database "project_intelligence_hub" in PostgreSQL first
python -m db.init_db
export GROQ_API_KEY=your-key-here    # or set in .env
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173. The Vite dev server proxies `/api` requests to the backend at port 8000.

### Tests
```bash
cd backend
pytest tests/ -v
```

---

## Key Design Decisions

- **Single-project model**: Only one project exists at a time. Simplifies the POC.
- **ChromaDB collection**: Named `project_knowledge`, uses cosine similarity, persistent storage at `./chroma_data`.
- **Chunking**: 900 chars default with 100 char overlap between adjacent chunks.
- **Embedding**: Uses ChromaDB's built-in DefaultEmbeddingFunction (all-MiniLM-L6-v2, 384 dimensions).
- **File processing pipeline**: Upload → extract text → chunk → embed → store vectors + metadata.
- **Error format**: All API errors return `{"detail": "human-readable message"}` with appropriate HTTP status codes.
- **File categories**: Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other.
- **Supported file types**: PDF, XLSX, XLS, CSV, JSON.

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/project | Create project |
| GET | /api/project | Get current project |
| DELETE | /api/project/reset | Full reset |
| POST | /api/files/upload | Upload file (multipart + category) |
| GET | /api/files | List all files |
| GET | /api/files/{id} | Download file |
| DELETE | /api/files/{id} | Delete file + chunks |
| GET | /api/dashboard | Dashboard stats |
| POST | /api/chat | AI Q&A |
| POST | /api/visualize | Generate chart config |

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://postgres:postgres@localhost:5432/project_intelligence_hub |
| GROQ_API_KEY | Groq LLM API authentication | (required for chat/visualization) |
