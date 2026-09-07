import time
from collections.abc import Callable, Sequence
from typing import Any

from app.evaluation.metrics import evaluate_result
from app.evaluation.models import ComparisonTask, ModelComparisonResult, ModelRunResult
from app.ingestion import WebDocument
from app.llm import ChatMessage, ChatResponse, LLMProvider
from app.research import ResearchEngine, ResearchParseError


class _TimedProvider(LLMProvider):
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.last_latency_ms = 0

    def generate(self, messages: Sequence[ChatMessage], model: str | None = None) -> ChatResponse:
        started_at = time.monotonic()
        try:
            return self.provider.generate(messages=messages, model=model)
        finally:
            self.last_latency_ms = round((time.monotonic() - started_at) * 1000)


class ModelComparator:
    """Run the same research task on one WebDocument across multiple models."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.timed_provider = _TimedProvider(llm_provider)
        self.engine = ResearchEngine(llm_provider=self.timed_provider)

    def compare_summary(
        self,
        document: WebDocument,
        models: Sequence[str],
    ) -> ModelComparisonResult:
        return self._compare(
            document=document,
            models=models,
            task="summary",
            runner=lambda model: self.engine.summarize(document, model=model),
        )

    def compare_facts(
        self,
        document: WebDocument,
        models: Sequence[str],
    ) -> ModelComparisonResult:
        return self._compare(
            document=document,
            models=models,
            task="facts",
            runner=lambda model: self.engine.extract_facts(document, model=model),
        )

    def compare_topics(
        self,
        document: WebDocument,
        models: Sequence[str],
    ) -> ModelComparisonResult:
        return self._compare(
            document=document,
            models=models,
            task="topics",
            runner=lambda model: self.engine.extract_topics(document, model=model),
        )

    def compare_question(
        self,
        document: WebDocument,
        question: str,
        models: Sequence[str],
    ) -> ModelComparisonResult:
        return self._compare(
            document=document,
            models=models,
            task="ask",
            runner=lambda model: self.engine.answer_question(document, question, model=model),
        )

    def compare_report(
        self,
        document: WebDocument,
        models: Sequence[str],
    ) -> ModelComparisonResult:
        return self._compare(
            document=document,
            models=models,
            task="report",
            runner=lambda model: self.engine.generate_report(document, model=model),
        )

    def _compare(
        self,
        *,
        document: WebDocument,
        models: Sequence[str],
        task: ComparisonTask,
        runner: Callable[[str], Any],
    ) -> ModelComparisonResult:
        runs = [self._run_model(model=model, task=task, runner=runner) for model in models]
        successful_runs = [run for run in runs if run.success]
        valid_models = [run.model for run in runs if run.parse_valid]
        fastest = (
            min(successful_runs, key=lambda run: run.latency_ms).model
            if successful_runs
            else None
        )
        return ModelComparisonResult(
            task=task,
            source_url=document.final_url,
            ingestion_method=document.source_type,
            runs=runs,
            fastest_model=fastest,
            valid_models=valid_models,
            summary=_build_summary(runs),
        )

    def _run_model(
        self,
        *,
        model: str,
        task: ComparisonTask,
        runner: Callable[[str], Any],
    ) -> ModelRunResult:
        self.timed_provider.last_latency_ms = 0
        try:
            result = runner(model)
        except ResearchParseError as exc:
            latency_ms = self.timed_provider.last_latency_ms
            return ModelRunResult(
                model=model,
                task=task,
                success=False,
                latency_ms=latency_ms,
                response_text="",
                structured_result=None,
                response_chars=0,
                parse_valid=False,
                metrics=None,
                error=f"Structured output parsing failed: {exc}",
            )
        except Exception as exc:
            latency_ms = self.timed_provider.last_latency_ms
            return ModelRunResult(
                model=model,
                task=task,
                success=False,
                latency_ms=latency_ms,
                response_text="",
                structured_result=None,
                response_chars=0,
                parse_valid=False,
                metrics=None,
                error=f"{type(exc).__name__}: {exc}",
            )

        latency_ms = self.timed_provider.last_latency_ms
        response_text = _stringify_result(result)
        metrics = evaluate_result(task=task, result=result, latency_ms=latency_ms)
        return ModelRunResult(
            model=model,
            task=task,
            success=True,
            latency_ms=latency_ms,
            response_text=response_text,
            structured_result=_jsonable_result(result),
            response_chars=len(response_text),
            parse_valid=True,
            metrics=metrics,
            error=None,
        )


def _stringify_result(result: Any) -> str:
    if hasattr(result, "model_dump_json"):
        return result.model_dump_json()
    if isinstance(result, list):
        return "\n".join(
            item.model_dump_json() if hasattr(item, "model_dump_json") else str(item)
            for item in result
        )
    return str(result)


def _jsonable_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if isinstance(result, list):
        return [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in result
        ]
    return result


def _build_summary(runs: Sequence[ModelRunResult]) -> str:
    successes = [run.model for run in runs if run.success]
    failures = [run.model for run in runs if not run.success]
    if successes and failures:
        return f"{', '.join(successes)} succeeded; {', '.join(failures)} failed."
    if successes:
        return f"All compared models succeeded: {', '.join(successes)}."
    return "All compared models failed."
