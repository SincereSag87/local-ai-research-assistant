from fastapi import APIRouter, Depends

from app.api.dependencies import get_research_service
from app.api.models import PromptRequest, QuestionRequest, URLResearchRequest
from app.llm import ChatResponse
from app.research import KeyFact, QuestionAnswer, ResearchReport, ResearchSummary
from app.services.research_service import ResearchService

router = APIRouter(prefix="/research", tags=["research"])
ResearchServiceDep = Depends(get_research_service)


@router.post(
    "/generate",
    response_model=ChatResponse,
    summary="Generate a direct local model response",
)
def generate(
    request: PromptRequest,
    service: ResearchService = ResearchServiceDep,
) -> ChatResponse:
    return service.ask(prompt=request.prompt, model=request.model)


@router.post(
    "/summary",
    response_model=ResearchSummary,
    summary="Summarize a webpage",
)
def summarize(
    request: URLResearchRequest,
    service: ResearchService = ResearchServiceDep,
) -> ResearchSummary:
    return service.summarize_url(url=str(request.url), model=request.model)


@router.post(
    "/facts",
    response_model=list[KeyFact],
    summary="Extract grounded facts from a webpage",
)
def facts(
    request: URLResearchRequest,
    service: ResearchService = ResearchServiceDep,
) -> list[KeyFact]:
    return service.extract_facts_from_url(url=str(request.url), model=request.model)


@router.post(
    "/topics",
    response_model=list[str],
    summary="Extract topics from a webpage",
)
def topics(
    request: URLResearchRequest,
    service: ResearchService = ResearchServiceDep,
) -> list[str]:
    return service.extract_topics_from_url(url=str(request.url), model=request.model)


@router.post(
    "/report",
    response_model=ResearchReport,
    summary="Generate a structured research report for a webpage",
)
def report(
    request: URLResearchRequest,
    service: ResearchService = ResearchServiceDep,
) -> ResearchReport:
    return service.generate_url_report(url=str(request.url), model=request.model)


@router.post(
    "/ask",
    response_model=QuestionAnswer,
    summary="Ask a grounded question about a webpage",
)
def ask(
    request: QuestionRequest,
    service: ResearchService = ResearchServiceDep,
) -> QuestionAnswer:
    return service.answer_url_question(
        url=str(request.url),
        question=request.question,
        model=request.model,
    )
