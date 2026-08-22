"""
AI domain error types.

Raised by AI services, providers, and orchestration when
AI-related operations fail.
"""

from app.errors.base import AppError, ErrorCategory


class ProviderResolutionError(AppError):
    """Raised when a requested LLM/embedding provider cannot be resolved."""

    def __init__(self, provider_name: str, supported_providers: list[str]) -> None:
        supported = ", ".join(supported_providers) if supported_providers else "none"
        super().__init__(
            error_code="PROVIDER_RESOLUTION_ERROR",
            message=f"Provider '{provider_name}' is not supported. Supported: {supported}",
            domain="ai",
            category=ErrorCategory.VALIDATION,
            detail=None,
        )
        self.provider_name = provider_name
        self.supported_providers = supported_providers


class ProviderCredentialError(AppError):
    """Raised when required provider credentials are missing or invalid."""

    def __init__(self, provider_name: str, missing_credentials: list[str]) -> None:
        missing = ", ".join(missing_credentials)
        super().__init__(
            error_code="PROVIDER_CREDENTIAL_ERROR",
            message=f"Provider '{provider_name}' is missing required credentials: {missing}",
            domain="ai",
            category=ErrorCategory.VALIDATION,
            detail=None,
        )
        self.provider_name = provider_name
        self.missing_credentials = missing_credentials


class AIQueryError(AppError):
    """Raised when an AI query execution fails."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(
            error_code="AI_QUERY_ERROR",
            message=message,
            domain="ai",
            category=ErrorCategory.EXTERNAL,
            detail=detail,
        )
