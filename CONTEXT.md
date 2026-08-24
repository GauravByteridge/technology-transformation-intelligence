# Project Intelligence Hub — Context

## What This Project Does

A RAG-based (Retrieval-Augmented Generation) proof-of-concept application that lets users:

1. **Create a single project** with a name and description
2. **Upload files** (PDF, Excel, CSV, JSON) tagged with categories — up to 50MB per file
3. **Automatically process** files — extract text, chunk it, generate embeddings, and store in a vector database
4. **Ask questions** about the combined data via an AI chatbot that retrieves relevant context and generates answers
5. **Generate visualizations** from natural language queries (bar, line, pie charts)
6. **View a dashboard** with file statistics, distribution charts, and recent uploads
7. **Reset everything** to start fresh

It's a lightweight POC — no auth, no multi-user, no multi-project. One project at a time.

---

## Architecture

```
┌─────────────────────┐       ┌──────────────────────────────────┐
│   React Frontend    │──API──▶│       FastAPI Backend             │
│   (TypeScript)      │       │                                  │
│   Port 5173         │       │  Port 8000                       │
│   Dark Theme UI     │       │                                  │
│   Sidebar Layout    │       │  ┌────────────┐  ┌────────────┐  │
└─────────────────────┘       │  │ PostgreSQL │  │  ChromaDB   │  │
                              │  │ (metadata) │  │ (vectors)   │  │
                              │  └────────────┘  └────────────┘  │
                              │                                  │
                              │  ┌────────────────────────────┐  │
                              │  │  Groq LLM (gpt-oss-120b)   │  │
                              │  │  via Strands Agents + LiteLLM│  │
                              │  └────────────────────────────┘  │
                              └──────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite, Recharts, Axios, React Router, react-markdown |
| Backend | Python 3.14, FastAPI, SQLAlchemy, Pydantic |
| Metadata DB | PostgreSQL |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384 dimensions) |
| LLM | Groq (`openai/gpt-oss-120b`) — via Strands Agents SDK + LiteLLM |
| Agent Framework | Strands Agents SDK with LiteLLM |
| PDF Processing | PyMuPDF |
| Data Processing | pandas, openpyxl |

---

## Current State (August 2026)

### ✅ Working Features

- **Dual-Pipeline Data Architecture**: Intelligent routing between structured and unstructured data
- **Structured Data Queries**: Exact numerical answers from SQL-like queries (no hallucination)
- **Chat**: Strands Agent with smart tool selection for structured vs unstructured data
- **File Upload**: Supports up to 50MB files, async chunked upload
- **Dark Theme UI**: Professional Databricks-style interface with sidebar navigation
- **Markdown Rendering**: Chat responses rendered with proper formatting

### Recent Changes (August 24, 2026)

1. **Dual-Pipeline Architecture**
   - **Structured Pipeline**: Excel tables, CSV → relational database → SQL queries → exact answers
   - **Unstructured Pipeline**: PDF, text → semantic chunking → embeddings → ChromaDB → RAG

2. **Query Classification & Routing**
   - Questions automatically classified as STRUCTURED, UNSTRUCTURED, or HYBRID
   - Financial/numerical questions routed to structured query engine
   - Document content questions routed to vector search RAG
   - Hybrid queries combine both approaches

3. **Structured Data Storage**
   - New database tables: `structured_datasets`, `structured_columns`, `structured_rows`
   - Preserves numeric types (currency, percentages)
   - Detects and stores summary rows (TOTAL, PORTFOLIO TOTAL, etc.)
   - Column metadata with type inference

4. **Smart Excel Processing**
   - Per-sheet classification (structured vs unstructured)
   - Header row detection
   - Summary row detection
   - Currency column detection by name and value patterns
   - Type-preserving data extraction

5. **New Agent Tools**
   - `query_structured_data`: SQL-like queries on structured data
   - `get_financial_summary`: Portfolio-level financial metrics
   - `list_structured_datasets`: Available structured data
   - `search_documents`: Semantic search on unstructured documents

### Example: Exact Financial Answers

**Question:** "What is the portfolio total approved budget for Financial Health?"

**Old Behavior (Broken):**
- Vector search for "approved budget" → random chunks
- LLM estimates/hallucinates a number

**New Behavior (Fixed):**
1. Query classified as STRUCTURED (operation: sum, column: approved_budget)
2. SQL query: `SUM(approved_budget)` on Financial Health sheet
3. Returns exact value: **$33,800,000** from 15 records
4. Includes source citation: Executive_Portfolio_Report.xlsx / Financial Health

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app entry point, CORS, router registration
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Environment variables (API keys)
│   ├── api/                     # API route handlers
│   │   ├── project.py           # POST/GET/DELETE /api/project
│   │   ├── files.py             # Upload (dual pipeline), list, download, delete
│   │   ├── dashboard.py         # GET /api/dashboard (stats)
│   │   ├── chat.py              # POST /api/chat (Strands RAG Agent)
│   │   └── visualize.py         # POST /api/visualize (chart generation)
│   ├── db/
│   │   ├── database.py          # SQLAlchemy engine, session, get_db dependency
│   │   ├── chroma_client.py     # ChromaDB client, collection, CRUD helpers
│   │   └── init_db.py           # Creates PostgreSQL tables
│   ├── models/
│   │   ├── database_models.py   # SQLAlchemy ORM (Project, File)
│   │   ├── structured_data_models.py  # NEW: StructuredDataset, Column, Row, QueryLog
│   │   └── schemas.py           # Pydantic request/response models
│   ├── services/
│   │   ├── file_processor.py    # Text extraction (PDF, Excel, CSV, JSON)
│   │   ├── chunker.py           # Text chunking (legacy, 900 chars)
│   │   ├── embeddings.py        # Embedding generation (sentence-transformers)
│   │   ├── strands_agent.py     # UPDATED: Smart agent with structured + unstructured tools
│   │   ├── rag_pipeline.py      # Legacy simple RAG pipeline (not used)
│   │   ├── visualization.py     # Query → data retrieval → LLM → chart config
│   │   │
│   │   ├── ingestion/           # NEW: Dual-pipeline ingestion services
│   │   │   ├── __init__.py
│   │   │   ├── file_classifier.py         # Classifies files as structured/unstructured
│   │   │   ├── excel_processor.py         # Type-preserving Excel extraction
│   │   │   ├── structured_ingestion_service.py   # Structured data → database
│   │   │   └── unstructured_ingestion_service.py # Unstructured → ChromaDB
│   │   │
│   │   ├── structured/          # NEW: Structured data query services
│   │   │   ├── __init__.py
│   │   │   ├── structured_query_service.py  # SQL-like queries (SUM, AVG, MAX, etc.)
│   │   │   └── aggregation_service.py       # High-level financial aggregations
│   │   │
│   │   └── ai/                  # NEW: Query classification and routing
│   │       ├── __init__.py
│   │       ├── query_classifier.py  # Classifies questions as STRUCTURED/UNSTRUCTURED/HYBRID
│   │       └── query_router.py      # Routes questions to appropriate pipeline
│   │
│   └── tests/                   # pytest + hypothesis property-based tests
│       ├── test_structured_query.py  # NEW: Tests for structured data pipeline
│       └── ...
│
├── frontend/
│   └── ... (unchanged)
│
├── mock_data/                   # Sample data files for testing
│
└── .kiro/
    ├── steering/
    │   └── project-context.md   # Kiro steering file
    └── specs/                   # Spec documents (requirements, design, tasks)
```

