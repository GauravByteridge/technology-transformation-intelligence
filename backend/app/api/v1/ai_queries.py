"""
AI query API route handlers.

Thin route layer: validates input, delegates to AIService, returns response.
No business logic, no direct database access, no AI prompt construction.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Request

from app.ai.service import AIService
from app.dependencies import get_ai_service
from app.schemas.ai import AIQueryRequest, AIResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=AIResponse,
    summary="Submit an AI query",
    responses={
        422: {"description": "Invalid request body"},
    },
)
async def submit_ai_query(
    body: AIQueryRequest,
    request: Request,
    ai_service: AIService = Depends(get_ai_service),
) -> AIResponse:
    """
    Submit a natural-language query to the AI orchestration layer.

    Generates a unique query_id, delegates to AIService.execute_query(),
    and returns the structured AI response with sources and evidence.

    Flow: API → AIService → Agent → Tools → Domain Services → Data Sources
    """
    request_id = getattr(request.state, "request_id", "unknown")
    query_id = uuid.uuid4()

    # Use provided conversation_id or create a new one
    conversation_id = body.conversation_id or uuid.uuid4()

    logger.info(
        "ai_query_received",
        extra={
            "query_id": str(query_id),
            "conversation_id": str(conversation_id),
            "project_id": str(body.project_id),
            "request_id": request_id,
        },
    )

    response = await ai_service.execute_query(
        question=body.question,
        project_id=body.project_id,
        query_id=query_id,
        conversation_id=conversation_id,
    )

    return response
