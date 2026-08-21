"""
Chat API endpoint for the Project Intelligence Hub.

Handles AI-powered Q&A queries using the Strands agent to answer
questions based on uploaded project data.

The Strands agent can:
- Perform multiple iterative searches
- Filter by category
- Reason step-by-step before answering
- Cite sources properly
"""

import logging

from fastapi import APIRouter, HTTPException, status

from models.schemas import ChatRequest, ChatResponse
from services.strands_agent import StrandsRAGAgent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Process a chat question using the Strands RAG agent.

    - Validates the question is not empty or whitespace-only.
    - Instantiates StrandsRAGAgent which uses tools to search the
      knowledge base, filter by category, and reason before answering.
    - The agent can make multiple searches if needed for comprehensive answers.
    - If the AI service fails, returns 503 Service Unavailable.

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
        agent = StrandsRAGAgent()
        result = agent.query(question=request.question.strip())
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"],
        )
    except RuntimeError as e:
        logger.error("Strands agent error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unavailable. Please try again later.",
        )
