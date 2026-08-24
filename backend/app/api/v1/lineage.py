"""
Lineage API endpoints.

Provides lineage graph retrieval for a given query execution.
The lineage shows how an AI answer was constructed from data sources.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_app_db_session
from app.models import LineageRun
from app.schemas.lineage import LineageRunResponse

import sqlalchemy as sa

router = APIRouter()


@router.get("/{query_id}", response_model=LineageRunResponse)
async def get_lineage_for_query(
    query_id: UUID,
    session: AsyncSession = Depends(get_app_db_session),
) -> LineageRunResponse:
    """Get the lineage graph for a specific query execution."""
    result = await session.execute(
        sa.select(LineageRun).where(LineageRun.query_id == query_id)
    )
    lineage_run = result.scalar_one_or_none()
    if not lineage_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lineage data not found for this query",
        )
    return LineageRunResponse.model_validate(lineage_run)
