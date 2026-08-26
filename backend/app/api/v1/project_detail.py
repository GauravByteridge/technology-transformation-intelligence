"""
Project Detail API — serves individual project data for Project 360 page.

Queries the external technology_transformation DB for a specific project's
financials, progress, risks, milestones, resources, issues, and actions.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncpg

router = APIRouter(prefix="/pmo/projects", tags=["pmo"])

EXT_DB_DSN = "postgresql://postgres:master@localhost:5432/technology_transformation"


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class FinanceDetail(BaseModel):
    budget: float
    actual_cost: float
    forecast_cost: float | None = None
    variance: float | None = None
    variance_percentage: float | None = None


class ProgressSnapshot(BaseModel):
    planned_percent: float
    actual_percent: float
    status_date: str
    notes: str | None = None


class RiskItem(BaseModel):
    risk_id: str
    severity: str
    status: str
    category: str | None = None
    description: str | None = None
    owner: str | None = None
    due_date: str | None = None


class MilestoneItem(BaseModel):
    name: str
    planned_date: str | None = None
    actual_date: str | None = None
    status: str


class ResourceItem(BaseModel):
    employee_name: str | None = None
    role: str | None = None
    allocation_percent: float | None = None
    utilization_percent: float | None = None


class JiraIssueItem(BaseModel):
    issue_key: str
    summary: str
    status: str
    priority: str
    assignee: str | None = None
    story_points: int | None = None
    due_date: str | None = None


class AuditFindingItem(BaseModel):
    finding_id: str
    severity: str
    status: str
    description: str | None = None
    due_date: str | None = None


class ActionItem(BaseModel):
    action: str
    owner: str | None = None
    due_date: str | None = None
    status: str
    source: str | None = None
    times_repeated: int = 1


class ITControlItem(BaseModel):
    control_id: str
    control_name: str
    compliance_status: str
    last_tested: str | None = None


class ProjectDetailResponse(BaseModel):
    code: str
    name: str
    overall_status: str
    schedule_status: str
    budget_status: str
    manager: str | None = None
    department: str | None = None
    finance: FinanceDetail | None = None
    progress: list[ProgressSnapshot]
    risks: list[RiskItem]
    milestones: list[MilestoneItem]
    resources: list[ResourceItem]
    issues: list[JiraIssueItem]
    audit_findings: list[AuditFindingItem]
    actions: list[ActionItem]
    it_controls: list[ITControlItem]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@router.get(
    "/{project_code}",
    response_model=ProjectDetailResponse,
    summary="Get detailed project data by code",
)
async def get_project_detail(project_code: str) -> ProjectDetailResponse:
    """Get full project detail from external technology_transformation DB."""
    conn = await asyncpg.connect(EXT_DB_DSN)

    try:
        # Get project
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE project_code = $1", project_code.upper()
        )
        if not project:
            raise HTTPException(status_code=404, detail=f"Project '{project_code}' not found")

        pid = project["id"]

        # Finance
        finance_row = await conn.fetchrow(
            "SELECT budget, actual_cost, forecast_cost, variance, variance_percentage FROM project_finance WHERE project_id = $1",
            pid
        )
        finance = FinanceDetail(**dict(finance_row)) if finance_row else None

        # Progress (all snapshots for burndown)
        progress_rows = await conn.fetch(
            "SELECT planned_percent, actual_percent, status_date::text, notes FROM project_progress WHERE project_id = $1 ORDER BY status_date",
            pid
        )
        progress = [ProgressSnapshot(**dict(r)) for r in progress_rows]

        # Risks
        risk_rows = await conn.fetch(
            "SELECT risk_id, severity, status, category, description, owner, due_date::text FROM project_risks_ext WHERE project_id = $1 ORDER BY severity DESC",
            pid
        )
        risks = [RiskItem(**dict(r)) for r in risk_rows]

        # Milestones
        milestone_rows = await conn.fetch(
            "SELECT name, planned_date::text, actual_date::text, status FROM project_milestones WHERE project_id = $1 ORDER BY planned_date",
            pid
        )
        milestones = [MilestoneItem(**dict(r)) for r in milestone_rows]

        # Resources
        resource_rows = await conn.fetch(
            "SELECT employee_name, role, allocation_percent, utilization_percent FROM resources WHERE project_id = $1",
            pid
        )
        resources = [ResourceItem(**dict(r)) for r in resource_rows]

        # JIRA Issues
        issue_rows = await conn.fetch(
            "SELECT issue_key, summary, status, priority, assignee, story_points, due_date::text FROM jira_issues WHERE project_id = $1 ORDER BY priority DESC",
            pid
        )
        issues = [JiraIssueItem(**dict(r)) for r in issue_rows]

        # Audit Findings
        audit_rows = await conn.fetch(
            "SELECT finding_id, severity, status, description, due_date::text FROM audit_findings WHERE project_id = $1 ORDER BY severity DESC",
            pid
        )
        audit_findings = [AuditFindingItem(**dict(r)) for r in audit_rows]

        # Unattended Actions
        action_rows = await conn.fetch(
            "SELECT action, owner, due_date::text, status, source, times_repeated FROM unattended_actions WHERE project_id = $1 ORDER BY status, due_date",
            pid
        )
        actions = [ActionItem(**dict(r)) for r in action_rows]

        # IT Controls
        control_rows = await conn.fetch(
            "SELECT control_id, control_name, compliance_status, last_tested::text FROM it_controls WHERE project_id = $1",
            pid
        )
        it_controls = [ITControlItem(**dict(r)) for r in control_rows]

    finally:
        await conn.close()

    return ProjectDetailResponse(
        code=project["project_code"],
        name=project["name"],
        overall_status=project["health"],
        schedule_status=project["schedule_status"],
        budget_status=project["budget_status"],
        manager=project["manager"],
        department=project["department"],
        finance=finance,
        progress=progress,
        risks=risks,
        milestones=milestones,
        resources=resources,
        issues=issues,
        audit_findings=audit_findings,
        actions=actions,
        it_controls=it_controls,
    )
