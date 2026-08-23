"""
Portfolio API route handlers.

Thin route layer: delegates to ProjectHealthService, returns typed response.
No business logic, no direct database access.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_project_health_service
from app.schemas.health import PortfolioSummaryResponse
from app.services.project_health_service import ProjectHealthService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get(
    "/summary",
    response_model=PortfolioSummaryResponse,
    summary="Get portfolio-level project health summary",
    responses={
        200: {"description": "Portfolio summary with all project health KPIs"},
    },
)
async def get_portfolio_summary(
    service: ProjectHealthService = Depends(get_project_health_service),
) -> PortfolioSummaryResponse:
    """
    Retrieve portfolio-level health summary for all projects.

    Returns aggregated health KPI data from the cached project_health_kpis
    table, including status counts and per-project health metrics.
    """
    summary = await service.get_portfolio_summary()

    projects = summary["projects"]
    on_track_count = sum(1 for p in projects if p["overall_status"] == "On Track")
    at_risk_count = sum(1 for p in projects if p["overall_status"] == "At Risk")
    delayed_count = sum(1 for p in projects if p["overall_status"] == "Delayed")
    completed_count = sum(1 for p in projects if p["overall_status"] == "Completed")

    return PortfolioSummaryResponse(
        total_projects=len(projects),
        on_track_count=on_track_count,
        at_risk_count=at_risk_count,
        delayed_count=delayed_count,
        completed_count=completed_count,
        projects=projects,
    )
