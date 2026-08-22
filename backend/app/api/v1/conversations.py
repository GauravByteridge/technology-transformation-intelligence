"""
Conversation API route handlers.

Thin route layer: validates input, delegates to ConversationService, returns response.
No business logic, no direct database access.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_conversation_service
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.services.conversation_service import ConversationService

router = APIRouter()


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
    responses={
        404: {"description": "Project not found"},
        422: {"description": "Validation error"},
    },
)
async def create_conversation(
    payload: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """Create a new conversation scoped to a project."""
    result = await service.create_conversation(
        project_id=payload.project_id,
        title=payload.title,
    )
    return ConversationResponse(**result)


@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="List conversations for a project",
)
async def list_conversations(
    project_id: UUID = Query(description="Filter conversations by project ID"),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    """List all conversations for the given project."""
    results = await service.list_by_project(project_id)
    return [ConversationResponse(**r) for r in results]


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get a conversation with messages",
    responses={
        404: {"description": "Conversation not found"},
        422: {"description": "Invalid conversation ID format"},
    },
)
async def get_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    """Retrieve a conversation including its messages."""
    result = await service.get_conversation(conversation_id)
    return ConversationResponse(**result)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a conversation",
    responses={
        404: {"description": "Conversation not found"},
        422: {"description": "Validation error"},
    },
)
async def add_message(
    conversation_id: UUID,
    payload: MessageCreate,
    service: ConversationService = Depends(get_conversation_service),
) -> MessageResponse:
    """Append a message to an existing conversation."""
    result = await service.add_message(
        conversation_id=conversation_id,
        role=payload.role,
        content=payload.content,
        metadata=payload.metadata,
    )
    return MessageResponse(**result)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    responses={404: {"description": "Conversation not found"}},
)
async def delete_conversation(
    conversation_id: UUID,
    service: ConversationService = Depends(get_conversation_service),
) -> None:
    """Delete a conversation and its messages."""
    await service.delete_conversation(conversation_id)
