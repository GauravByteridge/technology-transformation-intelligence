# Project Intelligence Hub — Steering Guide

## Project Overview

This is a RAG-based (Retrieval-Augmented Generation) proof-of-concept application for document analysis and AI-powered Q&A. It's a lightweight POC — no auth, no multi-user, one project at a time.

## Tech Stack

### Backend (Python/FastAPI)
- **Framework**: FastAPI with SQLAlchemy ORM
- **Databases**: PostgreSQL (metadata), ChromaDB (vectors)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, 384 dimensions)
- **LLM**: Groq compound-beta via Strands Agents SDK
- **File Processing**: PyMuPDF (PDF), pandas (Excel/CSV/JSON)
- **Testing**: pytest + hypothesis

### Frontend (React/TypeScript)
- **Framework**: React 19, TypeScript, Vite
- **Charts**: Recharts
- **HTTP Client**: Axios
- **Routing**: React Router v7
- **Dev Server**: Port 5173, proxies `/api` to backend port 8000

## Key Files

### Backend Entry Points
- `backend/main.py` — FastAPI app, CORS, router registration
- `backend/api/chat.py` — Chat endpoint using Strands RAG Agent
- `backend/services/strands_agent.py` — Strands agent with 4 tools

### Frontend Entry Points
- `frontend/src/main.tsx` — React entry point
- `frontend/src/App.tsx` — Router configuration
- `frontend/src/api/client.ts` — Axios API client

## Development Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Code Conventions

1. **API Errors**: Return `{"detail": "message"}` with appropriate HTTP status
2. **Chunking**: 900 chars default, 100 char overlap
3. **Relevance**: Filter chunks with cosine distance < 0.7
4. **File Categories**: Project Costs, Burndown, Audit, IT Controls, Remediation, Business Intelligence, Internal Data, Other
5. **Supported Files**: PDF, XLSX, XLS, CSV, JSON

## Environment Variables

Backend `.env` requires:
- `DATABASE_URL` — PostgreSQL connection string
- `GROQ_API_KEY` — Groq API key
- `GROQ_MODEL` — Currently `compound-beta`

## Reference

See `#[[file:CONTEXT.md]]` for detailed architecture and API documentation.