---

## How to Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running on localhost:5432
- Groq API key

### Backend
```bash
cd backend
pip install -r requirements.txt
# Create the database "project_intelligence_hub" in PostgreSQL first
python -m db.init_db
# Configure .env with your Groq API key
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

- **Dual-Pipeline Architecture**: Structured data → SQL queries; Unstructured → RAG. Never mix approaches.
- **Type-Preserving Ingestion**: Excel numeric values stored as floats, not strings. Enables accurate aggregation.
- **Query Classification**: Rule-based classifier routes questions to appropriate pipeline before any LLM call.
- **Summary Row Detection**: Explicit TOTAL/PORTFOLIO TOTAL rows detected and stored separately.
- **Single-project model**: Only one project exists at a time. Simplifies the POC.
- **ChromaDB collection**: Named `project_knowledge`, uses cosine similarity, persistent storage at `./chroma_data`.
- **Chunking**: Legacy 900 chars for unstructured. Semantic chunking (500-800 tokens) for new documents.
- **Embedding**: Uses sentence-transformers (all-MiniLM-L6-v2, 384 dimensions).
- **File processing pipeline**:
  - Upload → Classify (structured/unstructured)
  - Structured: Extract → Store in SQL → Index summary for search
  - Unstructured: Extract → Chunk → Embed → ChromaDB
- **Relevance filtering**: Only use chunks with cosine distance < 0.7 (relevance > 0.3).
- **Agentic RAG**: Strands agent chooses structured or unstructured tools based on question type.
- **Anti-hallucination**: For numerical questions, return exact database values, never LLM estimates.
- **Error format**: All API errors return `{"detail": "human-readable message"}` with appropriate HTTP status codes.
- **File categories**: Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other.
- **Supported file types**: PDF, XLSX, XLS, CSV, JSON (max 50MB).
- **No tables in chat output**: System prompt forbids markdown tables — uses lists instead.

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/project | Create project |
| GET | /api/project | Get current project |
| DELETE | /api/project/reset | Full reset |
| POST | /api/files/upload | Upload file (multipart, max 50MB) |
| GET | /api/files | List all files |
| GET | /api/files/{id} | Download file |
| DELETE | /api/files/{id} | Delete file + chunks |
| GET | /api/dashboard | Dashboard stats |
| POST | /api/chat | AI Q&A (Strands Agent) |
| POST | /api/visualize | Generate chart config |

---

## Environment Variables

The `.env` file in `backend/` should contain:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/project_intelligence_hub

# Groq API (LLM)
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b

# Note: compound-beta and llama models are auto-fallback to gpt-oss-120b
# due to LiteLLM compatibility issues

# PII Tokenization (optional)
PII_TOKENIZATION_ENABLED=true
AZURE_PII_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_PII_API_KEY=your-pii-api-key
AZURE_PII_API_VERSION=2024-11-15-preview
PII_CONFIDENCE_THRESHOLD=0.8
```

