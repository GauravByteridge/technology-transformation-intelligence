"""
Application configuration loaded from environment variables.

Requirement levels follow the .env.example documentation:
- REQUIRED: Must be set for any mode
- OPTIONAL: Has sensible defaults
- CONDITIONAL: Needed only when specific features/providers are enabled

Validates at startup that all required/conditional variables are present
based on the active configuration (Demo vs Live mode, selected providers).
"""

from typing import Literal
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file's directory (backend root)
# settings.py is at backend/app/config/settings.py → .parent.parent.parent = backend/
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # REQUIRED — Core Application
    # =========================================================================

    app_db_url: str
    secret_key: str
    fernet_key: str = ""

    # =========================================================================
    # OPTIONAL — Defaults Provided
    # =========================================================================

    demo_mode: bool = True
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    cors_origins: str = "http://localhost:5173"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # =========================================================================
    # CONDITIONAL — LLM Provider (REQUIRED when DEMO_MODE=false)
    # =========================================================================

    llm_provider: Literal["azure_foundry", "azure_openai", "groq", "mock"] | None = None

    # Azure AI Foundry
    azure_foundry_api_key: str | None = None
    azure_foundry_endpoint: str | None = None
    azure_foundry_model: str | None = None

    # Azure OpenAI
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-02-01"

    # Groq
    groq_api_key: str | None = None
    groq_model: str = "llama-3.1-70b-versatile"

    # =========================================================================
    # CONDITIONAL — RAG / Embeddings (REQUIRED when DEMO_MODE=false)
    # =========================================================================

    rag_db_url: str | None = None
    embedding_provider: Literal["azure_openai", "azure_foundry", "sentence_transformers", "mock"] | None = None
    embedding_model: str | None = None
    embedding_dimension: int = 1536

    # =========================================================================
    # CONDITIONAL — External Data Sources
    # =========================================================================

    mongodb_enabled: bool = False
    mongodb_url: str | None = None

    # Jira Cloud integration
    jira_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str = "SCRUM"
    jira_provider: str = "all"  # "rest_api" | "rovo_mcp_v1" | "rovo_mcp_v2" | "all"
    rovo_mcp_v1_token: str | None = None
    rovo_mcp_v2_token: str | None = None
    rovo_mcp_api_token: str | None = None  # Legacy fallback (maps to v1)

    # Gmail integration
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/gmail/auth/callback"

    # Outlook integration (delegated OAuth authorization-code flow via an
    # existing Microsoft Entra App Registration — delegated Graph Mail.Read).
    # The client secret is used server-side only and is never logged or
    # returned to the frontend.
    # `microsoft_tenant_id` accepts "common" (personal + work/school),
    # "organizations", "consumers", or a specific tenant ID.
    microsoft_tenant_id: str | None = "common"
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    microsoft_redirect_uri: str = "http://localhost:8000/api/v1/outlook/auth/callback"

    # =========================================================================
    # Computed Properties
    # =========================================================================

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_live_mode(self) -> bool:
        """True when running in Live Mode (DEMO_MODE=false)."""
        return not self.demo_mode

    # =========================================================================
    # Validators
    # =========================================================================

    @field_validator("app_db_url")
    @classmethod
    def validate_app_db_url(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("APP_DB_URL is required and cannot be empty")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SECRET_KEY is required and cannot be empty")
        return v


def validate_live_mode_settings(settings: Settings) -> None:
    """
    Validate that Live Mode has all required conditional configuration.

    In Demo Mode, LLM/embedding/RAG credentials are NOT required because
    live providers are not used. In Live Mode, the selected provider's
    credentials must all be present.

    Raises ValueError with a descriptive message if validation fails.
    """
    if settings.demo_mode:
        # Demo Mode does not require LLM/embedding/RAG credentials
        return

    errors: list[str] = []

    # Live Mode requires LLM_PROVIDER
    if not settings.llm_provider:
        errors.append("LLM_PROVIDER is required in Live Mode (DEMO_MODE=false)")
    else:
        _validate_llm_provider_credentials(settings, errors)

    # Live Mode requires RAG configuration
    if not settings.rag_db_url:
        errors.append("RAG_DB_URL is required in Live Mode")
    if not settings.embedding_provider:
        errors.append("EMBEDDING_PROVIDER is required in Live Mode")
    if not settings.embedding_model:
        errors.append("EMBEDDING_MODEL is required in Live Mode")

    # Validate embedding dimension is a known model dimension
    _validate_embedding_dimension(settings, errors)

    # Conditional: MongoDB
    if settings.mongodb_enabled and not settings.mongodb_url:
        errors.append("MONGODB_URL is required when MONGODB_ENABLED=true")

    if errors:
        raise ValueError(
            "Configuration validation failed for Live Mode:\n  - " + "\n  - ".join(errors)
        )


def _validate_llm_provider_credentials(settings: Settings, errors: list[str]) -> None:
    """Check that the selected LLM provider has its required credentials."""
    provider = settings.llm_provider

    if provider == "azure_foundry":
        if not settings.azure_foundry_api_key:
            errors.append("AZURE_FOUNDRY_API_KEY is required for provider 'azure_foundry'")
        if not settings.azure_foundry_endpoint:
            errors.append("AZURE_FOUNDRY_ENDPOINT is required for provider 'azure_foundry'")
        if not settings.azure_foundry_model:
            errors.append("AZURE_FOUNDRY_MODEL is required for provider 'azure_foundry'")

    elif provider == "azure_openai":
        if not settings.azure_openai_api_key:
            errors.append("AZURE_OPENAI_API_KEY is required for provider 'azure_openai'")
        if not settings.azure_openai_endpoint:
            errors.append("AZURE_OPENAI_ENDPOINT is required for provider 'azure_openai'")
        if not settings.azure_openai_deployment:
            errors.append("AZURE_OPENAI_DEPLOYMENT is required for provider 'azure_openai'")

    elif provider == "groq":
        if not settings.groq_api_key:
            errors.append("GROQ_API_KEY is required for provider 'groq'")


# Known embedding model dimensions supported by common providers
VALID_EMBEDDING_DIMENSIONS: set[int] = {384, 512, 768, 1024, 1536, 3072}


def _validate_embedding_dimension(settings: Settings, errors: list[str]) -> None:
    """
    Validate that EMBEDDING_DIMENSION is a positive integer matching
    known model dimensions.

    In Live Mode, a mismatch between EMBEDDING_DIMENSION and the RAG_DB
    vector column would cause silent data corruption or query failures.
    This validation catches misconfiguration at startup.

    NOTE: Full DB column dimension check requires a database connection,
    which is not available at settings-validation time. This validates
    against known model dimensions as a static check.
    """
    dimension = settings.embedding_dimension

    if dimension <= 0:
        errors.append(
            f"EMBEDDING_DIMENSION must be a positive integer, got: {dimension}"
        )
    elif dimension not in VALID_EMBEDDING_DIMENSIONS:
        valid_dims = ", ".join(str(d) for d in sorted(VALID_EMBEDDING_DIMENSIONS))
        errors.append(
            f"EMBEDDING_DIMENSION mismatch: configured={dimension} is not a recognized "
            f"embedding model dimension. Valid dimensions: {valid_dims}"
        )
