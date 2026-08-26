"""
Connector domain AI tools for cross-source intelligence.

Provides the AI agent with tools to query connected enterprise data sources
(PostgreSQL, MongoDB) and discover the semantic information landscape.

Tools access data exclusively through ConnectorRegistry and DataSourceRepository.
Credentials are resolved server-side only — never passed to or from the agent.

Two interfaces are provided:
- Factory functions (create_*) for ToolRegistry registration (legacy agent)
- @tool-decorated functions for Strands Agent consumption

WARNING: Never log or return credentials, connection strings, or API keys.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

import structlog
from strands import tool

from app.connectors.protocol import QueryResult
from app.connectors.registry import ConnectorRegistry
from app.connectors.sql_validator import validate_read_only_sql
from app.errors.datasource_errors import (
    DataSourceNotFoundError,
    QueryExecutionError,
    QueryValidationError,
)
from app.repositories.data_source_repository import DataSourceRepository
from app.security.credential_encryptor import CredentialEncryptor
from app.services.catalog_service import CatalogService

logger = structlog.get_logger(__name__)

# Default row limit for query results to prevent context overflow
DEFAULT_ROW_LIMIT: int = 500

# =============================================================================
# Module-level dependency references — set during application startup
# =============================================================================

_data_source_repository_factory: Any = None
_credential_encryptor: CredentialEncryptor | None = None
_connector_registry: ConnectorRegistry | None = None
_catalog_service_factory: Any = None
_row_limit: int = DEFAULT_ROW_LIMIT


def initialize_connector_tools(
    data_source_repository_factory: Any,
    credential_encryptor: CredentialEncryptor,
    connector_registry: ConnectorRegistry,
    catalog_service_factory: Any,
    row_limit: int = DEFAULT_ROW_LIMIT,
) -> None:
    """Set module-level dependencies for @tool-decorated functions.

    Called once during application startup from dependencies.py.

    Args:
        data_source_repository_factory: Async callable that returns a DataSourceRepository
            (creates its own session per invocation for isolation).
        credential_encryptor: Decrypts stored connection credentials.
        connector_registry: Resolves source_type to connector implementation.
        catalog_service_factory: Async callable that returns a CatalogService
            (creates its own session per invocation for isolation).
        row_limit: Maximum rows returned per query (default 500).
    """
    global _data_source_repository_factory, _credential_encryptor  # noqa: PLW0603
    global _connector_registry, _catalog_service_factory, _row_limit  # noqa: PLW0603

    _data_source_repository_factory = data_source_repository_factory
    _credential_encryptor = credential_encryptor
    _connector_registry = connector_registry
    _catalog_service_factory = catalog_service_factory
    _row_limit = row_limit

    logger.info("connector_tools_initialized")


def _get_dependencies() -> tuple[Any, CredentialEncryptor, ConnectorRegistry]:
    """Retrieve configured module-level dependencies for query tool.

    Raises:
        RuntimeError: If initialize_connector_tools() has not been called.
    """
    if _data_source_repository_factory is None or _credential_encryptor is None or _connector_registry is None:
        raise RuntimeError(
            "Connector tools not initialized. "
            "Call initialize_connector_tools() during application startup."
        )
    return _data_source_repository_factory, _credential_encryptor, _connector_registry


def _get_catalog_factory() -> Any:
    """Retrieve configured catalog service factory.

    Raises:
        RuntimeError: If initialize_connector_tools() has not been called.
    """
    if _catalog_service_factory is None:
        raise RuntimeError(
            "Connector tools not initialized. "
            "Call initialize_connector_tools() during application startup."
        )
    return _catalog_service_factory


# =============================================================================
# Factory: create_query_connected_source (for ToolRegistry)
# =============================================================================


def create_query_connected_source(
    data_source_repository: DataSourceRepository,
    credential_encryptor: CredentialEncryptor,
    connector_registry: ConnectorRegistry,
    row_limit: int = DEFAULT_ROW_LIMIT,
):
    """Factory that creates the query_connected_source tool function.

    Uses closure to inject dependencies (DataSourceRepository, CredentialEncryptor,
    ConnectorRegistry), keeping the tool function signature clean for agent invocation.

    Args:
        data_source_repository: Repository for DataSource entity lookups.
        credential_encryptor: Decrypts stored connection credentials at execution time.
        connector_registry: Resolves source_type to connector implementation.
        row_limit: Maximum rows returned per query (default 500).

    Returns:
        Async tool function registered in the ToolRegistry.
    """

    async def query_connected_source(
        source_id: str,
        query_type: str,
        query: str | list[dict],
    ) -> dict[str, Any]:
        """Execute a read-only query against a connected enterprise data source.

        Resolves the connector via source_id, validates read-only safety,
        executes the query, and returns structured results with source metadata.

        Args:
            source_id: UUID string of the data source from the catalog.
            query_type: "sql" for PostgreSQL or "mongodb" for MongoDB.
            query: Source-native query.
                For query_type="sql": a SQL SELECT string.
                For query_type="mongodb": an aggregation pipeline as list of stage dicts.

        Returns:
            Structured dict with columns, rows, row_count, has_more_rows,
            source_metadata, and duration_ms. On error, returns error dict
            with error_type and message (never credentials).
        """
        start_time = time.monotonic()

        logger.info(
            "tool_query_connected_source_invoked",
            extra={
                "source_id": source_id,
                "query_type": query_type,
            },
        )

        try:
            # Validate source_id is a valid UUID
            try:
                parsed_source_id = UUID(source_id)
            except (ValueError, AttributeError):
                return _error_response(
                    error_type="validation_error",
                    message="Invalid source_id format: must be a valid UUID",
                    duration_ms=_elapsed_ms(start_time),
                )

            # Validate query_type
            if query_type not in ("sql", "mongodb", "jira"):
                return _error_response(
                    error_type="validation_error",
                    message=f"Invalid query_type '{query_type}'. Must be 'sql' or 'mongodb'.",
                    duration_ms=_elapsed_ms(start_time),
                )

            # Validate query format matches query_type
            if query_type == "sql" and not isinstance(query, str):
                return _error_response(
                    error_type="validation_error",
                    message="For query_type='sql', query must be a SQL string.",
                    duration_ms=_elapsed_ms(start_time),
                )
            if query_type == "mongodb" and not isinstance(query, list):
                return _error_response(
                    error_type="validation_error",
                    message="For query_type='mongodb', query must be a list of pipeline stage dicts.",
                    duration_ms=_elapsed_ms(start_time),
                )

            # Validate read-only for SQL queries
            if query_type == "sql":
                try:
                    validate_read_only_sql(query, source_type="postgresql")
                except QueryValidationError as validation_err:
                    return _error_response(
                        error_type="query_validation_error",
                        message=str(validation_err.message),
                        duration_ms=_elapsed_ms(start_time),
                    )

            # Look up the data source
            data_source = await data_source_repository.get_data_source(parsed_source_id)
            if data_source is None:
                return _error_response(
                    error_type="source_not_found",
                    message=f"Data source '{source_id}' not found.",
                    duration_ms=_elapsed_ms(start_time),
                )

            # Decrypt credentials and resolve connector
            decrypted_config = credential_encryptor.decrypt_config(
                data_source.connection_config or {}
            )
            connector = connector_registry.resolve(
                source_type=data_source.source_type,
                connection_config=decrypted_config,
            )

            # Execute the query
            result: QueryResult = await connector.execute_read(query)

            # Apply row limit
            has_more_rows = result.has_more_rows or result.row_count > row_limit
            capped_rows = result.rows[:row_limit]
            capped_row_count = min(result.row_count, row_limit)

            duration_ms = _elapsed_ms(start_time)

            logger.info(
                "tool_query_connected_source_completed",
                extra={
                    "source_id": source_id,
                    "query_type": query_type,
                    "row_count": capped_row_count,
                    "has_more_rows": has_more_rows,
                    "duration_ms": duration_ms,
                },
            )

            return {
                "columns": result.columns,
                "rows": capped_rows,
                "row_count": capped_row_count,
                "has_more_rows": has_more_rows,
                "source_metadata": {
                    "source_id": source_id,
                    "source_type": data_source.source_type,
                    "source_name": data_source.name,
                    "object_name": _extract_object_name(query_type, query),
                },
                "duration_ms": duration_ms,
            }

        except DataSourceNotFoundError:
            return _error_response(
                error_type="source_not_found",
                message=f"Data source '{source_id}' not found.",
                duration_ms=_elapsed_ms(start_time),
            )
        except QueryExecutionError as exec_err:
            logger.error(
                "tool_query_connected_source_execution_error",
                extra={
                    "source_id": source_id,
                    "query_type": query_type,
                    "error": str(exec_err),
                },
            )
            return _error_response(
                error_type="query_execution_error",
                message="Query execution failed. Please check the query syntax and try again.",
                duration_ms=_elapsed_ms(start_time),
            )
        except Exception:
            # NOTE: Never expose internal details or credentials in error responses
            logger.exception(
                "tool_query_connected_source_unexpected_error",
                extra={
                    "source_id": source_id,
                    "query_type": query_type,
                },
            )
            return _error_response(
                error_type="internal_error",
                message="An unexpected error occurred while querying the data source.",
                duration_ms=_elapsed_ms(start_time),
            )

    return query_connected_source


# =============================================================================
# Factory: create_discover_available_sources (for ToolRegistry)
# =============================================================================


def create_discover_available_sources(catalog_service: CatalogService):
    """Factory that creates the discover_available_sources tool function.

    Uses closure to inject the CatalogService dependency, keeping
    the tool function signature clean for agent invocation.

    Args:
        catalog_service: Injected CatalogService for catalog data access.

    Returns:
        Async tool function accepting project_id and returning a semantic
        information landscape of available sources.
    """

    async def discover_available_sources(project_id: str) -> dict[str, Any]:
        """Discover what information is available for a project.

        Returns the semantic information landscape: what data exists across
        all connected sources, organized by domain (Finance, Risk, Resources, etc.)
        with descriptions and query capabilities.

        Use this to understand what enterprise data is available before
        deciding what to query. Each entry includes:
        - semantic_name: Human-friendly name (e.g., "Project Financials")
        - domain: Business domain (e.g., "Finance")
        - description: What information it contains
        - source_type: Where it lives (postgresql/mongodb/document)
        - query_capabilities: What questions it can answer
        - key_fields: Important data fields available

        Args:
            project_id: UUID string of the project to list sources for.

        Returns:
            Dict containing sources list with semantic metadata,
            total_sources count, and project_id.
        """
        logger.info(
            "tool_discover_available_sources_invoked",
            extra={"project_id": project_id},
        )

        try:
            parsed_project_id = UUID(project_id)
        except (ValueError, AttributeError):
            return {
                "error": True,
                "error_type": "validation_error",
                "message": "Invalid project_id format: must be a valid UUID",
                "sources": [],
                "total_sources": 0,
                "project_id": project_id,
            }

        entries = await catalog_service.get_catalog_for_project(parsed_project_id)

        sources: list[dict[str, Any]] = []
        for entry in entries:
            # Extract source_type from the related DataSource
            source_type = (
                entry.data_source.source_type
                if entry.data_source
                else "unknown"
            )

            # Primary domain tag — first tag capitalized, or "General"
            domain = _derive_domain(entry.domain_tags)

            # Extract key field names from the fields JSONB
            key_fields = _extract_key_fields(entry.fields)

            sources.append({
                "source_id": str(entry.source_id),
                "source_type": source_type,
                "semantic_name": entry.semantic_name or entry.object_name,
                "domain": domain,
                "description": entry.semantic_description or "",
                "query_capabilities": entry.query_capabilities or [],
                "key_fields": key_fields,
                "object_name": entry.object_name,
            })

        logger.info(
            "tool_discover_available_sources_completed",
            extra={
                "project_id": project_id,
                "total_sources": len(sources),
            },
        )

        return {
            "sources": sources,
            "total_sources": len(sources),
            "project_id": project_id,
        }

    return discover_available_sources


# =============================================================================
# Strands @tool-decorated functions (for StrandsAgentWrapper)
# =============================================================================


@tool
def query_connected_source(
    source_id: str, query_type: str, query: str
) -> dict:
    """Execute a read-only query against a connected enterprise data source.

    Use this when you need to retrieve data from a connected source identified
    in the catalog. The query must be read-only.

    Args:
        source_id: UUID of the data source from the catalog.
        query_type: "sql" for PostgreSQL, "mongodb" for MongoDB, "jira" for Jira Cloud.
        query: The source-native query as a string.
            For query_type="sql": a SQL SELECT string, e.g.
                "SELECT * FROM jira_issues WHERE project_id = 1"
            For query_type="mongodb": a JSON string with collection and filter, e.g.
                "{\"collection\": \"project_risks\", \"filter\": {\"project_id\": \"ALPHA\"}}"
            For query_type="jira": a JQL string, e.g.
                "project = SCRUM AND status = 'In Progress' ORDER BY created DESC"

    Returns:
        Structured results with columns, rows, row_count, source metadata,
        and execution duration. Results are capped at the configured row limit.
    """
    import asyncio

    repo_factory, encryptor, registry = _get_dependencies()

    async def _execute() -> dict[str, Any]:
        start_time = time.monotonic()

        logger.info(
            "strands_tool_query_connected_source_invoked",
            extra={"source_id": source_id, "query_type": query_type},
        )

        try:
            # Validate source_id
            try:
                parsed_source_id = UUID(source_id)
            except (ValueError, AttributeError):
                return _error_response(
                    error_type="validation_error",
                    message="Invalid source_id format: must be a valid UUID",
                    duration_ms=_elapsed_ms(start_time),
                )

            # Validate query_type
            if query_type not in ("sql", "mongodb", "jira"):
                return _error_response(
                    error_type="validation_error",
                    message=f"Invalid query_type '{query_type}'. Must be 'sql' or 'mongodb'.",
                    duration_ms=_elapsed_ms(start_time),
                )

            # Validate query format — parse JSON string for MongoDB queries
            import json as _json
            parsed_query = query
            if query_type == "mongodb":
                if isinstance(query, str):
                    try:
                        parsed_query = _json.loads(query)
                    except _json.JSONDecodeError:
                        return _error_response(
                            error_type="validation_error",
                            message="For query_type='mongodb', query must be a valid JSON object or array.",
                            duration_ms=_elapsed_ms(start_time),
                        )
                # Accept dict (single query) or list (pipeline)
                if isinstance(parsed_query, dict):
                    parsed_query = parsed_query  # MongoDB connector accepts dict
                elif isinstance(parsed_query, list):
                    parsed_query = parsed_query  # Pipeline format
                else:
                    return _error_response(
                        error_type="validation_error",
                        message="For query_type='mongodb', query must be a JSON object or array.",
                        duration_ms=_elapsed_ms(start_time),
                    )
            elif query_type == "sql" and not isinstance(query, str):
                return _error_response(
                    error_type="validation_error",
                    message="For query_type='sql', query must be a SQL string.",
                    duration_ms=_elapsed_ms(start_time),
                )

            # Validate read-only for SQL
            if query_type == "sql":
                try:
                    validate_read_only_sql(query, source_type="postgresql")
                except QueryValidationError as validation_err:
                    return _error_response(
                        error_type="query_validation_error",
                        message=str(validation_err.message),
                        duration_ms=_elapsed_ms(start_time),
                    )

            # Get a fresh repository for this invocation (thread-local engine)
            import sys
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            from sqlalchemy.ext.asyncio import async_sessionmaker as _asm, create_async_engine as _cae
            from app.dependencies import get_settings
            from app.repositories.data_source_repository import DataSourceRepository as _DSRepo
            from app.repositories.credential_repository import CredentialRepository as _CredRepo

            _settings = get_settings()
            _engine = _cae(_settings.app_db_url, pool_pre_ping=True)
            _factory = _asm(_engine, expire_on_commit=False)

            async with _factory() as _session:
                data_source_repository = _DSRepo(_session)
                credential_repo = _CredRepo(_session)

                # Look up the data source
                data_source = await data_source_repository.get_data_source(parsed_source_id)
                if data_source is None:
                    await _engine.dispose()
                    return _error_response(
                        error_type="source_not_found",
                        message=f"Data source '{source_id}' not found.",
                        duration_ms=_elapsed_ms(start_time),
                    )

                # Get credentials from vault and merge with connection config
                merged_config = dict(data_source.connection_config or {})
                credentials = await credential_repo.get_by_data_source(parsed_source_id)
                for cred in credentials:
                    vault_ref = cred.secret_reference
                    if vault_ref.startswith("vault://fernet/"):
                        encrypted_value = vault_ref[len("vault://fernet/"):]
                        decrypted = encryptor.decrypt_config({cred.credential_type: encrypted_value})
                        merged_config.update(decrypted)

                connector = registry.resolve(
                    source_type=data_source.source_type,
                    connection_config=merged_config,
                )

                # Execute the query
                result: QueryResult = await connector.execute_read(parsed_query)

            await _engine.dispose()

            # Apply row limit
            has_more_rows = result.has_more_rows or result.row_count > _row_limit
            capped_rows = result.rows[:_row_limit]
            capped_row_count = min(result.row_count, _row_limit)

            duration_ms = _elapsed_ms(start_time)

            logger.info(
                "strands_tool_query_connected_source_completed",
                extra={
                    "source_id": source_id,
                    "query_type": query_type,
                    "row_count": capped_row_count,
                    "has_more_rows": has_more_rows,
                    "duration_ms": duration_ms,
                },
            )

            return {
                "columns": result.columns,
                "rows": capped_rows,
                "row_count": capped_row_count,
                "has_more_rows": has_more_rows,
                "source_metadata": {
                    "source_id": source_id,
                    "source_type": data_source.source_type,
                    "source_name": data_source.name,
                    "object_name": _extract_object_name(query_type, query),
                },
                "duration_ms": duration_ms,
            }

        except DataSourceNotFoundError:
            return _error_response(
                error_type="source_not_found",
                message=f"Data source '{source_id}' not found.",
                duration_ms=_elapsed_ms(start_time),
            )
        except QueryExecutionError:
            return _error_response(
                error_type="query_execution_error",
                message="Query execution failed. Please check the query syntax and try again.",
                duration_ms=_elapsed_ms(start_time),
            )
        except Exception:
            logger.exception(
                "strands_tool_query_connected_source_unexpected_error",
                extra={"source_id": source_id, "query_type": query_type},
            )
            return _error_response(
                error_type="internal_error",
                message="An unexpected error occurred while querying the data source.",
                duration_ms=_elapsed_ms(start_time),
            )

    # Bridge synchronous @tool to async implementation
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _execute()).result()
        return loop.run_until_complete(_execute())
    except RuntimeError:
        return asyncio.run(_execute())


@tool
def discover_available_sources(project_id: str) -> dict:
    """Discover what information is available for this project.

    Returns the semantic information landscape: what data exists across
    all connected sources, organized by domain (Finance, Risk, Resources, etc.)
    with descriptions and query capabilities.

    Use this to understand what enterprise data is available before
    deciding what to query. Each entry includes:
    - semantic_name: Human-friendly name (e.g., "Project Financials")
    - domain: Business domain (e.g., "Finance")
    - description: What information it contains
    - source_type: Where it lives (postgresql/mongodb/document)
    - query_capabilities: What questions it can answer
    - key_fields: Important data fields available

    Args:
        project_id: UUID of the project to list sources for.

    Returns:
        List of source summaries organized by semantic domain.
    """
    import asyncio

    catalog_factory = _get_catalog_factory()

    async def _execute() -> dict[str, Any]:
        import sys
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        logger.info(
            "strands_tool_discover_available_sources_invoked",
            extra={"project_id": project_id},
        )

        try:
            parsed_project_id = UUID(project_id)
        except (ValueError, AttributeError):
            return {
                "error": True,
                "error_type": "validation_error",
                "message": "Invalid project_id format: must be a valid UUID",
                "sources": [],
                "total_sources": 0,
                "project_id": project_id,
            }

        # Create thread-local catalog service (fresh engine for new event loop)
        from sqlalchemy.ext.asyncio import async_sessionmaker as asm, create_async_engine as cae
        from app.repositories.catalog_repository import CatalogRepository
        from app.repositories.project_source_mapping_repository import ProjectSourceMappingRepository
        from app.services.catalog_service import CatalogService
        from app.dependencies import get_settings

        settings = get_settings()
        _engine = cae(settings.app_db_url, pool_pre_ping=True)
        _factory = asm(_engine, expire_on_commit=False)

        async with _factory() as session:
            catalog_repo = CatalogRepository(session)
            mapping_repo = ProjectSourceMappingRepository(session)
            catalog_service = CatalogService(
                catalog_repository=catalog_repo,
                project_source_mapping_repository=mapping_repo,
            )
            entries = await catalog_service.get_catalog_for_project(parsed_project_id)

        sources: list[dict[str, Any]] = []
        for entry in entries:
            source_type = (
                entry.data_source.source_type
                if entry.data_source
                else "unknown"
            )
            domain = _derive_domain(entry.domain_tags)
            key_fields = _extract_key_fields(entry.fields)

            sources.append({
                "source_id": str(entry.source_id),
                "source_type": source_type,
                "semantic_name": entry.semantic_name or entry.object_name,
                "domain": domain,
                "description": entry.semantic_description or "",
                "query_capabilities": entry.query_capabilities or [],
                "key_fields": key_fields,
                "object_name": entry.object_name,
            })

        logger.info(
            "strands_tool_discover_available_sources_completed",
            extra={"project_id": project_id, "total_sources": len(sources)},
        )

        return {
            "sources": sources,
            "total_sources": len(sources),
            "project_id": project_id,
        }

    # Bridge synchronous @tool to async implementation
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _execute()).result()
        return loop.run_until_complete(_execute())
    except RuntimeError:
        return asyncio.run(_execute())


# =============================================================================
# Tool list accessor for StrandsAgentWrapper
# =============================================================================


def get_connector_tools() -> list:
    """Return the list of all Strands @tool-decorated connector functions.

    Used by StrandsAgentWrapper to pass tools to the Strands Agent.

    Returns:
        List of tool functions decorated with @tool.
    """
    return [
        query_connected_source,
        discover_available_sources,
    ]


# =============================================================================
# Helper functions
# =============================================================================


def _elapsed_ms(start_time: float) -> int:
    """Calculate elapsed time in milliseconds from a monotonic start."""
    return round((time.monotonic() - start_time) * 1000)


def _error_response(error_type: str, message: str, duration_ms: int) -> dict[str, Any]:
    """Build a standardized error response dict.

    Never includes credentials, stack traces, or internal implementation details.
    """
    return {
        "error": True,
        "error_type": error_type,
        "message": message,
        "duration_ms": duration_ms,
    }


def _extract_object_name(query_type: str, query: str | list[dict]) -> str:
    """Best-effort extraction of the target object name from the query.

    For SQL: attempts to find the table name after FROM.
    For MongoDB: returns "aggregation_pipeline" as collection is implicit.
    """
    if query_type == "sql" and isinstance(query, str):
        return _extract_table_from_sql(query)
    return "aggregation_pipeline"


def _extract_table_from_sql(sql: str) -> str:
    """Extract the primary table name from a simple SELECT query.

    Handles basic patterns like:
        SELECT ... FROM table_name WHERE ...
        SELECT ... FROM schema.table_name WHERE ...

    Falls back to "unknown" for complex queries (subqueries, CTEs, joins).
    """
    upper_sql = sql.upper()
    from_idx = upper_sql.find("FROM")
    if from_idx == -1:
        return "unknown"

    # Get text after FROM
    after_from = sql[from_idx + 4:].strip()
    if not after_from:
        return "unknown"

    # Take the first token (table name or schema.table)
    token = ""
    for char in after_from:
        if char in (" ", "\t", "\n", "\r", ";", "("):
            break
        token += char

    return token if token else "unknown"


def _derive_domain(domain_tags: list[str] | None) -> str:
    """Derive a human-friendly domain label from domain tags.

    Uses the first tag as the primary domain, capitalized.
    Falls back to "General" when no tags are present.
    """
    if not domain_tags:
        return "General"
    return domain_tags[0].capitalize()


def _extract_key_fields(fields_data: Any) -> list[str]:
    """Extract field names from the fields JSONB structure.

    Handles both formats:
    - List of dicts with 'name' key: [{"name": "budget", ...}]
    - List of strings: ["budget", "actual_cost"]

    Args:
        fields_data: The fields JSONB value from a CatalogEntry.

    Returns:
        List of field name strings.
    """
    if not fields_data:
        return []

    if isinstance(fields_data, list):
        key_fields: list[str] = []
        for field in fields_data:
            if isinstance(field, dict) and "name" in field:
                key_fields.append(field["name"])
            elif isinstance(field, str):
                key_fields.append(field)
        return key_fields

    return []
