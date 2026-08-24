"""Health check and project health KPI response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response body for the application health check endpoint."""

    status: str


class ProjectHealthResponse(BaseModel):
    """Response schema for a single project's health KPIs.

    Fields are derived from authoritative domain data by ProjectHealthService.
    """

    project_id: UUID
    overall_status: str
    schedule_status: str
    budget_total: Decimal
    budget_spent: Decimal
    budget_variance: Decimal
    budget_variance_percentage: Decimal
    progress_percentage: int = Field(ge=0, le=100)
    resource_utilization_percentage: Decimal = Field(ge=0)
    open_issues_count: int = Field(ge=0)
    open_risks_count: int = Field(ge=0)
    open_audit_findings_count: int = Field(ge=0)
    open_remediation_items_count: int = Field(ge=0)
    it_control_compliance_percentage: int = Field(ge=0, le=100)
    last_calculated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PortfolioProjectSummary(BaseModel):
    """Summary of a single project within the portfolio overview."""

    project_id: UUID
    name: str = ""
    overall_status: str
    schedule_status: str
    budget_total: Decimal
    budget_spent: Decimal
    budget_variance: Decimal
    budget_variance_percentage: Decimal
    progress_percentage: int = Field(ge=0, le=100)
    resource_utilization_percentage: Decimal = Field(ge=0)
    open_issues_count: int = Field(ge=0)
    open_risks_count: int = Field(ge=0)
    open_audit_findings_count: int = Field(ge=0)
    open_remediation_items_count: int = Field(ge=0)
    it_control_compliance_percentage: int = Field(ge=0, le=100)
    last_calculated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PortfolioSummaryResponse(BaseModel):
    """Response schema for the portfolio-level project summary endpoint."""

    total_projects: int
    on_track_count: int
    at_risk_count: int
    delayed_count: int
    completed_count: int
    projects: list[PortfolioProjectSummary]

    model_config = {"from_attributes": True}
