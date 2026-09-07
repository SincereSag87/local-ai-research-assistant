from fastapi import APIRouter, Depends

from app.api.dependencies import get_ollama_readiness
from app.api.models import HealthResponse, OllamaHealthResponse

router = APIRouter(prefix="/health", tags=["health"])
OllamaReadinessDep = Depends(get_ollama_readiness)


@router.get("", response_model=HealthResponse, summary="Check API health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="local-ai-research-assistant")


@router.get(
    "/ollama",
    response_model=OllamaHealthResponse,
    summary="Check local Ollama readiness",
)
def ollama_health(readiness: dict = OllamaReadinessDep) -> OllamaHealthResponse:
    return OllamaHealthResponse.model_validate(readiness)
