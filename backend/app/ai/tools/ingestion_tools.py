"""
Ingestion-layer AI tools for Strands Agent consumption.

These tools wrap the Phase 4 IngestionInterface protocol, providing the
Strands Agent with access to document search, evidence retrieval, and
structured dataset operations.

Tool Organization:
- PRIMARY: search_documents, get_evidence (enterprise information retrieval)
- SUPPORTING: list_available_datasets, get_dataset_metadata, query_dataset

Security Invariants:
- Tools never receive credentials or database connections.
- Tools access data exclusively through the IngestionInterface protocol.
- Error messages are sanitized before returning to the agent.
"""

from __future__ import annotations

import logging
from uuid import UUID

from strands import tool

from app.services.ingestion_interface import IngestionInterface

logger = logging.getLogger(__name__)

# =============================================================================
# Module-level dependency reference — set during application startup
# =============================================================================

_ingestion_interface: IngestionInterface | None = None
_db_url: str | None = None


def initialize_ingestion_tools(ingestion: IngestionInterface) -> None:
    """Set the module-level IngestionInterface for tool functions.

    Called once during application startup from dependencies.py.

    Args:
        ingestion: The IngestionInterface implementation to inject.
    """
    global _ingestion_interface  # noqa: PLW0603
    _ingestion_interface = ingestion

    # Cache the DB URL for creating fresh sessions in tool threads
    global _db_url  # noqa: PLW0603
    try:
        from app.dependencies import get_settings
        _db_url = get_settings().app_db_url
    except Exception:
        pass

    logger.info("ingestion_tools_initialized")


def _get_ingestion() -> IngestionInterface:
    """Retrieve the configured IngestionInterface.

    Raises:
        RuntimeError: If initialize_ingestion_tools() has not been called.
    """
    if _ingestion_interface is None:
        raise RuntimeError(
            "Ingestion tools not initialized. "
            "Call initialize_ingestion_tools() during application startup."
        )
    return _ingestion_interface


