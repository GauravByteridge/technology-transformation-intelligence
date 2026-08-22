"""
AI Query Trace — Structured trace recording for AI query execution.

Captures the full execution trace for any AI query, enabling:
- Debugging: trace from question through tools to final answer
- Audit: record which sources were consulted and what evidence was found
- Observability: duration, partial failures, provider/model metadata

Security Invariant:
    Trace records NEVER contain credentials, connection strings, or API keys.
    All sensitive fields are excluded by design — the dataclass only captures
    operational metadata and business-level identifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


# Patterns that indicate sensitive values — used to scrub accidental leakage
_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(connection[_-]?string|conn[_-]?str)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(token|bearer)\s*[:=]\s*\S+"),
    re.compile(r"postgresql(\+\w+)?://\S+:\S+@"),
    re.compile(r"mongodb(\+srv)?://\S+:\S+@"),
]

REDACTED = "[REDACTED]"


@dataclass
class ToolInvocationTrace:
    """Trace record for a single tool invocation within a query.

    Attributes:
        tool_name: Business-intent name of the tool.
        source_id: Identifier of the data source queried (if applicable).
        execution_status: Outcome — "success" or "failed".
        duration_ms: Time taken for the tool invocation.
        error: Error description if the tool failed, None otherwise.
        records_returned: Number of records returned by the tool.
    """

    tool_name: str
    source_id: str | None = None
    execution_status: str = "success"
    duration_ms: int = 0
    error: str | None = None
    records_returned: int = 0


@dataclass
class QueryTrace:
    """Complete structured trace for an AI query execution.

    Captures everything needed to reconstruct the full execution path
    from question through tools to final answer.

    Attributes:
        query_id: Unique identifier for this query execution.
        conversation_id: Conversation this query belongs to.
        question: The user's original question.
        project_id: Project context used for scoping.
        tools_invoked: List of tool invocation trace records.
        sources_queried: List of source identifiers consulted.
        evidence_count: Number of evidence items retrieved.
        failures: List of tool failure descriptions.
        is_partial: Whether the answer is based on incomplete data.
        provider: LLM provider used for text generation.
        model: Specific model used for text generation.
        duration_ms: Total query execution time in milliseconds.
    """

    query_id: UUID
    conversation_id: UUID
    question: str
    project_id: UUID
    tools_invoked: list[ToolInvocationTrace] = field(default_factory=list)
    sources_queried: list[str] = field(default_factory=list)
    evidence_count: int = 0
    failures: list[str] = field(default_factory=list)
    is_partial: bool = False
    provider: str = "unknown"
    model: str = "unknown"
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the trace to a dictionary for logging/storage.

        Returns a sanitized dictionary representation with no sensitive data.
        """
        return {
            "query_id": str(self.query_id),
            "conversation_id": str(self.conversation_id),
            "question_length": len(self.question),
            "project_id": str(self.project_id),
            "tools_invoked": [
                {
                    "tool_name": t.tool_name,
                    "source_id": t.source_id,
                    "execution_status": t.execution_status,
                    "duration_ms": t.duration_ms,
                    "error": t.error,
                    "records_returned": t.records_returned,
                }
                for t in self.tools_invoked
            ],
            "sources_queried": self.sources_queried,
            "evidence_count": self.evidence_count,
            "failures": self.failures,
            "is_partial": self.is_partial,
            "provider": self.provider,
            "model": self.model,
            "duration_ms": self.duration_ms,
        }


def contains_sensitive_value(text: str) -> bool:
    """Check whether a string contains patterns that look like credentials.

    Used as a safety check to prevent accidental logging of secrets.

    Args:
        text: The string to inspect.

    Returns:
        True if any sensitive pattern matches.
    """
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def sanitize_log_value(value: str) -> str:
    """Redact sensitive patterns from a string before logging.

    Args:
        value: The raw string that may contain credentials.

    Returns:
        The string with sensitive patterns replaced by [REDACTED].
    """
    result = value
    for pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub(REDACTED, result)
    return result
