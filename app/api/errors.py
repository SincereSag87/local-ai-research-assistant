from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.ingestion import IngestionError
from app.llm import LLMError, LLMModelNotFoundError, LLMServiceUnavailableError
from app.research import ResearchParseError


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IngestionError, _ingestion_error_handler)
    app.add_exception_handler(ResearchParseError, _research_parse_error_handler)
    app.add_exception_handler(LLMServiceUnavailableError, _llm_unavailable_error_handler)
    app.add_exception_handler(LLMModelNotFoundError, _llm_model_error_handler)
    app.add_exception_handler(LLMError, _llm_error_handler)
    app.add_exception_handler(Exception, _unexpected_error_handler)


def error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


async def _ingestion_error_handler(request: Request, exc: IngestionError) -> JSONResponse:
    return error_response(
        "INGESTION_FAILED",
        str(exc) or "The URL could not be ingested.",
        422,
    )


async def _research_parse_error_handler(request: Request, exc: ResearchParseError) -> JSONResponse:
    return error_response(
        "RESEARCH_PARSE_FAILED",
        "The model returned output that could not be parsed into the expected schema.",
        status.HTTP_502_BAD_GATEWAY,
    )


async def _llm_unavailable_error_handler(
    request: Request,
    exc: LLMServiceUnavailableError,
) -> JSONResponse:
    return error_response(
        "OLLAMA_UNAVAILABLE",
        "The local Ollama service is unavailable.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


async def _llm_model_error_handler(request: Request, exc: LLMModelNotFoundError) -> JSONResponse:
    return error_response(
        "MODEL_UNAVAILABLE",
        str(exc) or "The requested local model is unavailable.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


async def _llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    return error_response(
        "LLM_REQUEST_FAILED",
        "The local model request failed.",
        status.HTTP_502_BAD_GATEWAY,
    )


async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        "INTERNAL_ERROR",
        "An unexpected internal error occurred.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
