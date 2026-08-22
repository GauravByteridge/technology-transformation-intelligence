"""
Configuration API route handlers.

Exposes non-sensitive configuration state (e.g., current operating mode)
to the frontend for runtime awareness. No secrets are exposed.
"""

from fastapi import APIRouter, Depends, Request

from app.config.settings import Settings
from app.dependencies import get_settings
from app.schemas.config import AppModeResponse

router = APIRouter()


@router.get(
    "/mode",
    response_model=AppModeResponse,
    summary="Get current application operating mode",
)
async def get_app_mode(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AppModeResponse:
    """
    Return the current application operating mode.

    Used by the frontend to adapt UI behavior (e.g., showing
    "Demo Mode" badge). No secrets or credentials are exposed.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    mode = "demo" if settings.demo_mode else "live"

    return AppModeResponse(
        mode=mode,
        demo_mode=settings.demo_mode,
        request_id=request_id,
    )
