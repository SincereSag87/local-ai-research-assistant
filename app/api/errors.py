import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.ingestion import IngestionError
from app.llm import LLMError, LLMModelNotFoundError, LLMServiceUnavailableError
from app.observability.logging import get_logger, log_event
from app.observability.metrics import get_metrics_store
from app.observability.tracing import current_request_id
from app.research import ResearchParseError


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IngestionError, _ingestion_error_handler)
    app.add_exception_handler(ResearchParseError, _research_parse_error_handler)
    app.add_exception_handler(LLMServiceUnavailableError, _llm_unavailable_error_handler)
    app.add_exception_handler(LLMModelNotFoundError, _llm_model_error_handler)
    app.add_exception_handler(LLMError, _llm_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


def error_response(
    code: str,
    message: str,
    status_code: int,
    request: Request | None = None,
) -> JSONResponse:
    headers = {}
    request_id = getattr(request.state, "request_id", None) if request else None
    request_id = request_id or current_request_id.get()
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


async def _ingestion_error_handler(request: Request, exc: IngestionError) -> JSONResponse:
    _record_api_error("ingestion_error", request, exc)
    return error_response(
        "INGESTION_FAILED",
        str(exc) or "The URL could not be ingested.",
        422,
        request,
    )


async def _research_parse_error_handler(request: Request, exc: ResearchParseError) -> JSONResponse:
    _record_api_error("parse_error", request, exc)
    return error_response(
        "RESEARCH_PARSE_FAILED",
        "The model returned output that could not be parsed into the expected schema.",
        status.HTTP_502_BAD_GATEWAY,
        request,
    )


async def _llm_unavailable_error_handler(
    request: Request,
    exc: LLMServiceUnavailableError,
) -> JSONResponse:
    _record_api_error("ollama_unavailable", request, exc)
    return error_response(
        "OLLAMA_UNAVAILABLE",
        "The local Ollama service is unavailable.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
        request,
    )


async def _llm_model_error_handler(request: Request, exc: LLMModelNotFoundError) -> JSONResponse:
    _record_api_error("model_not_found", request, exc)
    return error_response(
        "MODEL_UNAVAILABLE",
        str(exc) or "The requested local model is unavailable.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
        request,
    )


async def _llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    _record_api_error("llm_error", request, exc)
    return error_response(
        "LLM_REQUEST_FAILED",
        "The local model request failed.",
        status.HTTP_502_BAD_GATEWAY,
        request,
    )


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    _record_api_error("validation_error", request, exc)
    return error_response(
        "VALIDATION_ERROR",
        "The request did not match the required API schema.",
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        request,
    )


async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    get_metrics_store().record_error("internal_error")
    get_logger().exception(
        "unexpected_api_error",
        extra={
            "context": {
                "request_id": current_request_id.get(),
                "path": request.url.path,
                "method": request.method,
                "error_category": "internal_error",
            }
        },
    )
    return error_response(
        "INTERNAL_ERROR",
        "An unexpected internal error occurred.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        request,
    )


def _record_api_error(category: str, request: Request, exc: Exception) -> None:
    get_metrics_store().record_error(category)
    log_event(
        logging.WARNING,
        "api_error",
        request_id=current_request_id.get(),
        path=request.url.path,
        method=request.method,
        error_category=category,
        error_type=exc.__class__.__name__,
    )
