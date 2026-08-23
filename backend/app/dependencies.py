"""
Composition Root — Dependency Injection Wiring

All services receive their dependencies via constructor injection from here.
This module is the single place where the dependency graph is assembled,
making it explicit and inspectable.

Dependency Graph (Phase 0):
──────────────────────────────────────────────────────────────────────────
  Settings (singleton, loaded at startup)
      │
      ├── App_DB Session Factory (async, from APP_DB_URL)
      │       │
      │       └── ProjectRepository (database access for projects)
      │               │
      │               └── ProjectService (business logic)
      │
      ├── RAG_DB Session Factory (async, from RAG_DB_URL — Live Mode only)
      │
      ├── ConnectorRegistry (singleton, pre-registered at startup)
      │       ├── "postgresql" → PostgresConnector
      │       └── "mongodb"    → MongoDBConnector
      │
      └── ProviderRegistry (singleton, pre-registered at startup)
              ├── Text: "azure_foundry", "azure_openai", "groq", "mock"
              └── Embedding: "azure_openai", "azure_foundry", "mock"
──────────────────────────────────────────────────────────────────────────

# =============================================================================
# SECURITY INVARIANTS
# =============================================================================
#
# 1. ALL SECRETS COME FROM ENVIRONMENT VARIABLES ONLY
#    - The Settings class (pydantic-settings) loads secrets exclusively from
#      env vars. No config files, no CLI args, no hard-coded values.
#    - If a required secret is missing, the application refuses to start.
#
# 2. NO CREDENTIALS IN CODE, LOGS, OR AI AGENT CONTEXT
#    - Database URLs, API keys, and tokens are never logged (structlog is
#      configured to redact sensitive fields).
#    - Credentials never appear in API responses or error messages.
#    - The AI agent (Strands) never receives connection strings or auth tokens
#      in prompts, tool configs, or function parameters.
#
# 3. EXTERNAL DATA SOURCES ARE READ-ONLY
#    - Connector interfaces enforce read-only access (execute_read only).
#    - Database credentials for external sources have only SELECT permissions.
#    - No INSERT, UPDATE, DELETE, or DDL operations on external sources.
#
# 4. AI AGENT NEVER RECEIVES CREDENTIALS
#    - AI tools access data through service layer abstractions only.
#    - Tool functions never accept credential parameters.
#    - The agent invokes tools by business intent — it never knows which
#      database or connection backs a tool.
#
# 5. PARAMETERIZED QUERIES ONLY
#    - All repositories inherit from BaseRepository which enforces
#      SQLAlchemy bound parameters for every database operation.
#    - String interpolation of user input into SQL is forbidden.
#    - This is enforced by code review and the base repository pattern.
#
# 6. .GITIGNORE PROTECTS SECRETS FROM SOURCE CONTROL
#    - .env, *.pem, credentials.*, and secrets.* are excluded.
#    - Frontend bundles never contain secrets (VITE_ prefix only for
#      non-sensitive public config).
#
# =============================================================================
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import Settings


# =============================================================================
# Settings Provider (singleton)
# =============================================================================


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Provide the application settings singleton.

    Cached so environment parsing happens only once.
    Used as a dependency by other providers and directly in route handlers.
    """
    return Settings()


