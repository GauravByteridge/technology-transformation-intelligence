"""
Conversation and message request/response schemas.

Defines Pydantic models for conversation CRUD and message append operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """Request schema for adding a message to a conversation."""

    role: str = Field(min_length=1, max_length=50, description="Message role (e.g., user, assistant, system)")
    content: str = Field(min_length=1, description="Message content")
    metadata: dict | None = Field(default=None, description="Optional metadata for the message")


class MessageResponse(BaseModel):
    """Response schema for a message."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    metadata: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    """Request schema for creating a conversation."""

    project_id: UUID = Field(description="Project this conversation belongs to")
    title: str | None = Field(default=None, max_length=500, description="Optional conversation title")


class ConversationResponse(BaseModel):
    """Response schema for a conversation with its messages."""

    id: UUID
    project_id: UUID
    user_id: UUID
    title: str | None = None
    messages: list[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
