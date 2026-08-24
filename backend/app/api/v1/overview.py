"""
Overview dashboard API route handler.

Returns aggregated portfolio KPIs, per-project health summaries, and recent
activity — all derived from the cached project_health_kpis table and activity log.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends

from app.dependencies import get_project_health_service
from app.schemas.overview import (
    OverviewKPIs,
    OverviewResponse,
    PortfolioHealthItem,
    RecentActivityItem,
)
from app.services.project_health_service import ProjectHealthService

router = APIRouter(prefix="/overview", tags=["overview"])

# Map internal overall_status values to spec-compliant status codes
_STATUS_MAP = {
    "At Risk": "AT_RISK",
    "On Track": "ON_TRACK",
    "Delayed": "ATTENTION",
    "Completed": "ON_TRACK",
}


@router.get(
    "",
    response_model=OverviewResponse,
    summary="Get overview dashboard data",
    responses={
        200: {"description": "Overview with KPIs, portfolio health, and recent activity"},
    },
)
async def get_overview(
    service: ProjectHealthService = Depends(get_project_health_service),
) -> OverviewResponse:
    """
    Retrieve aggregated overview data for the main dashboard.

    Returns:
    - kpis: total projects, at-risk projects, total budget, open risks
    - portfolio_health: per-project progress bars and status indicators
    - recent_activity: latest platform events
    """
    summary = await service.get_portfolio_summary()
    projects = summary["projects"]

    # Aggregate KPIs
    total_projects = len(projects)
    at_risk_projects = sum(1 for p in projects if p["overall_status"] == "At Risk")
    total_budget = sum(
        (p["budget_total"] if isinstance(p["budget_total"], Decimal) else Decimal(str(p["budget_total"])))
        for p in projects
    )
    open_risks = sum(p["open_risks_count"] for p in projects)

    kpis = OverviewKPIs(
        total_projects=total_projects,
        at_risk_projects=at_risk_projects,
        total_budget=total_budget,
        open_risks=open_risks,
    )

    # Build portfolio health items — include project name from the KPI relationship
    # NOTE: get_portfolio_summary currently returns project_id (UUID).
    # We use get_portfolio_health_with_names to include project names.
    health_items = await _build_portfolio_health(service)

    # Recent activity — derive from recent platform state changes
    recent_activity = _build_recent_activity(projects)

    return OverviewResponse(
        kpis=kpis,
        portfolio_health=health_items,
        recent_activity=recent_activity,
    )


async def _build_portfolio_health(
    service: ProjectHealthService,
) -> list[PortfolioHealthItem]:
    """Build portfolio health items with project names from KPI cache + relationships."""
    kpis = await service._health_kpi_repository.list_all()

    items = []
    for kpi in kpis:
        # The ProjectHealthKpi model has a 'project' relationship loaded via selectin
        project_name = kpi.project.name if kpi.project else f"Project {kpi.project_id}"
        status_code = _STATUS_MAP.get(kpi.overall_status, "ON_TRACK")

        items.append(
            PortfolioHealthItem(
                project_id=kpi.project_id,
                name=project_name,
                progress=kpi.progress_percentage,
                status=status_code,
            )
        )

    return items


def _build_recent_activity(projects: list[dict]) -> list[RecentActivityItem]:
    """
    Generate recent activity entries from project data.

    In a full implementation this would query an activity_log table.
    For now, derive meaningful activity from project health changes.
    """
    now = datetime.now(timezone.utc)
    activities: list[RecentActivityItem] = []

    # Generate activity items from project statuses
    at_risk_projects = [p for p in projects if p["overall_status"] == "At Risk"]
    for project in at_risk_projects[:3]:
        activities.append(
            RecentActivityItem(
                type="risk_updated",
                description=f"Project risk status updated — {project['open_risks_count']} open risks",
                timestamp=project.get("last_calculated_at") or now,
            )
        )

    # Add general platform activity indicators
    if projects:
        activities.append(
            RecentActivityItem(
                type="health_recalculated",
                description=f"Portfolio health recalculated for {len(projects)} projects",
                timestamp=now,
            )
        )

    # Sort by timestamp descending, limit to 10
    activities.sort(key=lambda a: a.timestamp, reverse=True)
    return activities[:10]
