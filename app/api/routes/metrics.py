from fastapi import APIRouter

from app.observability.metrics import get_metrics_store
from app.observability.models import MetricsSnapshot

router = APIRouter(tags=["metrics"])


@router.get(
    "/metrics",
    response_model=MetricsSnapshot,
    summary="Inspect local application metrics",
)
def metrics() -> MetricsSnapshot:
    return get_metrics_store().snapshot()