---

## Strands Agent Configuration

The chat endpoint (`api/chat.py`) uses `StrandsRAGAgent` from `services/strands_agent.py`.

### Model Selection Logic
```python
# Reads GROQ_MODEL from env, falls back to gpt-oss-120b
# Auto-converts: compound-beta, compound, llama-3.3, llama-3.1 → openai/gpt-oss-120b
# Final model ID format: "groq/openai/gpt-oss-120b"
```

### Agent Tools
1. **search_knowledge_base(query, n_results)** — Vector search with relevance filtering
2. **get_files_by_category(category)** — List files in a category
3. **list_all_files()** — Summary of all uploaded files
4. **get_knowledge_base_stats()** — Total files, chunks, vectors

### System Prompt Rules
- Never use markdown tables (pipes `|`)
- Use numbered lists with sub-bullets instead
- Tool responses are internal — transform to natural language
- Always cite source files
- Professional tone suitable for business applications

---

## Chat Request Flow

```
Frontend (AIChatScreen.tsx)
  └── POST /api/chat { question: "..." }
        │
Backend (api/chat.py)
  └── StrandsRAGAgent().query(question)
        │
strands_agent.py
  ├── _build_agent() — Creates LiteLLM model + Strands Agent
  ├── Agent calls tools autonomously:
  │     ├── search_knowledge_base() → embeddings.py → chroma_client.py
  │     ├── list_all_files() → database.py
  │     └── get_files_by_category() → database.py
  └── Returns { answer: "...", sources: [...] }
        │
Frontend renders markdown response
```

---

## Legacy Code (Not Used)

- `services/rag_pipeline.py` — Original one-shot RAG, replaced by Strands Agent
- `services/azure_rag_agent.py` — Alternative Azure implementation
- `components/NavigationBar.tsx` — Replaced by Sidebar.tsx

---

## Git Repository

- **Remote**: https://github.com/GauravByteridge/technology-transformation-intelligence
- **Branch**: master
- **Note**: `.env` file is NOT committed (contains API keys)
