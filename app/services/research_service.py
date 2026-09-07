from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from app.evaluation import ModelComparator, ModelComparisonResult
from app.ingestion import IngestionError, WebIngestor
from app.llm import (
    ChatMessage,
    ChatResponse,
    LLMError,
    LLMModelNotFoundError,
    LLMProvider,
    LLMServiceUnavailableError,
)
from app.observability.logging import log_event
from app.observability.metrics import get_metrics_store
from app.observability.models import TraceEvent
from app.observability.tracing import current_request_id, timer
from app.research import (
    KeyFact,
    QuestionAnswer,
    ResearchEngine,
    ResearchParseError,
    ResearchReport,
    ResearchSummary,
)
from app.research.prompts import UNKNOWN_ANSWER

T = TypeVar("T")


class ResearchService:
    """Application service layer for direct prompts and URL research tasks."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        web_ingestor: WebIngestor | None = None,
        research_engine: ResearchEngine | None = None,
        model_comparator: ModelComparator | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.web_ingestor = web_ingestor or WebIngestor()
        self.research_engine = research_engine or ResearchEngine(llm_provider=llm_provider)
        self.model_comparator = model_comparator or ModelComparator(llm_provider=llm_provider)
        self.metrics = get_metrics_store()

    def ask(self, prompt: str, model: str | None = None) -> ChatResponse:
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are a concise research assistant that explains "
                    "technical topics clearly."
                ),
            ),
            ChatMessage(role="user", content=prompt),
        ]
        with timer() as total_timer:
            try:
                with timer() as model_timer:
                    response = self.llm_provider.generate(messages=messages, model=model)
            except Exception as exc:
                self._record_event(
                    task="generate",
                    url=None,
                    model=model,
                    ingestion_method=None,
                    ingestion_ms=None,
                    model_latency_ms=None,
                    total_latency_ms=total_timer.elapsed_ms,
                    success=False,
                    parse_valid=None,
                    error_category=_error_category(exc),
                )
                raise

        self._record_event(
            task="generate",
            url=None,
            model=response.model,
            ingestion_method=None,
            ingestion_ms=None,
            model_latency_ms=model_timer.elapsed_ms,
            total_latency_ms=total_timer.elapsed_ms,
            success=True,
            parse_valid=True,
            error_category=None,
        )
        return response

    def summarize_url(self, url: str, model: str | None = None) -> ResearchSummary:
        return self._run_url_research(
            task="summary",
            url=url,
            model=model,
            runner=lambda document: self.research_engine.summarize(document=document, model=model),
        )

    def extract_facts_from_url(self, url: str, model: str | None = None) -> list[KeyFact]:
        return self._run_url_research(
            task="facts",
            url=url,
            model=model,
            runner=lambda document: self.research_engine.extract_facts(
                document=document,
                model=model,
            ),
        )

    def extract_topics_from_url(self, url: str, model: str | None = None) -> list[str]:
        return self._run_url_research(
            task="topics",
            url=url,
            model=model,
            runner=lambda document: self.research_engine.extract_topics(
                document=document,
                model=model,
            ),
        )

    def answer_url_question(
        self,
        url: str,
        question: str,
        model: str | None = None,
    ) -> QuestionAnswer:
        return self._run_url_research(
            task="ask",
            url=url,
            model=model,
            runner=lambda document: self.research_engine.answer_question(
                document=document,
                question=question,
                model=model,
            ),
        )

    def generate_url_report(self, url: str, model: str | None = None) -> ResearchReport:
        return self._run_url_research(
            task="report",
            url=url,
            model=model,
            runner=lambda document: self.research_engine.generate_report(
                document=document,
                model=model,
            ),
        )

    def compare_url_task(
        self,
        *,
        url: str,
        task: str,
        models: Sequence[str],
        question: str | None = None,
    ) -> ModelComparisonResult:
        with timer() as total_timer:
            ingestion_ms = None
            ingestion_method = None
            try:
                with timer() as ingestion_timer:
                    document = self.web_ingestor.ingest(url)
                ingestion_ms = ingestion_timer.elapsed_ms
                ingestion_method = document.source_type
                result = self._compare_document(
                    document=document,
                    task=task,
                    models=models,
                    question=question,
                )
            except Exception as exc:
                self._record_event(
                    task=f"compare_{task}",
                    url=url,
                    model=",".join(models),
                    ingestion_method=ingestion_method,
                    ingestion_ms=ingestion_ms,
                    model_latency_ms=None,
                    total_latency_ms=total_timer.elapsed_ms,
                    success=False,
                    parse_valid=None,
                    error_category=_error_category(exc),
                )
                raise

        self.metrics.record_comparison(result)
        self._log_event(
            task=f"compare_{task}",
            url=url,
            model=",".join(models),
            ingestion_method=ingestion_method,
            ingestion_ms=ingestion_ms,
            model_latency_ms=sum(run.latency_ms for run in result.runs),
            total_latency_ms=total_timer.elapsed_ms,
            success=any(run.success for run in result.runs),
            parse_valid=all(run.parse_valid for run in result.runs),
            error_category=None,
        )
        return result

    def _compare_document(
        self,
        *,
        document: Any,
        task: str,
        models: Sequence[str],
        question: str | None,
    ) -> ModelComparisonResult:
        if task == "summary":
            return self.model_comparator.compare_summary(document=document, models=models)
        if task == "facts":
            return self.model_comparator.compare_facts(document=document, models=models)
        if task == "topics":
            return self.model_comparator.compare_topics(document=document, models=models)
        if task == "ask":
            if question is None:
                raise ValueError("question is required for ask comparison")
            return self.model_comparator.compare_question(
                document=document,
                question=question,
                models=models,
            )
        if task == "report":
            return self.model_comparator.compare_report(document=document, models=models)
        raise ValueError(f"Unsupported comparison task: {task}")

    def _run_url_research(
        self,
        *,
        task: str,
        url: str,
        model: str | None,
        runner: Callable[[Any], T],
    ) -> T:
        with timer() as total_timer:
            ingestion_ms = None
            ingestion_method = None
            selected_model = model
            try:
                with timer() as ingestion_timer:
                    document = self.web_ingestor.ingest(url)
                ingestion_ms = ingestion_timer.elapsed_ms
                ingestion_method = document.source_type
                result = runner(document)
                selected_model = getattr(result, "model", model)
            except Exception as exc:
                self._record_event(
                    task=task,
                    url=url,
                    model=selected_model,
                    ingestion_method=ingestion_method,
                    ingestion_ms=ingestion_ms,
                    model_latency_ms=getattr(self.research_engine, "last_model_latency_ms", None),
                    total_latency_ms=total_timer.elapsed_ms,
                    success=False,
                    parse_valid=False if isinstance(exc, ResearchParseError) else None,
                    error_category=_error_category(exc),
                )
                raise

        if isinstance(result, QuestionAnswer) and result.answer == UNKNOWN_ANSWER:
            self.metrics.record_unknown_answer()
        self._record_event(
            task=task,
            url=url,
            model=selected_model,
            ingestion_method=ingestion_method,
            ingestion_ms=ingestion_ms,
            model_latency_ms=getattr(self.research_engine, "last_model_latency_ms", None),
            total_latency_ms=total_timer.elapsed_ms,
            success=True,
            parse_valid=True,
            error_category=None,
        )
        return result

    def _record_event(
        self,
        *,
        task: str,
        url: str | None,
        model: str | None,
        ingestion_method: str | None,
        ingestion_ms: int | None,
        model_latency_ms: int | None,
        total_latency_ms: int,
        success: bool,
        parse_valid: bool | None,
        error_category: str | None,
    ) -> None:
        event = TraceEvent(
            request_id=current_request_id.get(),
            event="research_task",
            task=task,
            url=url,
            model=model,
            ingestion_method=ingestion_method,
            ingestion_ms=ingestion_ms,
            model_latency_ms=model_latency_ms,
            total_latency_ms=total_latency_ms,
            success=success,
            parse_valid=parse_valid,
            error_category=error_category,
        )
        self.metrics.record_event(event)
        self._log_event(
            task=task,
            url=url,
            model=model,
            ingestion_method=ingestion_method,
            ingestion_ms=ingestion_ms,
            model_latency_ms=model_latency_ms,
            total_latency_ms=total_latency_ms,
            success=success,
            parse_valid=parse_valid,
            error_category=error_category,
        )

    def _log_event(
        self,
        *,
        task: str,
        url: str | None,
        model: str | None,
        ingestion_method: str | None,
        ingestion_ms: int | None,
        model_latency_ms: int | None,
        total_latency_ms: int,
        success: bool,
        parse_valid: bool | None,
        error_category: str | None,
    ) -> None:
        log_event(
            20,
            "research_task_completed",
            request_id=current_request_id.get(),
            task=task,
            url=url,
            model=model,
            ingestion_method=ingestion_method,
            ingestion_ms=ingestion_ms,
            model_latency_ms=model_latency_ms,
            total_latency_ms=total_latency_ms,
            success=success,
            parse_valid=parse_valid,
            error_category=error_category,
        )


def _error_category(exc: Exception) -> str:
    if isinstance(exc, ResearchParseError):
        return "parse_error"
    if isinstance(exc, IngestionError):
        return "ingestion_error"
    if isinstance(exc, LLMServiceUnavailableError):
        return "ollama_unavailable"
    if isinstance(exc, LLMModelNotFoundError):
        return "model_not_found"
    if isinstance(exc, LLMError):
        return "llm_error"
    return exc.__class__.__name__
