"""
PMO Overview API — serves data for the AI PMO Dashboard.

Queries the external technology_transformation PostgreSQL database for project
health, risks, finance, progress, and unattended actions. Also queries app_db
for project metadata.

This endpoint is read-only and aggregates data across sources.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
import asyncpg

from app.services.jira_live import count_critical_defects, get_jira_project_key

router = APIRouter(prefix="/pmo", tags=["pmo"])

# External DB connection (technology_transformation)
EXT_DB_DSN = "postgresql://postgres:master@localhost:5432/technology_transformation"


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class PMOProject(BaseModel):
    id: int
    code: str
    name: str
    overall_status: str  # Red, Amber, Green
    schedule_status: str
    budget_status: str
    manager: str | None = None
    department: str | None = None
    budget: float | None = None
    actual_cost: float | None = None
    variance_percentage: float | None = None
    planned_percent: float | None = None
    actual_percent: float | None = None
    open_risks: int = 0
    high_severity_risks: int = 0
    overdue_actions: int = 0
    critical_defects: int = 0


class PMOAttentionItem(BaseModel):
    project_code: str
    project_name: str
    overall_status: str
    items: list[str]
    ai_assessment: str


class UnattendedAction(BaseModel):
    id: int
    project_code: str
    action: str
    owner: str | None = None
    due_date: str | None = None
    status: str
    source: str | None = None
    times_repeated: int = 1


class PMOOverviewResponse(BaseModel):
    total_projects: int
    projects_at_risk: int
    high_severity_risks: int
    overdue_actions: int
    budget_variance_projects: int
    projects: list[PMOProject]
    attention_items: list[PMOAttentionItem]
    unattended_actions: list[UnattendedAction]


# ---------------------------------------------------------------------------
# API Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PMOOverviewResponse,
    summary="Get PMO Overview dashboard data",
)
async def get_pmo_overview() -> PMOOverviewResponse:
    """
    Aggregate PMO dashboard data from the external technology_transformation DB.
    Returns project health, risks, finance, progress, and unattended actions.
    """
    conn = await asyncpg.connect(EXT_DB_DSN)

    try:
        # Get projects with latest finance and progress
        projects_raw = await conn.fetch("""
            SELECT
                p.id, p.project_code, p.name, p.health, p.schedule_status,
                p.budget_status, p.manager, p.department,
                pf.budget, pf.actual_cost, pf.variance_percentage,
                pp.planned_percent, pp.actual_percent
            FROM projects p
            LEFT JOIN project_finance pf ON pf.project_id = p.id
            LEFT JOIN (
                SELECT DISTINCT ON (project_id) project_id, planned_percent, actual_percent
                FROM project_progress
                ORDER BY project_id, status_date DESC
            ) pp ON pp.project_id = p.id
            ORDER BY p.id
        """)

        # Get risk counts per project
        risk_counts = await conn.fetch("""
            SELECT project_id,
                   COUNT(*) as total_risks,
                   COUNT(*) FILTER (WHERE severity IN ('Critical', 'High', 'HIGH')) as high_risks
            FROM project_risks_ext
            WHERE status = 'Open'
            GROUP BY project_id
        """)
        risk_map = {r["project_id"]: (r["total_risks"], r["high_risks"]) for r in risk_counts}

        # Get overdue action counts per project
        overdue_counts = await conn.fetch("""
            SELECT project_id, COUNT(*) as count
            FROM unattended_actions
            WHERE status = 'Overdue'
            GROUP BY project_id
        """)
        overdue_map = {r["project_id"]: r["count"] for r in overdue_counts}

        # Get critical defect counts (from Jira Cloud API)
        # We'll populate this after fetching project codes
        defect_map: dict[int, int] = {}

        # Get all unattended actions
        actions_raw = await conn.fetch("""
            SELECT ua.id, p.project_code, ua.action, ua.owner,
                   ua.due_date::text, ua.status, ua.source, ua.times_repeated
            FROM unattended_actions ua
            JOIN projects p ON p.id = ua.project_id
            ORDER BY
                CASE ua.status WHEN 'Overdue' THEN 0 ELSE 1 END,
                ua.due_date ASC
        """)

        # Get attention items (risks + actions for non-Green projects)
        attention_risks = await conn.fetch("""
            SELECT p.project_code, p.name, p.health, r.description
            FROM project_risks_ext r
            JOIN projects p ON p.id = r.project_id
            WHERE r.status = 'Open' AND r.severity IN ('Critical', 'High', 'HIGH')
              AND p.health != 'Green'
            ORDER BY p.id, r.severity DESC
        """)

    finally:
        await conn.close()

    # Build project list
    projects: list[PMOProject] = []
    for row in projects_raw:
        pid = row["id"]
        total_risks, high_risks = risk_map.get(pid, (0, 0))
        projects.append(PMOProject(
            id=pid,
            code=row["project_code"],
            name=row["name"],
            overall_status=row["health"],
            schedule_status=row["schedule_status"],
            budget_status=row["budget_status"],
            manager=row["manager"],
            department=row["department"],
            budget=float(row["budget"]) if row["budget"] else None,
            actual_cost=float(row["actual_cost"]) if row["actual_cost"] else None,
            variance_percentage=float(row["variance_percentage"]) if row["variance_percentage"] else None,
            planned_percent=float(row["planned_percent"]) if row["planned_percent"] else None,
            actual_percent=float(row["actual_percent"]) if row["actual_percent"] else None,
            open_risks=total_risks,
            high_severity_risks=high_risks,
            overdue_actions=overdue_map.get(pid, 0),
            critical_defects=defect_map.get(pid, 0),
        ))

    # Build attention items
    attention_by_project: dict[str, PMOAttentionItem] = {}
    for row in attention_risks:
        code = row["project_code"]
        if code not in attention_by_project:
            # AI Assessment based on status
            if row["health"] == "Red":
                assessment = "High Risk — Immediate PMO intervention required"
            else:
                assessment = "Needs Attention — Monitor closely"
            attention_by_project[code] = PMOAttentionItem(
                project_code=code,
                project_name=row["name"],
                overall_status=row["health"],
                items=[],
                ai_assessment=assessment,
            )
        attention_by_project[code].items.append(row["description"])

    # Add overdue actions to attention items
    for action in actions_raw:
        code = action["project_code"]
        if code in attention_by_project and action["status"] == "Overdue":
            attention_by_project[code].items.append(f"Overdue: {action['action']} (Owner: {action['owner']})")

    # Build unattended actions list
    unattended_actions = [
        UnattendedAction(
            id=a["id"],
            project_code=a["project_code"],
            action=a["action"],
            owner=a["owner"],
            due_date=a["due_date"],
            status=a["status"],
            source=a["source"],
            times_repeated=a["times_repeated"] or 1,
        )
        for a in actions_raw
    ]

    # Aggregates
    total_projects = len(projects)
    projects_at_risk = sum(1 for p in projects if p.overall_status in ("Red", "Amber"))
    high_severity_risks = sum(p.high_severity_risks for p in projects)
    total_overdue = sum(p.overdue_actions for p in projects)
    budget_variance_projects = sum(1 for p in projects if p.budget_status == "Over Budget")

    return PMOOverviewResponse(
        total_projects=total_projects,
        projects_at_risk=projects_at_risk,
        high_severity_risks=high_severity_risks,
        overdue_actions=total_overdue,
        budget_variance_projects=budget_variance_projects,
        projects=projects,
        attention_items=list(attention_by_project.values()),
        unattended_actions=unattended_actions,
    )


# ---------------------------------------------------------------------------
# Project Detail Endpoint
# ---------------------------------------------------------------------------

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


class JiraIssueItem(BaseModel):
    issue_key: str
    summary: str
    status: str
    priority: str
    assignee: str | None = None
    story_points: int | None = None
    due_date: str | None = None


class ProgressEntry(BaseModel):
    status_date: str
    planned_percent: float
    actual_percent: float


class ProjectDetailResponse(BaseModel):
    code: str
    name: str
    overall_status: str
    schedule_status: str
    budget_status: str
    manager: str | None = None
    department: str | None = None
    budget: float | None = None
    actual_cost: float | None = None
    forecast_cost: float | None = None
    variance: float | None = None
    variance_percentage: float | None = None
    planned_percent: float | None = None
    actual_percent: float | None = None
    open_risks: int = 0
    high_severity_risks: int = 0
    overdue_actions: int = 0
    critical_defects: int = 0
    open_issues: int = 0
    resource_count: int = 0
    avg_utilization: float | None = None
    open_audit_findings: int = 0
    open_remediation_items: int = 0
    it_control_compliance: float | None = None
    risks: list[RiskItem] = []
    milestones: list[MilestoneItem] = []
    jira_issues: list[JiraIssueItem] = []
    progress_history: list[ProgressEntry] = []


@router.get(
    "/{project_code}",
    response_model=ProjectDetailResponse,
    summary="Get detailed project data by code",
)
async def get_project_detail(project_code: str) -> ProjectDetailResponse:
    """
    Fetch detailed project metrics from the external technology_transformation DB.
    Returns financials, risks, milestones, JIRA issues, progress history, and resources.
    """
    conn = await asyncpg.connect(EXT_DB_DSN)

    try:
        # Get project
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE project_code = $1", project_code.upper()
        )
        if not project:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Project '{project_code}' not found")

        pid = project["id"]

        # Finance
        finance = await conn.fetchrow(
            "SELECT * FROM project_finance WHERE project_id = $1 ORDER BY as_of_date DESC LIMIT 1", pid
        )

        # Latest progress
        progress_latest = await conn.fetchrow(
            "SELECT * FROM project_progress WHERE project_id = $1 ORDER BY status_date DESC LIMIT 1", pid
        )

        # Progress history (for burndown chart)
        progress_rows = await conn.fetch(
            "SELECT status_date::text, planned_percent, actual_percent FROM project_progress WHERE project_id = $1 ORDER BY status_date", pid
        )

        # Risks
        risks = await conn.fetch(
            "SELECT risk_id, severity, status, category, description, owner, due_date::text FROM project_risks_ext WHERE project_id = $1 AND status = 'Open' ORDER BY severity", pid
        )

        # Risk counts
        risk_counts = await conn.fetchrow(
            "SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE severity IN ('Critical', 'High', 'HIGH')) as high FROM project_risks_ext WHERE project_id = $1 AND status = 'Open'", pid
        )

        # Milestones
        milestones = await conn.fetch(
            "SELECT name, planned_date::text, actual_date::text, status FROM project_milestones WHERE project_id = $1 ORDER BY planned_date", pid
        )

        # JIRA issues (fetched from Jira Cloud API)
        jira_project_key = get_jira_project_key(project["project_code"])
        from app.services.jira_live import fetch_issues_for_project, count_critical_defects as _count_critical, count_open_issues as _count_open
        jira_issues_live = await fetch_issues_for_project(jira_project_key) if jira_project_key else []

        # Resources
        resource_stats = await conn.fetchrow(
            "SELECT COUNT(*) as count, AVG(utilization_percent) as avg_util FROM resources WHERE project_id = $1", pid
        )

        # Audit findings
        audit_count = await conn.fetchval(
            "SELECT COUNT(*) FROM audit_findings WHERE project_id = $1 AND status != 'Closed'", pid
        )

        # Remediation items
        remediation_count = await conn.fetchval(
            "SELECT COUNT(*) FROM remediation_items WHERE project_id = $1 AND status != 'Closed'", pid
        )

        # IT Controls compliance
        controls = await conn.fetch(
            "SELECT compliance_status FROM it_controls WHERE project_id = $1", pid
        )
        compliant_count = sum(1 for c in controls if c["compliance_status"] == "Compliant")
        compliance_pct = (compliant_count / len(controls) * 100) if controls else None

        # Overdue actions
        overdue_count = await conn.fetchval(
            "SELECT COUNT(*) FROM unattended_actions WHERE project_id = $1 AND status = 'Overdue'", pid
        )

        # Critical defects (from Jira Cloud API)
        critical_count = await _count_critical(jira_project_key) if jira_project_key else 0

        # Open issues count (from Jira Cloud API)
        open_issues = await _count_open(jira_project_key) if jira_project_key else 0

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
        budget=float(finance["budget"]) if finance else None,
        actual_cost=float(finance["actual_cost"]) if finance else None,
        forecast_cost=float(finance["forecast_cost"]) if finance else None,
        variance=float(finance["variance"]) if finance else None,
        variance_percentage=float(finance["variance_percentage"]) if finance else None,
        planned_percent=float(progress_latest["planned_percent"]) if progress_latest else None,
        actual_percent=float(progress_latest["actual_percent"]) if progress_latest else None,
        open_risks=risk_counts["total"] if risk_counts else 0,
        high_severity_risks=risk_counts["high"] if risk_counts else 0,
        overdue_actions=overdue_count or 0,
        critical_defects=critical_count or 0,
        open_issues=open_issues or 0,
        resource_count=resource_stats["count"] if resource_stats else 0,
        avg_utilization=float(resource_stats["avg_util"]) if resource_stats and resource_stats["avg_util"] else None,
        open_audit_findings=audit_count or 0,
        open_remediation_items=remediation_count or 0,
        it_control_compliance=compliance_pct,
        risks=[RiskItem(
            risk_id=r["risk_id"], severity=r["severity"], status=r["status"],
            category=r["category"], description=r["description"],
            owner=r["owner"], due_date=r["due_date"]
        ) for r in risks],
        milestones=[MilestoneItem(
            name=m["name"], planned_date=m["planned_date"],
            actual_date=m["actual_date"], status=m["status"]
        ) for m in milestones],
        jira_issues=[JiraIssueItem(
            issue_key=j.issue_key, summary=j.summary, status=j.status,
            priority=j.priority, assignee=j.assignee,
            story_points=j.story_points, due_date=j.due_date
        ) for j in jira_issues_live],
        progress_history=[ProgressEntry(
            status_date=p["status_date"],
            planned_percent=float(p["planned_percent"]),
            actual_percent=float(p["actual_percent"])
        ) for p in progress_rows],
    )
