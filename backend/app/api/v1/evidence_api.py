"""
Evidence and Query Source Usage API endpoints.

Provides access to the structured evidence and source attribution
data for AI query answers. Powers the Evidence Panel and
Sources Consulted UI.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_app_db_session
from app.models import QueryHistory, QuerySourceUsage, Evidence
from app.schemas.query_source import (
    EvidenceResponse,
    QueryDetailResponse,
    QuerySourceUsageResponse,
)

import sqlalchemy as sa

router = APIRouter()


@router.get("/queries/{query_id}/detail", response_model=QueryDetailResponse)
async def get_query_detail(
    query_id: UUID,
    session: AsyncSession = Depends(get_app_db_session),
) -> QueryDetailResponse:
    """Get full query detail with sources and evidence."""
    result = await session.execute(
        sa.select(QueryHistory).where(QueryHistory.id == query_id)
    )
    query_record = result.scalar_one_or_none()
    if not query_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query record not found",
        )

    # Fetch source usages
    sources_result = await session.execute(
        sa.select(QuerySourceUsage)
        .where(QuerySourceUsage.query_id == query_id)
        .order_by(QuerySourceUsage.created_at)
    )
    sources = sources_result.scalars().all()

    # Fetch evidence
    evidence_result = await session.execute(
        sa.select(Evidence)
        .where(Evidence.query_id == query_id)
        .order_by(Evidence.created_at)
    )
    evidence_items = evidence_result.scalars().all()

    return QueryDetailResponse(
        id=query_record.id,
        query_id=query_record.query_id,
        conversation_id=query_record.conversation_id,
        project_id=query_record.project_id,
        question=query_record.question,
        response=query_record.response,
        is_partial=query_record.is_partial,
        llm_provider=query_record.llm_provider,
        duration_ms=query_record.duration_ms,
        sources=[QuerySourceUsageResponse.model_validate(s) for s in sources],
        evidence=[EvidenceResponse.model_validate(e) for e in evidence_items],
        created_at=query_record.created_at,
    )


@router.get("/queries/{query_id}/sources", response_model=list[QuerySourceUsageResponse])
async def get_query_sources(
    query_id: UUID,
    session: AsyncSession = Depends(get_app_db_session),
) -> list[QuerySourceUsageResponse]:
    """Get sources consulted for a specific query."""
    result = await session.execute(
        sa.select(QuerySourceUsage)
        .where(QuerySourceUsage.query_id == query_id)
        .order_by(QuerySourceUsage.created_at)
    )
    sources = result.scalars().all()
    return [QuerySourceUsageResponse.model_validate(s) for s in sources]


@router.get("/queries/{query_id}/evidence", response_model=list[EvidenceResponse])
async def get_query_evidence(
    query_id: UUID,
    session: AsyncSession = Depends(get_app_db_session),
) -> list[EvidenceResponse]:
    """Get all evidence items for a specific query."""
    result = await session.execute(
        sa.select(Evidence)
        .where(Evidence.query_id == query_id)
        .order_by(Evidence.created_at)
    )
    items = result.scalars().all()
    return [EvidenceResponse.model_validate(e) for e in items]
