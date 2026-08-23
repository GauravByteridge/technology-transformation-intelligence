"""
Audit Finding ORM model for App_DB.

Represents compliance or risk observations identified during audits,
with severity classification, remediation timelines, and status tracking.

Overdue Condition (Derived State):
    An audit finding is considered "overdue" when BOTH conditions are met:
      1. status IN ("Open", "In Progress")
      2. target_remediation_date < today (i.e., target date is in the past)

    This is a derived/computed state — there is no literal "Overdue" status value.
    The overdue condition should be evaluated at query time or in the service layer,
    not stored as a column or status enum value.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


class AuditFinding(AppBase):
    """
    A compliance or risk observation identified during an audit.

    Overdue Condition (Derived):
        An audit finding is overdue when:
        - status is "Open" or "In Progress", AND
        - target_remediation_date is not None and is before today's date.

        This is NOT a stored status value — it must be computed at runtime.
    """

    __tablename__ = "audit_findings"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), nullable=False
    )
    finding_reference: Mapped[str] = mapped_column(
        sa.String(100), unique=True, nullable=False
    )
    title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    severity: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    identified_date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    target_remediation_date: Mapped[date | None] = mapped_column(
        sa.Date, nullable=True
    )
    actual_remediation_date: Mapped[date | None] = mapped_column(
        sa.Date, nullable=True
    )
    auditor: Mapped[str] = mapped_column(sa.String(255), nullable=False)
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
    remediation_items: Mapped[list["RemediationItem"]] = relationship(
        "RemediationItem", back_populates="finding", lazy="selectin"
    )

    __table_args__ = (
        sa.CheckConstraint(
            "severity IN ('Critical', 'High', 'Medium', 'Low')",
            name="severity",
        ),
        sa.CheckConstraint(
            "status IN ('Open', 'In Progress', 'Closed')",
            name="status",
        ),
        sa.Index(
            "ix_audit_findings_project_id_severity", "project_id", "severity"
        ),
        sa.Index(
            "ix_audit_findings_project_id_status", "project_id", "status"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditFinding id={self.id} "
            f"finding_reference={self.finding_reference} "
            f"severity={self.severity} status={self.status}>"
        )
