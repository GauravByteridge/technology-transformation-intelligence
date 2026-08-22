"""
Query history and saved query request/response schemas.

Defines Pydantic models for query history (append-only) and saved query CRUD.
NOTE: No update schema exists for query_history — records are append-only by design.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class QueryHistoryCreate(BaseModel):
    """Request schema for creating a query history record."""

    query_id: UUID = Field(description="Unique query identifier from the AI execution")
    conversation_id: UUID = Field(description="Conversation this query belongs to")
    project_id: UUID = Field(description="Project this query belongs to")
    question: str = Field(min_length=1, description="The user's question")
    response: dict | None = Field(default=None, description="Structured AI response")
    tools_invoked: list | None = Field(default=None, description="List of tools used during execution")
    sources_consulted: list | None = Field(default=None, description="List of sources referenced")
    is_partial: bool = Field(default=False, description="Whether the response is partial/streaming")
    llm_provider: str | None = Field(default=None, description="LLM provider used")
    llm_model: str | None = Field(default=None, description="LLM model identifier")
    prompt_version: str | None = Field(default=None, description="Version of the prompt template used")
    duration_ms: int | None = Field(default=None, description="Query execution duration in milliseconds")


class QueryHistoryResponse(BaseModel):
    """Response schema for a query history record."""

    id: UUID
    query_id: UUID
    conversation_id: UUID
    project_id: UUID
    question: str
    response: dict | None = None
    tools_invoked: list | None = None
    sources_consulted: list | None = None
    is_partial: bool
    llm_provider: str | None = None
    llm_model: str | None = None
    prompt_version: str | None = None
    duration_ms: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SavedQueryCreate(BaseModel):
    """Request schema for creating a saved query."""

    project_id: UUID = Field(description="Project this saved query belongs to")
    title: str = Field(min_length=1, max_length=500, description="Title for the saved query")
    question: str = Field(min_length=1, description="The saved question text")


class SavedQueryResponse(BaseModel):
    """Response schema for a saved query."""

    id: UUID
    user_id: UUID
    project_id: UUID
    title: str
    question: str
    created_at: datetime

    model_config = {"from_attributes": True}
