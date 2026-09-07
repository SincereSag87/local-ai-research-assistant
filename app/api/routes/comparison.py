from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_research_service
from app.api.models import ComparisonRequest
from app.evaluation import ModelComparisonResult
from app.services.research_service import ResearchService

router = APIRouter(tags=["comparison"])
ResearchServiceDep = Depends(get_research_service)


@router.post(
    "/compare",
    response_model=ModelComparisonResult,
    summary="Compare local models on one webpage research task",
)
def compare(
    request: ComparisonRequest,
    service: ResearchService = ResearchServiceDep,
) -> ModelComparisonResult:
    if request.task == "ask" and not request.question:
        raise HTTPException(
            status_code=422,
            detail="question is required when task is ask",
        )
    return service.compare_url_task(
        url=str(request.url),
        task=request.task,
        models=request.models,
        question=request.question,
    )
