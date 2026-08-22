"""
Query history API route handlers.

Thin route layer for query history (append-only) and saved queries.
No PATCH/DELETE on query_history — records are append-only by design.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_query_history_service
from app.schemas.query_history import (
    QueryHistoryCreate,
    QueryHistoryResponse,
    SavedQueryCreate,
    SavedQueryResponse,
)
from app.services.query_history_service import QueryHistoryService

router = APIRouter()


@router.post(
    "",
    response_model=QueryHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a query history record",
    responses={
        404: {"description": "Project not found"},
        422: {"description": "Validation error"},
    },
)
async def create_query_history(
    payload: QueryHistoryCreate,
    service: QueryHistoryService = Depends(get_query_history_service),
) -> QueryHistoryResponse:
    """Record a new AI query execution (append-only)."""
    result = await service.create_query_history(
        project_id=payload.project_id,
        conversation_id=payload.conversation_id,
        query_id=payload.query_id,
        question=payload.question,
        response=payload.response,
        tools_invoked=payload.tools_invoked,
        sources_consulted=payload.sources_consulted,
        is_partial=payload.is_partial,
        llm_provider=payload.llm_provider,
        llm_model=payload.llm_model,
        prompt_version=payload.prompt_version,
        duration_ms=payload.duration_ms,
    )
    return QueryHistoryResponse(**result)


@router.get(
    "",
    response_model=list[QueryHistoryResponse],
    summary="List query history for a project",
)
async def list_query_history(
    project_id: UUID = Query(description="Filter query history by project ID"),
    service: QueryHistoryService = Depends(get_query_history_service),
) -> list[QueryHistoryResponse]:
    """List query history records ordered by most recent first."""
    results = await service.list_by_project(project_id)
    return [QueryHistoryResponse(**r) for r in results]


@router.get(
    "/saved",
    response_model=list[SavedQueryResponse],
    summary="List saved queries for a project",
)
async def list_saved_queries(
    project_id: UUID = Query(description="Filter saved queries by project ID"),
    service: QueryHistoryService = Depends(get_query_history_service),
) -> list[SavedQueryResponse]:
    """List all saved queries for the given project."""
    results = await service.list_saved_by_project(project_id)
    return [SavedQueryResponse(**r) for r in results]


@router.post(
    "/saved",
    response_model=SavedQueryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a saved query",
    responses={
        404: {"description": "Project not found"},
        422: {"description": "Validation error"},
    },
)
async def create_saved_query(
    payload: SavedQueryCreate,
    service: QueryHistoryService = Depends(get_query_history_service),
) -> SavedQueryResponse:
    """Save a query for quick reuse."""
    result = await service.create_saved_query(
        project_id=payload.project_id,
        title=payload.title,
        question=payload.question,
    )
    return SavedQueryResponse(**result)


@router.get(
    "/{query_history_id}",
    response_model=QueryHistoryResponse,
    summary="Get a query history record",
    responses={
        404: {"description": "Query history record not found"},
        422: {"description": "Invalid query history ID format"},
    },
)
async def get_query_history(
    query_history_id: UUID,
    service: QueryHistoryService = Depends(get_query_history_service),
) -> QueryHistoryResponse:
    """Retrieve a single query history record by ID."""
    result = await service.get_query_history(query_history_id)
    return QueryHistoryResponse(**result)


@router.delete(
    "/saved/{saved_query_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved query",
    responses={404: {"description": "Saved query not found"}},
)
async def delete_saved_query(
    saved_query_id: UUID,
    service: QueryHistoryService = Depends(get_query_history_service),
) -> None:
    """Delete a saved query by its UUID."""
    await service.delete_saved_query(saved_query_id)
