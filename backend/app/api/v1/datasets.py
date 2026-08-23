"""
Dataset API route handlers.

Thin route layer: validates input, delegates to DatasetService, returns response.
Provides CRUD, preview, query, and confirmation endpoints for datasets.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_dataset_service
from app.schemas.dataset import (
    DatasetConfirmRequest,
    DatasetDetailResponse,
    DatasetPreviewResponse,
    DatasetQueryRequest,
    DatasetQueryResponse,
    DatasetResponse,
)
from app.services.dataset_service import DatasetService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[DatasetResponse],
    summary="List datasets",
)
async def list_datasets(
    project_id: UUID | None = Query(None, description="Filter by project ID"),
    service: DatasetService = Depends(get_dataset_service),
) -> list[dict]:
    """List datasets with optional project filter."""
    return await service.list_datasets(project_id=project_id)


@router.get(
    "/{dataset_id}",
    response_model=DatasetDetailResponse,
    summary="Get dataset details",
    responses={404: {"description": "Dataset not found"}},
)
async def get_dataset(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Retrieve dataset details including columns and regions."""
    try:
        return await service.get_dataset(dataset_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{dataset_id}/preview",
    response_model=DatasetPreviewResponse,
    summary="Preview dataset records",
    responses={404: {"description": "Dataset not found"}},
)
async def preview_dataset(
    dataset_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Max rows to preview"),
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Return sample rows and schema for a dataset preview."""
    try:
        return await service.preview_dataset(dataset_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{dataset_id}/confirm",
    response_model=DatasetDetailResponse,
    summary="Confirm a dataset",
    responses={
        404: {"description": "Dataset not found"},
        409: {"description": "Dataset not in REVIEW_REQUIRED status"},
    },
)
async def confirm_dataset(
    dataset_id: UUID,
    payload: DatasetConfirmRequest,
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Confirm a dataset, transitioning from REVIEW_REQUIRED to READY."""
    try:
        adjustments = payload.model_dump(exclude_unset=True) or None
        return await service.confirm_dataset(dataset_id, adjustments=adjustments)
    except ValueError as exc:
        error_msg = str(exc)
        if "not in REVIEW_REQUIRED" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg,
        ) from exc


@router.post(
    "/{dataset_id}/query",
    response_model=DatasetQueryResponse,
    summary="Query dataset records",
    responses={404: {"description": "Dataset not found"}},
)
async def query_dataset(
    dataset_id: UUID,
    payload: DatasetQueryRequest,
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Query dataset records using JSONB operators with filtering, sorting, and aggregation."""
    try:
        query_params = payload.model_dump(exclude_unset=True)
        # Convert sort dicts to tuples for repository
        if "sort" in query_params and query_params["sort"]:
            query_params["sort"] = [
                (s.get("column", ""), s.get("direction", "asc"))
                for s in query_params["sort"]
            ]
        return await service.query_dataset(dataset_id, query_params)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{dataset_id}",
    response_model=DatasetResponse,
    summary="Update dataset metadata",
    responses={404: {"description": "Dataset not found"}},
)
async def update_dataset(
    dataset_id: UUID,
    payload: DatasetConfirmRequest,
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    """Update dataset metadata fields (name, description, classification, domain)."""
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No fields to update",
            )

        # Use confirm_dataset logic but without status transition for PATCH
        # We directly call get_dataset and then update via service
        dataset = await service.get_dataset(dataset_id)

        # Apply updates directly via the dataset repository
        updated = await service._dataset_repo.update_dataset(dataset_id, updates)
        if updated is None:
            raise ValueError(f"Dataset not found: {dataset_id}")

        return service._to_dataset_summary(updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dataset",
    responses={404: {"description": "Dataset not found"}},
)
async def delete_dataset(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service),
) -> None:
    """Delete a dataset and its associated columns, records, and regions."""
    deleted = await service._dataset_repo.delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset not found: {dataset_id}",
        )
