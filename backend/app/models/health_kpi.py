"""
Project Health KPI ORM model for App_DB.

This table stores DERIVED/CACHED data computed by ProjectHealthService from
underlying authoritative domain tables. It is NOT the authoritative source of
financial, JIRA, resource, audit, or remediation information. The authoritative
sources are:
    - project_budgets / actual_costs → budget_total, budget_spent, budget_variance
    - jira_issues → open_issues_count
    - resource_allocations + resource_utilization → resource_utilization_percentage
    - audit_findings → open_audit_findings_count
    - remediation_items → open_remediation_items_count
    - control_assessments → it_control_compliance_percentage
    - project_risks → open_risks_count
    - project_progress_snapshots → progress_percentage

Derivation Notes:
    resource_utilization_percentage:
        Derived from the average utilization_percentage of team members who have
        an active resource_allocation to the project during the most recent
        utilization month. Only team members with an active allocation during
        that month are included. If project-level utilization cannot be reliably
        derived (e.g., no active allocations or no utilization records), the
        resource_forecasts.gap_fte metric serves as the primary project-level
        resource health indicator.

    progress_percentage:
        Derived from the actual_progress_percentage of the most recent
        project_progress_snapshots record for the project (ordered by
        snapshot_date descending).

The ProjectHealthService recalculates these values and writes them here as a
performance cache for dashboard queries and AI retrieval.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppBase


# Allowed values for overall_status
OVERALL_STATUS_VALUES = ("On Track", "At Risk", "Delayed", "Completed")

# Allowed values for schedule_status
SCHEDULE_STATUS_VALUES = ("On Time", "Delayed", "Ahead")


class ProjectHealthKpi(AppBase):
    """
    Derived/cached aggregation of project health metrics.

    This is a cache table — NOT the authoritative source. ProjectHealthService
    computes KPIs from underlying domain tables (finance, JIRA, resources,
    audit, controls, remediation, risks, progress) and writes results here.

    resource_utilization_percentage derivation:
        Average of utilization_percentage for team members with an active
        resource_allocation to the project in the most recent utilization month.
        Falls back to resource_forecasts.gap_fte if utilization cannot be derived.

    progress_percentage derivation:
        actual_progress_percentage from the most recent project_progress_snapshots
        record for the project.
    """

    __tablename__ = "project_health_kpis"

    id: Mapped[UUID] = mapped_column(sa.UUID, primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("projects.id"), unique=True, nullable=False
    )
    overall_status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    schedule_status: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    budget_total: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    budget_spent: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    budget_variance: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    budget_variance_percentage: Mapped[Decimal] = mapped_column(
        sa.Numeric(15, 2), nullable=False
    )
    progress_percentage: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    resource_utilization_percentage: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 1), nullable=False
    )
    open_issues_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    open_risks_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    open_audit_findings_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    open_remediation_items_count: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    it_control_compliance_percentage: Mapped[int] = mapped_column(
        sa.Integer, nullable=False
    )
    last_calculated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
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
    project: Mapped["Project"] = relationship("Project", lazy="selectin")

    __table_args__ = (
        sa.CheckConstraint(
            "overall_status IN ('On Track', 'At Risk', 'Delayed', 'Completed')",
            name="overall_status",
        ),
        sa.CheckConstraint(
            "schedule_status IN ('On Time', 'Delayed', 'Ahead')",
            name="schedule_status",
        ),
        sa.CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="progress_percentage",
        ),
        sa.CheckConstraint(
            "resource_utilization_percentage >= 0",
            name="resource_utilization_percentage",
        ),
        sa.CheckConstraint(
            "it_control_compliance_percentage >= 0 AND it_control_compliance_percentage <= 100",
            name="it_control_compliance_percentage",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectHealthKpi id={self.id} "
            f"project_id={self.project_id} "
            f"overall_status={self.overall_status}>"
        )