async def get_async_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session for dependency injection.

    The session is scoped to the request lifecycle and automatically
    closed after the request completes. Transactions are committed
    by the service layer and rolled back on unhandled exceptions.

    WARNING: Never pass this session directly to AI tools or agent code.
    AI tools access data exclusively through service → repository chains.

    Args:
        session_factory: Async session factory created at application startup.

    Yields:
        An AsyncSession instance for the request scope.
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    """
    Create an async session factory for a given database URL.

    This is called once at application startup for each internal database
    (App_DB, RAG_DB). The URL comes from environment variables via Settings.

    WARNING: database_url contains credentials — never log this value.

    Args:
        database_url: PostgreSQL async connection string from environment.

    Returns:
        Configured async session factory.
    """
    engine = create_async_engine(
        database_url,
        echo=False,  # NOTE: Never set echo=True in production — it logs SQL with params
        pool_pre_ping=True,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


# =============================================================================
# App_DB Session Provider
# =============================================================================

# NOTE: The session factory is initialized at application startup in main.py.
# This module-level variable is set by `initialize_app_db()` below.
_app_db_session_factory: async_sessionmaker[AsyncSession] | None = None


def initialize_app_db(settings: Settings) -> None:
    """
    Create the App_DB session factory at application startup.

    Called once from main.py lifespan. After this, get_app_db_session()
    can yield sessions for request-scoped dependency injection.

    Args:
        settings: Application settings containing APP_DB_URL.
    """
    global _app_db_session_factory  # noqa: PLW0603
    _app_db_session_factory = create_session_factory(settings.app_db_url)


async def get_app_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a request-scoped App_DB async session.

    Yields:
        AsyncSession bound to App_DB for the duration of the request.

    Raises:
        RuntimeError: If called before initialize_app_db().
    """
    if _app_db_session_factory is None:
        raise RuntimeError(
            "App_DB session factory not initialized. "
            "Call initialize_app_db() during application startup."
        )
    async with _app_db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# Repository Layer
# =============================================================================


async def get_project_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "ProjectRepository":
    """
    Provide a ProjectRepository instance with real database session.

    Args:
        session: AsyncSession injected from App_DB session provider.

    Returns:
        ProjectRepository connected to the App_DB.
    """
    from app.repositories.project_repository import ProjectRepository

    return ProjectRepository(session)


# =============================================================================
# Service Layer
# =============================================================================


async def get_project_service(
    repository: "ProjectRepository" = Depends(get_project_repository),
) -> "ProjectService":
    """
    Provide a ProjectService instance with repository injected.

    Assembles the service with its repository dependency.
    """
    from app.services.project_service import ProjectService

    return ProjectService(repository=repository)


# =============================================================================
# Domain Repository Providers (Phase 3)
# =============================================================================


async def get_finance_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "FinanceRepository":
    """Provide a FinanceRepository instance."""
    from app.repositories.finance_repository import FinanceRepository

    return FinanceRepository(session)


async def get_jira_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "JiraRepository":
    """Provide a JiraRepository instance."""
    from app.repositories.jira_repository import JiraRepository

    return JiraRepository(session)


async def get_resource_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "ResourceRepository":
    """Provide a ResourceRepository instance."""
    from app.repositories.resource_repository import ResourceRepository

    return ResourceRepository(session)


async def get_sdlc_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "SdlcRepository":
    """Provide an SdlcRepository instance."""
    from app.repositories.sdlc_repository import SdlcRepository

    return SdlcRepository(session)


async def get_audit_finding_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "AuditFindingRepository":
    """Provide an AuditFindingRepository instance."""
    from app.repositories.audit_finding_repository import AuditFindingRepository

    return AuditFindingRepository(session)


async def get_control_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "ControlRepository":
    """Provide a ControlRepository instance."""
    from app.repositories.control_repository import ControlRepository

    return ControlRepository(session)


async def get_remediation_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "RemediationRepository":
    """Provide a RemediationRepository instance."""
    from app.repositories.remediation_repository import RemediationRepository

    return RemediationRepository(session)


async def get_risk_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "RiskRepository":
    """Provide a RiskRepository instance."""
    from app.repositories.risk_repository import RiskRepository

    return RiskRepository(session)


async def get_progress_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "ProgressRepository":
    """Provide a ProgressRepository instance."""
    from app.repositories.progress_repository import ProgressRepository

    return ProgressRepository(session)


async def get_health_kpi_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "HealthKpiRepository":
    """Provide a HealthKpiRepository instance."""
    from app.repositories.health_kpi_repository import HealthKpiRepository

    return HealthKpiRepository(session)


# =============================================================================
# Domain Service Providers (Phase 3)
# =============================================================================


async def get_finance_service(
    repository: "FinanceRepository" = Depends(get_finance_repository),
) -> "FinanceService":
    """Provide a FinanceService instance with repository injected."""
    from app.services.finance_service import FinanceService

    return FinanceService(repository=repository)


async def get_jira_service(
    repository: "JiraRepository" = Depends(get_jira_repository),
) -> "JiraService":
    """Provide a JiraService instance with repository injected."""
    from app.services.jira_service import JiraService

    return JiraService(repository=repository)


async def get_resource_service(
    repository: "ResourceRepository" = Depends(get_resource_repository),
) -> "ResourceService":
    """Provide a ResourceService instance with repository injected."""
    from app.services.resource_service import ResourceService

    return ResourceService(repository=repository)


async def get_sdlc_service(
    repository: "SdlcRepository" = Depends(get_sdlc_repository),
) -> "SdlcService":
    """Provide an SdlcService instance with repository injected."""
    from app.services.sdlc_service import SdlcService

    return SdlcService(repository=repository)


async def get_audit_finding_service(
    repository: "AuditFindingRepository" = Depends(get_audit_finding_repository),
) -> "AuditFindingService":
    """Provide an AuditFindingService instance with repository injected."""
    from app.services.audit_finding_service import AuditFindingService

    return AuditFindingService(repository=repository)


async def get_control_service(
    repository: "ControlRepository" = Depends(get_control_repository),
) -> "ControlService":
    """Provide a ControlService instance with repository injected."""
    from app.services.control_service import ControlService

    return ControlService(repository=repository)


async def get_remediation_service(
    repository: "RemediationRepository" = Depends(get_remediation_repository),
) -> "RemediationService":
    """Provide a RemediationService instance with repository injected."""
    from app.services.remediation_service import RemediationService

    return RemediationService(repository=repository)


async def get_risk_service(
    repository: "RiskRepository" = Depends(get_risk_repository),
) -> "RiskService":
    """Provide a RiskService instance with repository injected."""
    from app.services.risk_service import RiskService

    return RiskService(repository=repository)


async def get_progress_service(
    repository: "ProgressRepository" = Depends(get_progress_repository),
) -> "ProgressService":
    """Provide a ProgressService instance with repository injected."""
    from app.services.progress_service import ProgressService

    return ProgressService(repository=repository)


async def get_project_health_service(
    finance_repository: "FinanceRepository" = Depends(get_finance_repository),
    jira_repository: "JiraRepository" = Depends(get_jira_repository),
    resource_repository: "ResourceRepository" = Depends(get_resource_repository),
    audit_finding_repository: "AuditFindingRepository" = Depends(get_audit_finding_repository),
    control_repository: "ControlRepository" = Depends(get_control_repository),
    remediation_repository: "RemediationRepository" = Depends(get_remediation_repository),
    risk_repository: "RiskRepository" = Depends(get_risk_repository),
    progress_repository: "ProgressRepository" = Depends(get_progress_repository),
    health_kpi_repository: "HealthKpiRepository" = Depends(get_health_kpi_repository),
) -> "ProjectHealthService":
    """Provide a ProjectHealthService instance with all domain repositories injected."""
    from app.services.project_health_service import ProjectHealthService

    return ProjectHealthService(
        finance_repository=finance_repository,
        jira_repository=jira_repository,
        resource_repository=resource_repository,
        audit_finding_repository=audit_finding_repository,
        control_repository=control_repository,
        remediation_repository=remediation_repository,
        risk_repository=risk_repository,
        progress_repository=progress_repository,
        health_kpi_repository=health_kpi_repository,
    )





# =============================================================================
# Data Source Service Provider (Phase 2)
# =============================================================================


async def get_data_source_service(
    session: AsyncSession = Depends(get_app_db_session),
) -> "DataSourceService":
    """Provide a DataSourceService instance with repository injected."""
    from app.repositories.data_source_repository import DataSourceRepository
    from app.services.data_source_service import DataSourceService

    repository = DataSourceRepository(session)
    return DataSourceService(repository=repository)


async def get_connector_service(
    session: AsyncSession = Depends(get_app_db_session),
    registry: "ConnectorRegistry" = Depends(lambda: get_connector_registry()),
) -> "ConnectorService":
    """Provide a ConnectorService instance with dependencies injected."""
    from app.repositories.data_source_repository import DataSourceRepository
    from app.security.credential_encryptor import CredentialEncryptor
    from app.services.connector_service import ConnectorService

    repository = DataSourceRepository(session)
    settings = get_settings()
    encryptor = CredentialEncryptor(fernet_key=settings.fernet_key)
    return ConnectorService(
        data_source_repository=repository,
        credential_encryptor=encryptor,
        connector_registry=registry,
    )


# =============================================================================
# Connector Layer
# =============================================================================


_connector_registry: "ConnectorRegistry | None" = None


def initialize_connector_registry() -> None:
    """
    Create and populate the ConnectorRegistry at application startup.

    Registers all built-in connector implementations. Adding a future connector
    requires only:
      1. Creating a new file (e.g., app/connectors/snowflake_connector.py)
      2. Registering it here: registry.register("snowflake", SnowflakeConnector)

    No changes to existing connector implementations, services, or AI tools.
    """
    global _connector_registry  # noqa: PLW0603

    from app.connectors import ConnectorRegistry, MongoDBConnector, PostgresConnector

    registry = ConnectorRegistry()
    registry.register("postgresql", PostgresConnector)
    registry.register("mongodb", MongoDBConnector)

    # To add a future connector (e.g., Snowflake):
    # from app.connectors.snowflake_connector import SnowflakeConnector
    # registry.register("snowflake", SnowflakeConnector)

    _connector_registry = registry


def get_connector_registry() -> "ConnectorRegistry":
    """
    Provide the singleton ConnectorRegistry with all connectors pre-registered.

    Returns:
        The application-wide ConnectorRegistry instance.

    Raises:
        RuntimeError: If called before initialize_connector_registry().
    """
    if _connector_registry is None:
        raise RuntimeError(
            "ConnectorRegistry not initialized. "
            "Call initialize_connector_registry() during application startup."
        )
    return _connector_registry


# =============================================================================
# AI / Provider Layer
# =============================================================================

_provider_registry: "ProviderRegistry | None" = None
_text_generation_provider: "TextGenerationProvider | None" = None
_embedding_provider: "EmbeddingProvider | None" = None


def initialize_provider_registry() -> "ProviderRegistry":
    """
    Create and populate the ProviderRegistry at application startup.

    Registers all built-in text generation and embedding providers.
    Adding a future provider requires only creating the implementation
    and registering it here.

    Returns:
        The initialized ProviderRegistry instance.
    """
    global _provider_registry  # noqa: PLW0603

    from app.ai.providers import (
        AzureFoundryTextGenerationProvider,
        AzureOpenAIEmbeddingProvider,
        AzureOpenAITextGenerationProvider,
        GroqTextGenerationProvider,
        MockEmbeddingProvider,
        MockTextGenerationProvider,
        ProviderRegistry,
    )

    registry = ProviderRegistry()

    # Text generation providers
    registry.register_text_provider("azure_foundry", AzureFoundryTextGenerationProvider)
    registry.register_text_provider("azure_openai", AzureOpenAITextGenerationProvider)
    registry.register_text_provider("groq", GroqTextGenerationProvider)
    registry.register_text_provider("mock", MockTextGenerationProvider)

    # Embedding providers
    registry.register_embedding_provider("azure_openai", AzureOpenAIEmbeddingProvider)
    registry.register_embedding_provider("azure_foundry", AzureFoundryTextGenerationProvider)
    registry.register_embedding_provider("mock", MockEmbeddingProvider)

    _provider_registry = registry
    return registry


def get_provider_registry() -> "ProviderRegistry":
    """
    Provide the singleton ProviderRegistry with all providers pre-registered.

    Returns:
        The application-wide ProviderRegistry instance.

    Raises:
        RuntimeError: If called before initialize_provider_registry().
    """
    if _provider_registry is None:
        raise RuntimeError(
            "ProviderRegistry not initialized. "
            "Call initialize_provider_registry() during application startup."
        )
    return _provider_registry


def resolve_text_generation_provider(settings: Settings) -> "TextGenerationProvider":
    """
    Resolve the text generation provider based on settings.

    In Demo Mode, defaults LLM_PROVIDER to "mock" if not explicitly set,
    enabling full orchestration smoke testing without credentials.

    In Live Mode, the provider must already be validated by
    validate_live_mode_settings().

    Args:
        settings: Application settings with llm_provider and credentials.

    Returns:
        An instantiated TextGenerationProvider.
    """
    from app.config.logging import get_logger

    logger = get_logger(__name__)
    registry = get_provider_registry()

    provider_name = settings.llm_provider

    # In Demo Mode, default to "mock" if no provider is explicitly set
    if settings.demo_mode and not provider_name:
        provider_name = "mock"
        logger.info(
            "provider_defaulted_to_mock",
            reason="LLM_PROVIDER not set in Demo Mode",
        )

    # Resolve with provider-specific config
    config = _get_text_provider_config(settings, provider_name)
    return registry.resolve_text_provider(provider_name, **config)


def resolve_embedding_provider(settings: Settings) -> "EmbeddingProvider":
    """
    Resolve the embedding provider based on settings.

    In Demo Mode, defaults EMBEDDING_PROVIDER to "mock" if not explicitly set.

    Args:
        settings: Application settings with embedding_provider and credentials.

    Returns:
        An instantiated EmbeddingProvider.
    """
    from app.config.logging import get_logger

    logger = get_logger(__name__)
    registry = get_provider_registry()

    provider_name = settings.embedding_provider

    # In Demo Mode, default to "mock" if no embedding provider is set
    if settings.demo_mode and not provider_name:
        provider_name = "mock"
        logger.info(
            "embedding_provider_defaulted_to_mock",
            reason="EMBEDDING_PROVIDER not set in Demo Mode",
        )

    config = _get_embedding_provider_config(settings, provider_name)
    return registry.resolve_embedding_provider(provider_name, **config)


def initialize_providers(settings: Settings) -> None:
    """
    Initialize the provider registry and resolve providers at startup.

    In Demo Mode: logs warnings if credentials are absent but does NOT
    fail startup (demo uses seeded data + mock provider).

    In Live Mode: provider validation is already done by
    validate_live_mode_settings() before this is called.

    Args:
        settings: Application settings.
    """
    from app.config.logging import get_logger

    logger = get_logger(__name__)

    global _text_generation_provider, _embedding_provider  # noqa: PLW0603

    initialize_provider_registry()

    if settings.demo_mode:
        # In Demo Mode, warn but don't fail if credentials are absent
        try:
            _text_generation_provider = resolve_text_generation_provider(settings)
        except Exception as exc:
            logger.warning(
                "text_provider_resolution_failed_demo_mode",
                error=str(exc),
                fallback="mock",
            )
            # Fall back to mock in demo mode
            registry = get_provider_registry()
            _text_generation_provider = registry.resolve_text_provider("mock")

        try:
            _embedding_provider = resolve_embedding_provider(settings)
        except Exception as exc:
            logger.warning(
                "embedding_provider_resolution_failed_demo_mode",
                error=str(exc),
                fallback="mock",
            )
            # Fall back to mock in demo mode
            registry = get_provider_registry()
            from app.ai.providers import MockEmbeddingProvider

            _embedding_provider = MockEmbeddingProvider(
                dimension=settings.embedding_dimension
            )
    else:
        # Live Mode — resolution errors should propagate as startup failures
        _text_generation_provider = resolve_text_generation_provider(settings)
        _embedding_provider = resolve_embedding_provider(settings)

    logger.info(
        "providers_initialized",
        text_provider=type(_text_generation_provider).__name__,
        embedding_provider=type(_embedding_provider).__name__,
    )


def get_text_generation_provider() -> "TextGenerationProvider":
    """
    Provide the resolved text generation provider.

    Returns:
        The active TextGenerationProvider instance.

    Raises:
        RuntimeError: If called before initialize_providers().
    """
    if _text_generation_provider is None:
        raise RuntimeError(
            "Text generation provider not initialized. "
            "Call initialize_providers() during application startup."
        )
    return _text_generation_provider


def get_embedding_provider() -> "EmbeddingProvider":
    """
    Provide the resolved embedding provider.

    Returns:
        The active EmbeddingProvider instance.

    Raises:
        RuntimeError: If called before initialize_providers().
    """
    if _embedding_provider is None:
        raise RuntimeError(
            "Embedding provider not initialized. "
            "Call initialize_providers() during application startup."
        )
    return _embedding_provider


# =============================================================================
# AI Service Layer
# =============================================================================

_tool_registry: "ToolRegistry | None" = None
_ai_service: "AIService | None" = None


def initialize_tool_registry() -> "ToolRegistry":
    """
    Create the AI ToolRegistry at application startup.

    Tools are registered here by domain name. Adding a new tool requires:
      1. Creating the tool function in app/ai/tools/<domain>_tools.py
      2. Registering it here: registry.register("tool_name", tool_fn)

    No changes to existing tools, agent, or service code.

    Returns:
        The initialized ToolRegistry instance.
    """
    global _tool_registry  # noqa: PLW0603

    from app.ai.tools.registry import ToolRegistry
    from app.ai.tools.project_tools import create_get_project_context
    from app.ai.tools.finance_tools import create_query_project_finance

    registry = ToolRegistry()

    # Register domain tools with session-scoped service factories.
    # Each tool invocation creates a fresh session → repository → service chain.
    registry.register(
        "get_project_context",
        _create_project_context_tool(),
    )
    registry.register(
        "query_project_finance",
        _create_finance_tool(),
    )

    _tool_registry = registry
    return registry


def _create_project_context_tool():
    """
    Build the get_project_context tool with per-invocation session management.

    The tool creates a fresh database session for each call, ensuring
    proper connection lifecycle and isolation between agent invocations.

    Returns:
        Async tool function that obtains its own session at call time.
    """
    from uuid import UUID

    from app.ai.tools.project_tools import create_get_project_context
    from app.repositories.project_repository import ProjectRepository
    from app.services.project_service import ProjectService

    async def get_project_context(project_id: UUID) -> dict:
        if _app_db_session_factory is None:
            raise RuntimeError("App_DB not initialized")

        async with _app_db_session_factory() as session:
            repository = ProjectRepository(session)
            service = ProjectService(repository=repository)
            tool_fn = create_get_project_context(service)
            return await tool_fn(project_id)

    return get_project_context


def _create_finance_tool():
    """
    Build the query_project_finance tool with per-invocation session management.

    The tool creates a fresh database session for each call, ensuring
    proper connection lifecycle and isolation between agent invocations.

    Returns:
        Async tool function that obtains its own session at call time.
    """
    from uuid import UUID

    from app.ai.tools.finance_tools import create_query_project_finance
    from app.repositories.data_source_repository import DataSourceRepository
    from app.services.data_source_service import DataSourceService

    async def query_project_finance(project_id: UUID) -> dict:
        if _app_db_session_factory is None:
            raise RuntimeError("App_DB not initialized")

        async with _app_db_session_factory() as session:
            repository = DataSourceRepository(session)
            service = DataSourceService(repository=repository)
            tool_fn = create_query_project_finance(service)
            return await tool_fn(project_id)

    return query_project_finance


def get_tool_registry() -> "ToolRegistry":
    """
    Provide the singleton ToolRegistry with all AI tools pre-registered.

    Returns:
        The application-wide ToolRegistry instance.

    Raises:
        RuntimeError: If called before initialize_tool_registry().
    """
    if _tool_registry is None:
        raise RuntimeError(
            "ToolRegistry not initialized. "
            "Call initialize_tool_registry() during application startup."
        )
    return _tool_registry


def initialize_ai_service(settings: Settings) -> "AIService":
    """
    Create the AIService at application startup.

    Assembles the AI service with its dependencies:
    - Text generation provider (already resolved)
    - Tool registry (already initialized)
    - Prompt manager (None for Phase 0)

    Must be called AFTER initialize_providers() and initialize_tool_registry().

    Args:
        settings: Application settings.

    Returns:
        The initialized AIService instance.
    """
    global _ai_service  # noqa: PLW0603

    from app.ai.service import AIService

    provider = get_text_generation_provider()
    tool_registry = get_tool_registry()

    _ai_service = AIService(
        provider=provider,
        tool_registry=tool_registry,
        prompt_manager=None,  # Phase 1: PromptManager integration
    )

    from app.config.logging import get_logger

    logger = get_logger(__name__)
    logger.info(
        "ai_service_initialized",
        registered_tools=tool_registry.list_tools(),
        provider=type(provider).__name__,
    )

    return _ai_service


def get_ai_service() -> "AIService":
    """
    Provide the singleton AIService instance.

    Returns:
        The application-wide AIService.

    Raises:
        RuntimeError: If called before initialize_ai_service().
    """
    if _ai_service is None:
        raise RuntimeError(
            "AIService not initialized. "
            "Call initialize_ai_service() during application startup."
        )
    return _ai_service


# =============================================================================
# Provider Configuration Helpers
# =============================================================================


def _get_text_provider_config(settings: Settings, provider_name: str | None) -> dict:
    """Build provider-specific config dict for text generation provider instantiation."""
    if provider_name == "azure_foundry":
        return {
            "api_key": settings.azure_foundry_api_key or "",
            "endpoint": settings.azure_foundry_endpoint or "",
            "model": settings.azure_foundry_model or "",
        }
    elif provider_name == "azure_openai":
        return {
            "api_key": settings.azure_openai_api_key or "",
            "endpoint": settings.azure_openai_endpoint or "",
            "model": settings.azure_openai_deployment or "",
            "api_version": settings.azure_openai_api_version,
        }
    elif provider_name == "groq":
        return {
            "api_key": settings.groq_api_key or "",
            "model": settings.groq_model,
        }
    # "mock" and any other provider that takes no config
    return {}


def _get_embedding_provider_config(settings: Settings, provider_name: str | None) -> dict:
    """Build provider-specific config dict for embedding provider instantiation."""
    if provider_name == "azure_openai":
        return {
            "api_key": settings.azure_openai_api_key or "",
            "endpoint": settings.azure_openai_endpoint or "",
            "model": settings.embedding_model or "",
            "api_version": settings.azure_openai_api_version,
        }
    elif provider_name == "azure_foundry":
        return {
            "api_key": settings.azure_foundry_api_key or "",
            "endpoint": settings.azure_foundry_endpoint or "",
            "model": settings.embedding_model or "",
        }
    elif provider_name == "mock":
        return {
            "dimension": settings.embedding_dimension,
        }
    return {}



# =============================================================================
# File Service Provider (Phase 1)
# =============================================================================


async def get_file_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "FileRepository":
    """Provide a FileRepository instance with database session."""
    from app.repositories.file_repository import FileRepository

    return FileRepository(session)


async def get_file_service(
    session: AsyncSession = Depends(get_app_db_session),
) -> "FileService":
    """Provide a FileService instance with all required repositories."""
    from app.repositories.data_source_repository import DataSourceRepository
    from app.repositories.file_repository import FileRepository
    from app.repositories.project_repository import ProjectRepository
    from app.services.file_service import FileService

    file_repo = FileRepository(session)
    project_repo = ProjectRepository(session)
    data_source_repo = DataSourceRepository(session)
    return FileService(
        file_repository=file_repo,
        project_repository=project_repo,
        data_source_repository=data_source_repo,
    )


# =============================================================================
# Phase 4: Content-Aware Ingestion Providers
# =============================================================================


def get_file_type_detector() -> "FileTypeDetector":
    """Provide a FileTypeDetector instance."""
    from app.processors.file_type_detector import FileTypeDetector

    return FileTypeDetector()


def get_content_classifier() -> "ContentClassifier":
    """Provide a ContentClassifier with default confidence threshold."""
    from app.processors.content_classifier import ContentClassifier

    return ContentClassifier(confidence_threshold=0.75)


def get_file_processor_registry() -> "FileProcessorRegistry":
    """Create a FileProcessorRegistry with all format processors registered.

    Registers: Excel, CSV, JSON, PDF, DOCX, Text processors.
    """
    from app.processors.csv_processor import CSVProcessor
    from app.processors.docx_processor import DOCXProcessor
    from app.processors.excel_processor import ExcelProcessor
    from app.processors.json_processor import JSONProcessor
    from app.processors.pdf_processor import PDFProcessor
    from app.processors.registry import FileProcessorRegistry
    from app.processors.text_processor import TextProcessor

    registry = FileProcessorRegistry()

    # Excel formats
    excel_processor = ExcelProcessor()
    registry.register("xlsx", excel_processor)
    registry.register("xls", excel_processor)

    # Tabular data formats
    registry.register("csv", CSVProcessor())
    registry.register("json", JSONProcessor())

    # Document formats
    registry.register("pdf", PDFProcessor())
    registry.register("docx", DOCXProcessor())
    registry.register("txt", TextProcessor())

    return registry


async def get_dataset_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "DatasetRepository":
    """Provide a DatasetRepository instance."""
    from app.repositories.dataset_repository import DatasetRepository

    return DatasetRepository(session)


async def get_dataset_service(
    session: AsyncSession = Depends(get_app_db_session),
) -> "DatasetService":
    """Provide a DatasetService instance with dataset and file repositories."""
    from app.repositories.dataset_repository import DatasetRepository
    from app.repositories.file_repository import FileRepository
    from app.services.dataset_service import DatasetService

    dataset_repo = DatasetRepository(session)
    file_repo = FileRepository(session)
    return DatasetService(
        dataset_repository=dataset_repo,
        file_repository=file_repo,
    )


async def get_document_repository(
    session: AsyncSession = Depends(get_app_db_session),
) -> "DocumentRepository":
    """Provide a DocumentRepository instance.

    NOTE: In a full deployment, this would use RAG_DB session.
    For POC, uses App_DB session (both DBs share the same engine in dev).
    """
    from app.repositories.document_repository import DocumentRepository

    return DocumentRepository(session)


async def get_document_search_service(
    session: AsyncSession = Depends(get_app_db_session),
) -> "DocumentSearchService":
    """Provide a DocumentSearchService with document repository and embedding generator.

    Uses the configured embedding provider for query embedding generation.
    Falls back to DeterministicEmbeddingGenerator if provider not initialized.
    """
    from app.documents.embedder import DeterministicEmbeddingGenerator
    from app.repositories.document_repository import DocumentRepository
    from app.services.document_search_service import DocumentSearchService

    doc_repo = DocumentRepository(session)

    # Use production embedding generator if provider is available
    try:
        embedding_provider = get_embedding_provider()
        from app.documents.embedder import ProductionEmbeddingGenerator

        embedding_gen = ProductionEmbeddingGenerator(embedding_provider)
    except RuntimeError:
        # Fallback to deterministic embedder for dev/demo
        embedding_gen = DeterministicEmbeddingGenerator()

    return DocumentSearchService(
        document_repository=doc_repo,
        embedding_generator=embedding_gen,
    )


async def get_ingestion_orchestrator(
    session: AsyncSession = Depends(get_app_db_session),
) -> "IngestionOrchestrator":
    """Provide a fully configured IngestionOrchestrator with all dependencies.

    Assembles both legacy pipeline components (validator, extractor, chunker,
    embedder) and content-aware components (file type detector, processor
    registry, content classifier, dataset service).
    """
    from app.documents.chunker import FixedSizeChunker
    from app.documents.embedder import DeterministicEmbeddingGenerator
    from app.documents.extractors import TxtContentExtractor
    from app.documents.orchestrator import IngestionOrchestrator
    from app.documents.validator import SimpleFileValidator
    from app.repositories.dataset_repository import DatasetRepository
    from app.repositories.document_repository import DocumentRepository
    from app.repositories.file_repository import FileRepository
    from app.services.dataset_service import DatasetService

    # Legacy pipeline components
    file_validator = SimpleFileValidator(
        allowed_types={"txt", "pdf", "docx", "xlsx", "xls", "csv", "json"}
    )
    content_extractor = TxtContentExtractor()
    # Metadata extractor — simple stub
    metadata_extractor = _SimpleMetadataExtractor()
    text_chunker = FixedSizeChunker()

    # Embedding generator — use production if available
    try:
        embedding_provider = get_embedding_provider()
        from app.documents.embedder import ProductionEmbeddingGenerator

        embedding_gen = ProductionEmbeddingGenerator(embedding_provider)
    except RuntimeError:
        embedding_gen = DeterministicEmbeddingGenerator()

    # Repositories
    doc_repo = DocumentRepository(session)
    dataset_repo = DatasetRepository(session)
    file_repo = FileRepository(session)

    # Content-aware components
    file_type_detector = get_file_type_detector()
    processor_registry = get_file_processor_registry()
    content_classifier = get_content_classifier()
    dataset_service = DatasetService(
        dataset_repository=dataset_repo,
        file_repository=file_repo,
    )

    return IngestionOrchestrator(
        file_validator=file_validator,
        content_extractor=content_extractor,
        metadata_extractor=metadata_extractor,
        text_chunker=text_chunker,
        embedding_generator=embedding_gen,
        document_repository=doc_repo,
        file_type_detector=file_type_detector,
        processor_registry=processor_registry,
        content_classifier=content_classifier,
        dataset_service=dataset_service,
    )


class _SimpleMetadataExtractor:
    """Simple metadata extractor stub for the ingestion pipeline.

    Returns basic metadata from file path. Satisfies the MetadataExtractor protocol.
    """

    async def extract_metadata(self, file_path: str, content: str) -> dict[str, str]:
        """Extract basic metadata from file path and content length."""
        from pathlib import Path

        path = Path(file_path)
        return {
            "file_name": path.name,
            "content_length": str(len(content)),
        }
