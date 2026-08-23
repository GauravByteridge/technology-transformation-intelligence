"""Pydantic response schemas for project domain endpoints.

Defines typed response models for finance, JIRA, resource, SDLC, risk,
progress, audit, IT controls, and remediation endpoints. All schemas use
from_attributes mode for ORM compatibility.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Finance
# ---------------------------------------------------------------------------


class BudgetLineItemResponse(BaseModel):
    """A single line item within a project budget."""

    id: UUID
    budget_id: UUID
    cost_category_id: UUID
    planned_amount: Decimal

    model_config = {"from_attributes": True}


class ProjectBudgetResponse(BaseModel):
    """Budget record for a project fiscal year."""

    id: UUID
    project_id: UUID
    fiscal_year: int
    total_budget: Decimal
    approved_date: date | None = None
    status: str
    line_items: list[BudgetLineItemResponse] = []

    model_config = {"from_attributes": True}


class ActualCostResponse(BaseModel):
    """A recorded actual cost entry for a project."""

    id: UUID
    project_id: UUID
    cost_category_id: UUID
    amount: Decimal
    incurred_date: date
    description: str | None = None

    model_config = {"from_attributes": True}


class MonthlyCostTrendResponse(BaseModel):
    """Planned vs actual spending for a single month."""

    id: UUID
    project_id: UUID
    year_month: str
    planned_spend: Decimal
    actual_spend: Decimal
    cumulative_planned: Decimal
    cumulative_actual: Decimal

    model_config = {"from_attributes": True}


class ProjectFinanceResponse(BaseModel):
    """Aggregate finance response for a project."""

    budget: ProjectBudgetResponse | None = None
    actual_costs: list[ActualCostResponse] = []
    total_spent: Decimal
    budget_variance: Decimal
    variance_percentage: Decimal
    monthly_trends: list[MonthlyCostTrendResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# JIRA
# ---------------------------------------------------------------------------


class SprintResponse(BaseModel):
    """A sprint belonging to a project."""

    id: UUID
    project_id: UUID
    name: str
    sprint_number: int
    start_date: date
    end_date: date
    status: str
    goal: str | None = None
    velocity: int | None = None

    model_config = {"from_attributes": True}


class JiraIssueResponse(BaseModel):
    """A JIRA issue tracked within a project."""

    id: UUID
    project_id: UUID
    sprint_id: UUID | None = None
    issue_key: str
    issue_type: str
    summary: str
    description: str | None = None
    status: str
    priority: str
    assignee: str | None = None
    reporter: str | None = None
    story_points: int | None = None
    due_date: date | None = None
    resolved_date: date | None = None

    model_config = {"from_attributes": True}


class ProjectJiraResponse(BaseModel):
    """Aggregate JIRA response including sprints, issues, and metrics."""

    sprints: list[SprintResponse] = []
    issues: list[JiraIssueResponse] = []
    open_issues_count: int = Field(ge=0)
    overdue_issues_count: int = Field(ge=0)
    completion_percentage: Decimal = Field(ge=0)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


class ResourceAllocationResponse(BaseModel):
    """A team member's allocation to a project."""

    id: UUID
    project_id: UUID
    team_member_id: UUID
    allocation_percentage: int = Field(ge=0, le=100)
    start_date: date
    end_date: date | None = None
    role_on_project: str | None = None

    model_config = {"from_attributes": True}


class ResourceForecastResponse(BaseModel):
    """Demand vs capacity forecast for a project in a given month."""

    id: UUID
    project_id: UUID
    year_month: str
    demand_fte: Decimal
    capacity_fte: Decimal
    gap_fte: Decimal

    model_config = {"from_attributes": True}


