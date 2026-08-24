"""
Executive Briefs API endpoints.

Provides CRUD operations for AI-generated executive briefs,
including generation, listing, and detail views.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_app_db_session
from app.models import ExecutiveBrief, BriefSource
from app.schemas.executive_brief import (
    ExecutiveBriefCreate,
    ExecutiveBriefListResponse,
    ExecutiveBriefResponse,
)

import sqlalchemy as sa

router = APIRouter()


@router.get("/", response_model=list[ExecutiveBriefListResponse])
async def list_briefs(
    project_id: UUID | None = None,
    session: AsyncSession = Depends(get_app_db_session),
) -> list[ExecutiveBriefListResponse]:
    """List executive briefs, optionally filtered by project."""
    query = sa.select(ExecutiveBrief).order_by(ExecutiveBrief.created_at.desc())
    if project_id:
        query = query.where(ExecutiveBrief.project_id == project_id)
    result = await session.execute(query)
    briefs = result.scalars().all()
    return [ExecutiveBriefListResponse.model_validate(b) for b in briefs]


@router.get("/{brief_id}", response_model=ExecutiveBriefResponse)
async def get_brief(
    brief_id: UUID,
    session: AsyncSession = Depends(get_app_db_session),
) -> ExecutiveBriefResponse:
    """Get a single executive brief with sources."""
    result = await session.execute(
        sa.select(ExecutiveBrief).where(ExecutiveBrief.id == brief_id)
    )
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Executive brief not found",
        )
    return ExecutiveBriefResponse.model_validate(brief)


@router.post("/", response_model=ExecutiveBriefResponse, status_code=status.HTTP_201_CREATED)
async def create_brief(
    payload: ExecutiveBriefCreate,
    session: AsyncSession = Depends(get_app_db_session),
) -> ExecutiveBriefResponse:
    """Create a new executive brief (triggers AI generation)."""
    # NOTE: In a full implementation, this would invoke the AI service
    # to generate the brief content from project data. For now, creates
    # a draft record that the AI service can populate asynchronously.
    brief = ExecutiveBrief(
        project_id=payload.project_id,
        title=payload.title,
        status="generating",
        # TODO(AI): Replace with actual authenticated user ID
        created_by="00000000-0000-0000-0000-000000000001",
    )
    session.add(brief)
    await session.commit()
    await session.refresh(brief)
    return ExecutiveBriefResponse.model_validate(brief)


@router.delete("/{brief_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brief(
    brief_id: UUID,
    session: AsyncSession = Depends(get_app_db_session),
) -> None:
    """Delete an executive brief."""
    result = await session.execute(
        sa.select(ExecutiveBrief).where(ExecutiveBrief.id == brief_id)
    )
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Executive brief not found",
        )
    await session.delete(brief)
    await session.commit()
