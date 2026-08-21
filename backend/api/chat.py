"""
Chat API endpoint for the Project Intelligence Hub.

Handles AI-powered Q&A queries using the RAG pipeline to answer
questions based on uploaded project data.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from models.schemas import ChatRequest, ChatResponse
from services.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Process a chat question using the RAG pipeline.

    - Validates the question is not empty or whitespace-only.
    - Instantiates RAGPipeline and calls query() to retrieve relevant
      context and generate an answer via the Groq API.
    - If no relevant chunks are found, the RAGPipeline returns an
      appropriate message asking the user to upload relevant files.
    - If the Groq API fails, returns 503 Service Unavailable.

    Returns:
        ChatResponse with the generated answer and list of source file names.
    """
    # Validate question is not empty or whitespace-only
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    try:
        pipeline = RAGPipeline()
        response = pipeline.query(question=request.question.strip())
        return response
    except RuntimeError as e:
        logger.error("RAG pipeline error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unavailable. Please try again later.",
        )