class ProjectResourceResponse(BaseModel):
    """Aggregate resource response for a project."""

    allocations: list[ResourceAllocationResponse] = []
    utilization_percentage: Decimal | None = None
    capacity_gap: Decimal
    forecasts: list[ResourceForecastResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# SDLC
# ---------------------------------------------------------------------------


class SdlcDeliverableResponse(BaseModel):
    """A deliverable produced by a milestone."""

    id: UUID
    name: str
    description: str | None = None
    status: str
    owner: str | None = None
    due_date: date | None = None
    completion_date: date | None = None

    model_config = {"from_attributes": True}


class SdlcMilestoneResponse(BaseModel):
    """A milestone within an SDLC phase."""

    id: UUID
    name: str
    description: str | None = None
    planned_date: date | None = None
    actual_date: date | None = None
    status: str
    deliverables: list[SdlcDeliverableResponse] = []

    model_config = {"from_attributes": True}


class SdlcPhaseResponse(BaseModel):
    """An SDLC phase for a project."""

    id: UUID
    phase_name: str
    sequence_order: int
    status: str
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    actual_start_date: date | None = None
    actual_end_date: date | None = None
    milestones: list[SdlcMilestoneResponse] = []

    model_config = {"from_attributes": True}


class ProjectSdlcResponse(BaseModel):
    """Aggregate SDLC response for a project."""

    project_id: UUID
    phases: list[SdlcPhaseResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Risks
# ---------------------------------------------------------------------------


class ProjectRiskResponse(BaseModel):
    """A risk record for a project."""

    id: UUID
    project_id: UUID
    risk_reference: str
    title: str
    description: str | None = None
    severity: str
    status: str
    owner: str | None = None
    identified_date: date | None = None
    target_date: date | None = None

    model_config = {"from_attributes": True}


class ProjectRisksResponse(BaseModel):
    """Aggregate risks response for a project."""

    risks: list[ProjectRiskResponse] = []
    open_risks_count: int = Field(ge=0)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


class ProgressSnapshotResponse(BaseModel):
    """A progress measurement snapshot."""

    id: UUID
    snapshot_date: date
    planned_progress_percentage: int = Field(ge=0, le=100)
    actual_progress_percentage: int = Field(ge=0, le=100)

    model_config = {"from_attributes": True}


class ProjectProgressResponse(BaseModel):
    """Aggregate progress response for a project."""

    project_id: UUID
    snapshots: list[ProgressSnapshotResponse] = []
    progress_percentage: int = Field(ge=0, le=100)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Audit Findings
# ---------------------------------------------------------------------------


class AuditFindingResponse(BaseModel):
    """An audit finding for a project."""

    id: UUID
    project_id: UUID
    finding_reference: str
    title: str
    description: str | None = None
    severity: str
    status: str
    identified_date: date | None = None
    target_remediation_date: date | None = None
    actual_remediation_date: date | None = None
    auditor: str | None = None

    model_config = {"from_attributes": True}


class ProjectAuditResponse(BaseModel):
    """Aggregate audit response for a project."""

    findings: list[AuditFindingResponse] = []
    overdue_count: int = Field(ge=0)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# IT Controls
# ---------------------------------------------------------------------------


class ControlAssessmentResponse(BaseModel):
    """A control assessment record for a project."""

    id: UUID
    control_id: UUID
    project_id: UUID
    compliance_status: str
    assessed_date: date | None = None
    assessor: str | None = None
    notes: str | None = None
    next_assessment_date: date | None = None

    model_config = {"from_attributes": True}


class ProjectControlsResponse(BaseModel):
    """Aggregate IT controls response for a project."""

    assessments: list[ControlAssessmentResponse] = []
    compliance_percentage: int = Field(ge=0, le=100)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Remediation
# ---------------------------------------------------------------------------


class RemediationItemResponse(BaseModel):
    """A remediation item linked to an audit finding."""

    id: UUID
    finding_id: UUID
    project_id: UUID
    title: str
    description: str | None = None
    owner: str | None = None
    status: str
    priority: str
    due_date: date
    completion_date: date | None = None

    model_config = {"from_attributes": True}


class ProjectRemediationResponse(BaseModel):
    """Aggregate remediation response for a project."""

    items: list[RemediationItemResponse] = []
    overdue_count: int = Field(ge=0)

    model_config = {"from_attributes": True}
