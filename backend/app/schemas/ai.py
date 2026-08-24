"""
AI query request and response schemas.

Defines the structured contract for AI query endpoints,
matching the AI response contract specified in Requirement 11.
"""

import re
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Pattern to detect HTML/JSX/React markup in answer text.
# Matches opening tags (<div>), closing tags (</div>), and self-closing tags (<br/>).
_HTML_JSX_PATTERN = re.compile(
    r"<[a-zA-Z][^>]*>|</[a-zA-Z][^>]*>|<[a-zA-Z][^>]*/>"
)


class AIQueryRequest(BaseModel):
    """Request schema for submitting an AI query."""

    question: str = Field(min_length=1, max_length=5000, description="The user's question")
    project_id: UUID | None = Field(default=None, description="Project context for scoping the query (optional for portfolio-level queries)")
    conversation_id: UUID | None = Field(
        default=None,
        description="Existing conversation ID to continue, or None to start a new conversation",
    )


class AIResponse(BaseModel):
    """
    Structured AI response matching the platform's AI response contract.

    The frontend decides how to render based on response_type and
    visualization_spec — this schema carries data, not presentation.
    """

    answer: str = Field(description="Generated answer text")
    response_type: Literal["text", "table", "chart"] = Field(
        description="Indicates how the frontend should render the response"
    )
    sources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Data sources consulted (with meaningful labels, not internal tool names)",
    )
    evidence: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Evidence linking claims to retrieved records",
    )
    query_id: UUID = Field(description="Unique identifier for this query execution")
    conversation_id: UUID = Field(description="Conversation this response belongs to")
    is_partial: bool = Field(
        default=False,
        description="True if some sources failed and the answer is based on partial data",
    )
    failed_sources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Sources that were unavailable during query execution",
    )
    visualization_spec: dict[str, Any] | None = Field(
        default=None,
        description="Structured chart/table specification (present only for table/chart response_type)",
    )

    # Phase 8: Cross-Source Intelligence fields
    lineage_trace: dict[str, Any] | None = Field(
        default=None,
        description="Full execution lineage trace from question to answer",
    )
    groundedness: list[dict[str, Any]] | None = Field(
        default=None,
        description="Groundedness classifications for claims in the answer",
    )
    sources_consulted: list[dict[str, Any]] | None = Field(
        default=None,
        description="Detailed source references with semantic metadata and record counts",
    )

    model_config = {"from_attributes": True}

    @field_validator("answer")
    @classmethod
    def answer_must_not_contain_markup(cls, value: str) -> str:
        """Ensure answer text contains no HTML/JSX/React markup (Requirement 11.3)."""
        if _HTML_JSX_PATTERN.search(value):
            raise ValueError(
                "AI response answer must not contain HTML/JSX/React markup. "
                "Use structured visualization_spec for rendering instructions."
            )
        return value
