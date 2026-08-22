"""
Request ID middleware — generates and propagates a unique identifier per request.

Every incoming request is assigned a UUID v4 `request_id` that is:
- Stored in a ContextVar (accessible throughout the request lifecycle)
- Added to the response as an `X-Request-ID` header
- Available to structured logging for correlation

This enables full traceability from API entry through service/repository calls
and into log aggregation systems.
"""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ContextVar holding the current request's ID — accessible from any async code
# within the same request scope (services, repositories, logging processors).
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a UUID v4 request_id to every incoming request.

    The ID is stored in a ContextVar for structured logging and added
    to the response as the X-Request-ID header for client-side correlation.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Generate request_id, bind to context, and attach to response."""
        generated_id = str(uuid.uuid4())
        request_id_ctx.set(generated_id)

        # Store on request state so route handlers can access it directly
        request.state.request_id = generated_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = generated_id
        return response
