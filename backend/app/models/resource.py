"""
Resource management ORM models for App_DB.

Stores team members, resource allocations to projects, utilization tracking,
and resource demand/capacity forecasts. These tables are the authoritative
source for resource data used by ResourceService and ProjectHealthService.

NOTE: allocation_percentage is constrained to 0–100 via CHECK constraint.
utilization_percentage has NO upper bound — values above 100% represent
over-utilization scenarios (e.g., overtime, weekend work).
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class TeamMember(AppBase):
    """A team member who can be allocated to projects."""

    __tablename__ = "team_members"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        sa.String(255), unique=True, nullable=False
    )
    role: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    department: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    hourly_rate: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(15, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
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

    # Relationships
    allocations: Mapped[list["ResourceAllocation"]] = relationship(
        "ResourceAllocation", back_populates="team_member", lazy="selectin"
    )
    utilization_records: Mapped[list["ResourceUtilization"]] = relationship(
        "ResourceUtilization", back_populates="team_member", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<TeamMember id={self.id} name={self.name} email={self.email}>"


class ResourceAllocation(AppBase):
    """Assignment of a team member to a project with percentage and date range."""

    __tablename__ = "resource_allocations"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    team_member_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("team_members.id"), nullable=False
    )
    allocation_percentage: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    start_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    role_on_project: Mapped[str] = mapped_column(
        sa.String(100), nullable=False
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

    # Relationships
    team_member: Mapped["TeamMember"] = relationship(
        "TeamMember", back_populates="allocations"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="allocation_percentage",
        ),
        sa.Index(
            "ix_resource_allocations_project_id_team_member_id",
            "project_id",
            "team_member_id",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ResourceAllocation id={self.id} project_id={self.project_id} "
            f"team_member_id={self.team_member_id} allocation={self.allocation_percentage}%>"
        )


class ResourceUtilization(AppBase):
    """Monthly utilization record for a team member."""

    __tablename__ = "resource_utilization"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    team_member_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("team_members.id"), nullable=False
    )
    year_month: Mapped[str] = mapped_column(
        sa.String(7), nullable=False
    )
    available_hours: Mapped[Decimal] = mapped_column(
        sa.Numeric, nullable=False
    )
    billed_hours: Mapped[Decimal] = mapped_column(
        sa.Numeric, nullable=False
    )
    utilization_percentage: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 1), nullable=False
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

    # Relationships
    team_member: Mapped["TeamMember"] = relationship(
        "TeamMember", back_populates="utilization_records"
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "team_member_id",
            "year_month",
            name="uq_resource_utilization_team_member_id_year_month",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ResourceUtilization id={self.id} team_member_id={self.team_member_id} "
            f"year_month={self.year_month} utilization={self.utilization_percentage}%>"
        )


class ResourceForecast(AppBase):
    """Forward-looking resource demand vs capacity projection per project per month."""

    __tablename__ = "resource_forecasts"

    id: Mapped[UUID] = mapped_column(
        sa.UUID, primary_key=True, default=uuid4
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    year_month: Mapped[str] = mapped_column(
        sa.String(7), nullable=False
    )
    demand_fte: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2), nullable=False
    )
    capacity_fte: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2), nullable=False
    )
    gap_fte: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2), nullable=False
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
        sa.UniqueConstraint(
            "project_id",
            "year_month",
            name="uq_resource_forecasts_project_id_year_month",
        ),
        sa.Index(
            "ix_resource_forecasts_project_id_year_month",
            "project_id",
            "year_month",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ResourceForecast id={self.id} project_id={self.project_id} "
            f"year_month={self.year_month} gap_fte={self.gap_fte}>"
        )
