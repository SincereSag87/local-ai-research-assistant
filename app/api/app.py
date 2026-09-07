from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes import comparison, health, research
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    api = FastAPI(
        title="LocalAI Research Assistant API",
        description=(
            "Local-first AI research backend for webpage ingestion, grounded research "
            "tasks, and local model comparison."
        ),
        version="0.5.0",
    )
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
    register_exception_handlers(api)
    return api


app = create_app()
