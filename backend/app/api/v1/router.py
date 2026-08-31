"""
API v1 router aggregating all domain route modules.

New domain routes are added here as sub-routers.
"""

from fastapi import APIRouter

from app.api.v1.ai_queries import router as ai_queries_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.config import router as config_router
from app.api.v1.data_sources import router as data_sources_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.documents import router as documents_router
from app.api.v1.gmail import router as gmail_router
from app.api.v1.health import router as health_router
from app.api.v1.outlook import router as outlook_router
from app.api.v1.overview import router as overview_router
from app.api.v1.pmo import router as pmo_router
from app.api.v1.project_detail import router as project_detail_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.project_domain import router as project_domain_router
from app.api.v1.projects import router as projects_router
from app.api.v1.query_history import router as query_history_router
from app.api.v1.upload import router as upload_router

api_router = APIRouter()

# Health check — required for load balancers and orchestrators
api_router.include_router(health_router)

# Domain routers
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(project_domain_router, prefix="/projects", tags=["project-domain"])
api_router.include_router(portfolio_router, tags=["portfolio"])
api_router.include_router(overview_router, tags=["overview"])
api_router.include_router(pmo_router, tags=["pmo"])
api_router.include_router(project_detail_router, tags=["pmo"])
api_router.include_router(data_sources_router, prefix="/data-sources", tags=["data-sources"])
api_router.include_router(discovery_router, prefix="/data-sources", tags=["discovery"])
api_router.include_router(ai_queries_router, prefix="/ai", tags=["ai"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(upload_router, prefix="/files", tags=["files"])
api_router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
api_router.include_router(catalog_router, prefix="/catalog", tags=["catalog"])
api_router.include_router(query_history_router, prefix="/query-history", tags=["query-history"])
api_router.include_router(gmail_router, prefix="/gmail", tags=["gmail"])
api_router.include_router(outlook_router, prefix="/outlook", tags=["outlook"])
