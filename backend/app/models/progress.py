"""
Project progress snapshot ORM model for App_DB.

Stores point-in-time records of planned vs actual progress percentage
per project. Used for burn-down/progress trend charts and AI trend analysis.

Both planned_progress_percentage and actual_progress_percentage are
constrained to the range 0–100 via CHECK constraints.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AppBase


class ProjectProgressSnapshot(AppBase):
    """Point-in-time record of planned vs actual progress for a project."""

    __tablename__ = "project_progress_snapshots"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    planned_progress_percentage: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    actual_progress_percentage: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        sa.CheckConstraint(
            "planned_progress_percentage >= 0 AND planned_progress_percentage <= 100",
            name="planned_progress_percentage",
        ),
        sa.CheckConstraint(
            "actual_progress_percentage >= 0 AND actual_progress_percentage <= 100",
            name="actual_progress_percentage",
        ),
        sa.UniqueConstraint(
            "project_id",
            "snapshot_date",
            name="uq_project_progress_snapshots_project_id_snapshot_date",
        ),
        sa.Index(
            "ix_project_progress_snapshots_project_id_snapshot_date",
            "project_id",
            "snapshot_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectProgressSnapshot id={self.id} project_id={self.project_id} "
            f"snapshot_date={self.snapshot_date} "
            f"planned={self.planned_progress_percentage}% actual={self.actual_progress_percentage}%>"
        )
