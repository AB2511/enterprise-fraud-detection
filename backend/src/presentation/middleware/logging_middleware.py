"""Request/Response Logging Middleware."""

import time
from uuid import uuid4

from fastapi import Request, Response
from src.config.logging_config import get_logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses.

    Logs:
    - Request method, path, headers
    - Response status code, duration
    - Request ID for correlation
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize logging middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or endpoint

        Returns:
            HTTP response
        """
        # Generate request ID for correlation
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Log request
        start_time = time.time()
        logger.info(
            "Incoming request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_host=request.client.host if request.client else None,
        )

        # Process request
        try:
            response = await call_next(request)

            # Log response
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Log error
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Request failed",
                request_id=request_id,
                duration_ms=duration_ms,
                error=str(exc),
                exc_info=True,
            )
            raise
