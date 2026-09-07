import logging
import re

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.observability.logging import log_event
from app.observability.metrics import get_metrics_store
from app.observability.tracing import current_request_id, generate_request_id, timer

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def resolve_request_id(value: str | None) -> str:
    if value and _SAFE_REQUEST_ID.fullmatch(value):
        return value
    return generate_request_id()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Attach request IDs, request timing, and high-level HTTP metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        token = current_request_id.set(request_id)
        status_code = 500
        with timer() as request_timer:
            try:
                response = await call_next(request)
                status_code = response.status_code
            except Exception:
                get_metrics_store().record_http_request(
                    success=False,
                    latency_ms=request_timer.elapsed_ms,
                )
                log_event(
                    logging.ERROR,
                    "http_request_failed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    total_latency_ms=request_timer.elapsed_ms,
                    success=False,
                    error_category="internal_error",
                )
                current_request_id.reset(token)
                raise

        success = status_code < 400
        get_metrics_store().record_http_request(
            success=success,
            latency_ms=request_timer.elapsed_ms,
        )
        log_event(
            logging.INFO,
            "http_request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            total_latency_ms=request_timer.elapsed_ms,
            success=success,
        )
        response.headers[REQUEST_ID_HEADER] = request_id
        current_request_id.reset(token)
        return response
