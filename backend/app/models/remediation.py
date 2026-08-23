"""
Remediation Item ORM model for App_DB.

Represents action items linked to audit findings, with assigned owners,
priority classification, status tracking, and due date management.

Overdue Condition (Derived State):
    A remediation item is considered "overdue" when BOTH conditions are met:
      1. status IN ("Open", "In Progress")
      2. due_date < today (i.e., the due date is in the past)

    This is a derived/computed state — there is no literal "Overdue" status value.
    The overdue condition should be evaluated at query time or in the service layer,
    not stored as a column or status enum value.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class RemediationItem(AppBase):
    """
    An action item linked to an audit finding requiring remediation.

    Overdue Condition (Derived):
        A remediation item is overdue when:
        - status is "Open" or "In Progress", AND
        - due_date is before today's date.

        This is NOT a stored status value — it must be computed at runtime.
    """

    __tablename__ = "remediation_items"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    finding_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("audit_findings.id"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    owner: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    priority: Mapped[str] = mapped_column(sa.String(50), nullable=False)
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
    finding: Mapped["AuditFinding"] = relationship(
        "AuditFinding", back_populates="remediation_items", lazy="selectin"
    )
    project: Mapped["Project"] = relationship("Project", lazy="selectin")

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('Open', 'In Progress', 'Completed', 'Cancelled')",
            name="status",
        ),
        sa.CheckConstraint(
            "priority IN ('Critical', 'High', 'Medium', 'Low')",
            name="priority",
        ),
        sa.Index(
            "ix_remediation_items_project_id_status", "project_id", "status"
        ),
        sa.Index(
            "ix_remediation_items_finding_id", "finding_id"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RemediationItem id={self.id} "
            f"finding_id={self.finding_id} "
            f"status={self.status} priority={self.priority}>"
        )
