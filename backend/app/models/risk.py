"""
Project Risk ORM model for App_DB.

Represents documented risks to project delivery with severity classification,
ownership, and mitigation status tracking. Supports the Project 360 view,
risk dashboards, and AI queries such as "What are the biggest risks?" and
"Why is Project Alpha at risk?"
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class ProjectRisk(AppBase):
    """A documented risk to project delivery with severity and mitigation status."""

    __tablename__ = "project_risks"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    risk_reference: Mapped[str] = mapped_column(
        sa.String(100), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    severity: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    owner: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    identified_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    target_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
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
    project: Mapped["Project"] = relationship("Project", lazy="selectin")

    __table_args__ = (
        sa.CheckConstraint(
            "severity IN ('Critical', 'High', 'Medium', 'Low')",
            name="severity",
        ),
        sa.CheckConstraint(
            "status IN ('Open', 'Mitigated', 'Closed')",
            name="status",
        ),
        sa.Index(
            "ix_project_risks_project_id_severity", "project_id", "severity"
        ),
        sa.Index(
            "ix_project_risks_project_id_status", "project_id", "status"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectRisk id={self.id} "
            f"risk_reference={self.risk_reference} "
            f"severity={self.severity} status={self.status}>"
        )