def _create_thread_local_facade():
    """Create a fresh IngestionFacade with its own session factory for use in a thread.

    This is needed because asyncio.run() in tool threads creates a new event loop,
    and SQLAlchemy async sessions are bound to the loop they were created on.
    """
    import sys
    import asyncio

    # On Windows, asyncpg requires SelectorEventLoop (not ProactorEventLoop)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from app.services.ingestion_facade import IngestionFacade

    if not _db_url:
        raise RuntimeError("DB URL not available for thread-local facade")

    engine = create_async_engine(_db_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    return IngestionFacade(session_factory=factory)


# =============================================================================
# PRIMARY INTELLIGENCE TOOLS
# =============================================================================


@tool
def search_documents(project_id: str, query: str) -> dict:
    """Search ingested documents using semantic similarity.

    Use this when the user asks about reports, findings, meeting notes,
    concerns, recommendations, audit issues, remediation notes, or any
    narrative/unstructured content from project documents.

    Args:
        project_id: UUID of the project to search within.
        query: Natural language search query.

    Returns:
        Search results with excerpts, source files, and similarity scores.
    """
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ingestion = _create_thread_local_facade()

    try:
        parsed_project_id = UUID(project_id)
        results = asyncio.run(
            ingestion.search_documents(project_id=parsed_project_id, query=query)
        )

        return {
            "results": results,
            "result_count": len(results),
            "query": query,
            "source_label": "Document Search",
            "source_type": "document",
        }
    except ValueError as exc:
        return {
            "error": f"Invalid project_id format: {project_id}",
            "source_label": "Document Search",
            "result_count": 0,
            "results": [],
        }
    except Exception as exc:
        logger.error(
            "search_documents_tool_failed",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return {
            "error": "Document search encountered an error. Please try again.",
            "source_label": "Document Search",
            "result_count": 0,
            "results": [],
        }


@tool
def get_evidence(source_id: str, evidence_type: str) -> dict:
    """Retrieve detailed evidence for a specific source.

    Use this when you need full context about a specific document chunk
    or dataset record to ground a claim in your answer.

    Args:
        source_id: UUID of the evidence source (chunk_id or dataset_id).
        evidence_type: Either "document" or "structured".

    Returns:
        Detailed evidence with source traceability.
    """
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ingestion = _create_thread_local_facade()

    if evidence_type not in ("document", "structured"):
        return {
            "error": f"Invalid evidence_type: '{evidence_type}'. Must be 'document' or 'structured'.",
            "source_label": "Evidence Retrieval",
        }

    try:
        parsed_source_id = UUID(source_id)
        evidence = asyncio.run(
            ingestion.get_evidence(source_id=parsed_source_id, evidence_type=evidence_type)
        )

        return {
            "evidence": evidence,
            "evidence_type": evidence_type,
            "source_label": "Evidence Retrieval",
        }
    except ValueError as exc:
        error_msg = str(exc)
        if "invalid" in error_msg.lower() or "uuid" in error_msg.lower():
            return {
                "error": f"Invalid source_id format: {source_id}",
                "source_label": "Evidence Retrieval",
            }
        return {
            "error": "Evidence source not found.",
            "source_label": "Evidence Retrieval",
        }
    except Exception as exc:
        logger.error(
            "get_evidence_tool_failed",
            extra={"source_id": source_id, "evidence_type": evidence_type, "error": str(exc)},
        )
        return {
            "error": "Evidence retrieval encountered an error.",
            "source_label": "Evidence Retrieval",
        }


# =============================================================================
# SUPPORTING DATA TOOLS
# =============================================================================


@tool
def query_dataset(dataset_id: str, query_params: dict) -> dict:
    """Query a structured dataset with filters and aggregations.

    Use this when the user asks about specific values, totals, comparisons,
    costs, budgets, metrics, or filtered data from tabular sources.

    Args:
        dataset_id: UUID of the dataset to query.
        query_params: Query parameters with optional filters, sort, limit, columns, aggregations.

    Returns:
        Matching records, total count, and aggregation results.
    """
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ingestion = _create_thread_local_facade()

    try:
        parsed_dataset_id = UUID(dataset_id)
        result = asyncio.run(
            ingestion.query_dataset(dataset_id=parsed_dataset_id, query_params=query_params)
        )

        return {
            "records": result.get("records", []),
            "total_count": result.get("total_count", 0),
            "aggregations": result.get("aggregations", {}),
            "source_label": "Structured Dataset Query",
            "source_type": "structured",
        }
    except ValueError as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            return {
                "error": f"Dataset not found: {dataset_id}",
                "source_label": "Structured Dataset Query",
                "records": [],
                "total_count": 0,
            }
        return {
            "error": f"Invalid query parameters: {error_msg}",
            "source_label": "Structured Dataset Query",
            "records": [],
            "total_count": 0,
        }
    except Exception as exc:
        logger.error(
            "query_dataset_tool_failed",
            extra={"dataset_id": dataset_id, "error": str(exc)},
        )
        return {
            "error": "Dataset query encountered an error.",
            "source_label": "Structured Dataset Query",
            "records": [],
            "total_count": 0,
        }


@tool
def list_available_datasets(project_id: str = "") -> dict:
    """List all structured datasets available for a project.

    Use this when the user asks what data is available or what datasets exist.

    Args:
        project_id: Optional project UUID to filter by. Empty string returns all.

    Returns:
        List of dataset summaries with names, types, and record counts.
    """
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ingestion = _create_thread_local_facade()

    try:
        parsed_project_id: UUID | None = None
        if project_id and project_id.strip():
            parsed_project_id = UUID(project_id)

        datasets = asyncio.run(
            ingestion.list_available_datasets(project_id=parsed_project_id)
        )

        return {
            "datasets": datasets,
            "dataset_count": len(datasets),
            "source_label": "Dataset Discovery",
            "source_type": "structured",
        }
    except ValueError:
        return {
            "error": f"Invalid project_id format: {project_id}",
            "source_label": "Dataset Discovery",
            "datasets": [],
            "dataset_count": 0,
        }
    except Exception as exc:
        logger.error(
            "list_available_datasets_tool_failed",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return {
            "error": "Failed to list datasets.",
            "source_label": "Dataset Discovery",
            "datasets": [],
            "dataset_count": 0,
        }


@tool
def get_dataset_metadata(dataset_id: str) -> dict:
    """Get schema and column information for a specific dataset.

    Use this when you need to understand a dataset's structure before querying it.

    Args:
        dataset_id: UUID of the dataset to inspect.

    Returns:
        Column names, types, record count, and source information.
    """
    import asyncio
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    ingestion = _create_thread_local_facade()

    try:
        parsed_dataset_id = UUID(dataset_id)
        metadata = asyncio.run(
            ingestion.get_dataset_metadata(dataset_id=parsed_dataset_id)
        )

        return {
            "metadata": metadata,
            "source_label": "Dataset Metadata",
            "source_type": "structured",
        }
    except ValueError as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            return {
                "error": f"Dataset not found: {dataset_id}",
                "source_label": "Dataset Metadata",
            }
        return {
            "error": f"Invalid dataset_id format: {dataset_id}",
            "source_label": "Dataset Metadata",
        }
    except Exception as exc:
        logger.error(
            "get_dataset_metadata_tool_failed",
            extra={"dataset_id": dataset_id, "error": str(exc)},
        )
        return {
            "error": "Failed to retrieve dataset metadata.",
            "source_label": "Dataset Metadata",
        }


# =============================================================================
# Tool list accessor for StrandsAgentWrapper
# =============================================================================


def get_ingestion_tools() -> list:
    """Return the list of all Strands @tool-decorated functions.

    Used by StrandsAgentWrapper to pass tools to the Strands Agent.

    Returns:
        List of tool functions decorated with @tool.
    """
    return [
        search_documents,
        get_evidence,
        query_dataset,
        list_available_datasets,
        get_dataset_metadata,
    ]
