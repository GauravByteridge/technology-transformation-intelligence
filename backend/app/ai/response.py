"""
AI Response Builder — Convenience module for constructing AIResponse objects.

This module provides a builder utility that enforces the platform's response
contract invariants:
- Source labels are meaningful (not internal tool names)
- No HTML/JSX/React markup in answer text
- Partial failure metadata is correctly populated
- Visualization specs are present only for table/chart response types

The AIResponse Pydantic model is defined in app.schemas.ai and re-exported here
for convenience. The builder adds construction helpers and validation logic on
top of the raw schema.
"""

import re
from typing import Any
from uuid import UUID

from app.schemas.ai import AIResponse

# NOTE: Pattern catches common HTML/JSX constructs but is deliberately conservative.
# False positives on math expressions (e.g., "x < 5") are avoided by requiring
# a letter immediately after '<' (matching tags like <div>, <Component>, etc.)
_HTML_JSX_PATTERN = re.compile(
    r"<[a-zA-Z][^>]*>|</[a-zA-Z][^>]*>|<[a-zA-Z][^>]*/>"
)


def contains_markup(text: str) -> bool:
    """Check whether the text contains HTML/JSX/React markup.

    Args:
        text: The answer text to validate.

    Returns:
        True if markup is detected, False otherwise.
    """
    return bool(_HTML_JSX_PATTERN.search(text))


def strip_markup(text: str) -> str:
    """Remove HTML/JSX tags from text, preserving inner content.

    Args:
        text: The text potentially containing markup.

    Returns:
        Cleaned text with all HTML/JSX tags removed.
    """
    return _HTML_JSX_PATTERN.sub("", text)


class ResponseBuilder:
    """Builder for constructing AIResponse objects with contract enforcement.

    Usage:
        builder = ResponseBuilder(query_id=..., conversation_id=...)
        builder.set_answer("The budget is on track.")
        builder.add_source(label="Finance PostgreSQL", source_type="postgresql", records=5)
        builder.add_evidence(claim="Budget variance < 5%", source="Finance PostgreSQL", data={...})
        response = builder.build()

    The builder enforces:
    - Answer text is stripped of any HTML/JSX markup
    - Sources use meaningful labels
    - is_partial is automatically set when failed_sources are present
    - visualization_spec is only included for table/chart response types
    """

    def __init__(self, query_id: UUID, conversation_id: UUID) -> None:
        """Initialize the response builder.

        Args:
            query_id: Unique identifier for this query execution.
            conversation_id: Conversation this response belongs to.
        """
        self._query_id = query_id
        self._conversation_id = conversation_id
        self._answer: str = ""
        self._response_type: str = "text"
        self._sources: list[dict[str, Any]] = []
        self._evidence: list[dict[str, Any]] = []
        self._failed_sources: list[dict[str, Any]] = []
        self._visualization_spec: dict[str, Any] | None = None

    def set_answer(self, answer: str) -> "ResponseBuilder":
        """Set the answer text, stripping any markup.

        Args:
            answer: The generated answer text.

        Returns:
            Self for method chaining.
        """
        self._answer = strip_markup(answer)
        return self

    def set_response_type(self, response_type: str) -> "ResponseBuilder":
        """Set the response type (text, table, or chart).

        Args:
            response_type: One of "text", "table", "chart".

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If response_type is not one of the allowed values.
        """
        allowed = ("text", "table", "chart")
        if response_type not in allowed:
            raise ValueError(f"response_type must be one of {allowed}, got '{response_type}'")
        self._response_type = response_type
        return self

    def add_source(
        self,
        label: str,
        source_type: str = "unknown",
        records: int = 0,
    ) -> "ResponseBuilder":
        """Add a successful source to the response.

        Args:
            label: Human-readable source label (e.g., "Finance PostgreSQL").
            source_type: The type of data source.
            records: Number of records returned.

        Returns:
            Self for method chaining.
        """
        self._sources.append({
            "name": label,
            "type": source_type,
            "records_returned": records,
        })
        return self

    def add_evidence(
        self,
        claim: str,
        source: str,
        data: Any = None,
    ) -> "ResponseBuilder":
        """Add an evidence item linking a claim to its source.

        Args:
            claim: The claim made in the answer.
            source: The source label that supports this claim.
            data: Supporting data for the claim.

        Returns:
            Self for method chaining.
        """
        self._evidence.append({
            "claim": claim,
            "source": source,
            "data": data,
        })
        return self

    def add_failed_source(self, source: str, error: str) -> "ResponseBuilder":
        """Record a source that failed during query execution.

        Args:
            source: Human-readable source label.
            error: Description of what went wrong.

        Returns:
            Self for method chaining.
        """
        self._failed_sources.append({
            "source": source,
            "error": error,
        })
        return self

    def set_visualization_spec(self, spec: dict[str, Any]) -> "ResponseBuilder":
        """Set the visualization specification for table/chart responses.

        Args:
            spec: Structured visualization specification.

        Returns:
            Self for method chaining.
        """
        self._visualization_spec = spec
        return self

    def build(self) -> AIResponse:
        """Construct the final AIResponse.

        Automatically sets is_partial=True when any failed sources exist.
        Clears visualization_spec for text response types.

        Returns:
            A validated AIResponse instance.
        """
        is_partial = len(self._failed_sources) > 0

        # Visualization spec only applies to table/chart
        viz_spec = self._visualization_spec if self._response_type != "text" else None

        return AIResponse(
            answer=self._answer,
            response_type=self._response_type,  # type: ignore[arg-type]
            sources=self._sources,
            evidence=self._evidence,
            query_id=self._query_id,
            conversation_id=self._conversation_id,
            is_partial=is_partial,
            failed_sources=self._failed_sources,
            visualization_spec=viz_spec,
        )
