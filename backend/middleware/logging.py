"""Structured logging middleware with correlation ID tracking."""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

logger = logging.getLogger(__name__)


class CorrelationIdFilter(logging.Filter):
    """Add correlation_id to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get("")
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        correlation_id_var.set(correlation_id)

        # Skip logging for health check endpoint (too noisy)
        if request.url.path == "/api/health":
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = correlation_id
            return response

        # Record start time
        start_time = time.perf_counter()

        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request/response
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": correlation_id,
                },
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": correlation_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return correlation_id_var.get("")
