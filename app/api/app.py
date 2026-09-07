from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware import ObservabilityMiddleware
from app.api.routes import comparison, health, metrics, research
from app.core.config import get_settings
from app.observability.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    api = FastAPI(
        title="LocalAI Research Assistant API",
        description=(
            "Local-first AI research backend for webpage ingestion, grounded research "
            "tasks, and local model comparison."
        ),
        version="1.0.0",
    )
    api.add_middleware(ObservabilityMiddleware)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    api.include_router(health.router)
    api.include_router(research.router)
    api.include_router(comparison.router)
    api.include_router(metrics.router)
    register_exception_handlers(api)
    return api


app = create_app()
