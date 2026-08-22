"""
Conversation domain error types.

Raised by conversation services when conversation-related
operations fail.
"""

from app.errors.base import AppError, ErrorCategory


class ConversationNotFoundError(AppError):
    """Raised when a requested conversation does not exist."""

    def __init__(self, conversation_id: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="CONVERSATION_NOT_FOUND",
            message=f"Conversation '{conversation_id}' not found",
            domain="conversation",
            category=ErrorCategory.NOT_FOUND,
            detail=detail,
        )
