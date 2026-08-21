"""
Project Intelligence Hub - FastAPI Backend

A RAG-based POC application for project data analysis with AI-powered
chatbot and visualization capabilities.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env file before anything else

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI application
app = FastAPI(
    title="Project Intelligence Hub",
    description="RAG-based POC application for uploading files, processing data, and AI-powered Q&A",
    version="1.0.0",
)

# Configure CORS for frontend communication
# Allow all origins for POC simplicity (no authentication required)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for POC
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# --- Router Includes ---
from api.project import router as project_router
from api.files import router as files_router
from api.dashboard import router as dashboard_router
from api.chat import router as chat_router

app.include_router(project_router, prefix="/api", tags=["project"])
app.include_router(files_router, prefix="/api", tags=["files"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(chat_router, prefix="/api", tags=["chat"])

# Routers will be registered here as they are implemented in subsequent tasks.
# from api.visualize import router as visualize_router
# app.include_router(visualize_router, prefix="/api", tags=["visualize"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Project Intelligence Hub API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}
