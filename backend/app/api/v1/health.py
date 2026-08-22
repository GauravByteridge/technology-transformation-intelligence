"""
Health check endpoint — verifies the application is running and ready to serve.

Returns a simple status response that load balancers and orchestrators
can use to determine if the service is healthy.
"""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Check application health.

    Returns HTTP 200 with status "ok" when the application is ready.
    """
    return HealthResponse(status="ok")
