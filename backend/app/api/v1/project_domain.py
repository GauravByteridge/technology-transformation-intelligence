"""
Project domain API route handlers.

Thin route layer for project-scoped domain data endpoints.
Each handler validates input, delegates to the appropriate domain service,
and returns a typed Pydantic response. No business logic lives here.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_audit_finding_service,
    get_control_service,
    get_finance_service,
    get_jira_service,
    get_progress_service,
    get_project_health_service,
    get_remediation_service,
    get_resource_service,
    get_risk_service,
    get_sdlc_service,
)
from app.schemas.health import ProjectHealthResponse
from app.schemas.project_domain import (
    ProjectAuditResponse,
    ProjectControlsResponse,
    ProjectFinanceResponse,
    ProjectJiraResponse,
    ProjectProgressResponse,
    ProjectRemediationResponse,
    ProjectResourceResponse,
    ProjectRisksResponse,
    ProjectSdlcResponse,
)
from app.services.audit_finding_service import AuditFindingService
from app.services.control_service import ControlService
from app.services.finance_service import FinanceService
from app.services.jira_service import JiraService
from app.services.progress_service import ProgressService
from app.services.project_health_service import ProjectHealthService
from app.services.remediation_service import RemediationService
from app.services.resource_service import ResourceService
from app.services.risk_service import RiskService
from app.services.sdlc_service import SdlcService

router = APIRouter()


@router.get(
    "/{project_id}/health",
    response_model=ProjectHealthResponse,
    summary="Get project health KPIs",
    responses={
        404: {"description": "Project not found or no health data available"},
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_health(
    project_id: UUID,
    service: ProjectHealthService = Depends(get_project_health_service),
) -> ProjectHealthResponse:
    """Retrieve computed health KPIs for a project."""
    data = await service.get_project_health(project_id)
    return ProjectHealthResponse(**data)


@router.get(
    "/{project_id}/finance",
    response_model=ProjectFinanceResponse,
    summary="Get project finance data",
    responses={
        404: {"description": "No finance data for this project"},
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_finance(
    project_id: UUID,
    service: FinanceService = Depends(get_finance_service),
) -> ProjectFinanceResponse:
    """Retrieve budget, costs, variance, and monthly trends for a project."""
    data = await service.get_project_finance(project_id)
    return ProjectFinanceResponse(**data)


@router.get(
    "/{project_id}/jira",
    response_model=ProjectJiraResponse,
    summary="Get project JIRA data",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_jira(
    project_id: UUID,
    service: JiraService = Depends(get_jira_service),
) -> ProjectJiraResponse:
    """Retrieve sprints, issues, and JIRA metrics for a project."""
    data = await service.get_project_jira(project_id)
    return ProjectJiraResponse(**data)


@router.get(
    "/{project_id}/resources",
    response_model=ProjectResourceResponse,
    summary="Get project resource data",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_resources(
    project_id: UUID,
    service: ResourceService = Depends(get_resource_service),
) -> ProjectResourceResponse:
    """Retrieve allocations, utilization, and capacity forecasts for a project."""
    data = await service.get_project_resources(project_id)
    return ProjectResourceResponse(**data)


@router.get(
    "/{project_id}/audit",
    response_model=ProjectAuditResponse,
    summary="Get project audit findings",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_audit(
    project_id: UUID,
    service: AuditFindingService = Depends(get_audit_finding_service),
) -> ProjectAuditResponse:
    """Retrieve audit findings and overdue count for a project."""
    data = await service.get_project_audit(project_id)
    return ProjectAuditResponse(**data)


@router.get(
    "/{project_id}/controls",
    response_model=ProjectControlsResponse,
    summary="Get project IT controls",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_controls(
    project_id: UUID,
    service: ControlService = Depends(get_control_service),
) -> ProjectControlsResponse:
    """Retrieve control assessments and compliance percentage for a project."""
    data = await service.get_project_controls(project_id)
    return ProjectControlsResponse(**data)


@router.get(
    "/{project_id}/remediation",
    response_model=ProjectRemediationResponse,
    summary="Get project remediation items",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_remediation(
    project_id: UUID,
    service: RemediationService = Depends(get_remediation_service),
) -> ProjectRemediationResponse:
    """Retrieve remediation items and overdue count for a project."""
    data = await service.get_project_remediation(project_id)
    return ProjectRemediationResponse(**data)


@router.get(
    "/{project_id}/sdlc",
    response_model=ProjectSdlcResponse,
    summary="Get project SDLC lifecycle",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_sdlc(
    project_id: UUID,
    service: SdlcService = Depends(get_sdlc_service),
) -> ProjectSdlcResponse:
    """Retrieve SDLC phases, milestones, and deliverables for a project."""
    data = await service.get_project_sdlc(project_id)
    return ProjectSdlcResponse(**data)


@router.get(
    "/{project_id}/risks",
    response_model=ProjectRisksResponse,
    summary="Get project risks",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_risks(
    project_id: UUID,
    service: RiskService = Depends(get_risk_service),
) -> ProjectRisksResponse:
    """Retrieve risks and open risk count for a project."""
    data = await service.get_project_risks(project_id)
    return ProjectRisksResponse(**data)


@router.get(
    "/{project_id}/progress",
    response_model=ProjectProgressResponse,
    summary="Get project progress",
    responses={
        422: {"description": "Invalid project ID format"},
    },
)
async def get_project_progress(
    project_id: UUID,
    service: ProgressService = Depends(get_progress_service),
) -> ProjectProgressResponse:
    """Retrieve progress snapshots and current percentage for a project."""
    data = await service.get_project_progress(project_id)
    return ProjectProgressResponse(**data)
