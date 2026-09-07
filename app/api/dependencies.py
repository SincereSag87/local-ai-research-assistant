from functools import lru_cache

import requests

from app.core.config import Settings, get_settings
from app.llm import OllamaProvider
from app.services.research_service import ResearchService


@lru_cache
def get_ollama_provider() -> OllamaProvider:
    return OllamaProvider(settings=get_settings())


@lru_cache
def get_research_service() -> ResearchService:
    return ResearchService(llm_provider=get_ollama_provider())


def get_ollama_readiness(settings: Settings | None = None) -> dict:
    active_settings = settings or get_settings()
    models_url = f"{str(active_settings.ollama_base_url).rstrip('/')}/models"
    reachable = False
    try:
        response = requests.get(models_url, timeout=min(active_settings.http_timeout, 5.0))
        reachable = response.ok
    except requests.RequestException:
        reachable = False

    return {
        "status": "ok" if reachable else "degraded",
        "service": "ollama",
        "base_url": str(active_settings.ollama_base_url),
        "default_model": active_settings.default_model,
        "reachable": reachable,
    }
