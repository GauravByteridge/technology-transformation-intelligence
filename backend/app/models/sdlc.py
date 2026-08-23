"""
SDLC lifecycle ORM models for App_DB.

Models represent the software development lifecycle structure per project:
phases → milestones → deliverables. Each project defines a sequence of
phases, each phase contains milestones, and each milestone produces
deliverables.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


# Allowed status values for sdlc_phases
SDLC_PHASE_STATUS_VALUES = ("Not Started", "In Progress", "Completed", "Blocked")


class SdlcPhase(AppBase):
    """A stage in the software development lifecycle for a project."""

    __tablename__ = "sdlc_phases"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    phase_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    sequence_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    planned_start_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    planned_end_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    actual_start_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    actual_end_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    milestones: Mapped[list["SdlcMilestone"]] = relationship(
        "SdlcMilestone", back_populates="phase", lazy="selectin"
    )

    __table_args__ = (
        sa.CheckConstraint(
            sa.column("status").in_(SDLC_PHASE_STATUS_VALUES),
            name="status",
        ),
        sa.Index(
            "ix_sdlc_phases_project_id_sequence_order",
            "project_id",
            "sequence_order",
        ),
    )

    def __repr__(self) -> str:
        return f"<SdlcPhase id={self.id} phase_name={self.phase_name} sequence_order={self.sequence_order}>"


class SdlcMilestone(AppBase):
    """A deliverable checkpoint within an SDLC phase."""

    __tablename__ = "sdlc_milestones"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    phase_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("sdlc_phases.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    planned_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    actual_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    phase: Mapped["SdlcPhase"] = relationship(
        "SdlcPhase", back_populates="milestones"
    )
    deliverables: Mapped[list["SdlcDeliverable"]] = relationship(
        "SdlcDeliverable", back_populates="milestone", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<SdlcMilestone id={self.id} name={self.name}>"


class SdlcDeliverable(AppBase):
    """A deliverable produced by a milestone."""

    __tablename__ = "sdlc_deliverables"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    milestone_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("sdlc_milestones.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    owner: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    due_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    completion_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    # Relationships
    milestone: Mapped["SdlcMilestone"] = relationship(
        "SdlcMilestone", back_populates="deliverables"
    )

    def __repr__(self) -> str:
        return f"<SdlcDeliverable id={self.id} name={self.name}>"
