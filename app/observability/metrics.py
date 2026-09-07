from threading import Lock

from app.evaluation.models import ModelComparisonResult
from app.observability.models import MetricsSnapshot, ModelMetrics, RequestMetrics, TraceEvent
from app.research.prompts import UNKNOWN_ANSWER


class MetricsStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._request_total = 0
            self._request_successful = 0
            self._request_failed = 0
            self._request_latency_total = 0
            self._model_counts: dict[str, int] = {}
            self._model_latency_totals: dict[str, int] = {}
            self._task_counts: dict[str, int] = {}
            self._ingestion_counts: dict[str, int] = {}
            self._error_counts: dict[str, int] = {}
            self._parsing_failures = 0
            self._comparison_runs = 0
            self._unknown_answer_responses = 0

    def record_http_request(self, *, success: bool, latency_ms: int) -> None:
        with self._lock:
            self._request_total += 1
            self._request_latency_total += latency_ms
            if success:
                self._request_successful += 1
            else:
                self._request_failed += 1

    def record_event(self, event: TraceEvent) -> None:
        with self._lock:
            if event.task:
                self._task_counts[event.task] = self._task_counts.get(event.task, 0) + 1
            if event.model:
                self._model_counts[event.model] = self._model_counts.get(event.model, 0) + 1
                if event.model_latency_ms is not None:
                    current = self._model_latency_totals.get(event.model, 0)
                    self._model_latency_totals[event.model] = current + event.model_latency_ms
            if event.ingestion_method:
                current = self._ingestion_counts.get(event.ingestion_method, 0)
                self._ingestion_counts[event.ingestion_method] = current + 1
            if event.error_category:
                self._error_counts[event.error_category] = (
                    self._error_counts.get(event.error_category, 0) + 1
                )
            if event.parse_valid is False:
                self._parsing_failures += 1

    def record_error(self, category: str) -> None:
        with self._lock:
            self._error_counts[category] = self._error_counts.get(category, 0) + 1

    def record_comparison(self, result: ModelComparisonResult) -> None:
        with self._lock:
            self._comparison_runs += 1
            self._task_counts[result.task] = self._task_counts.get(result.task, 0) + 1
            self._ingestion_counts[result.ingestion_method] = (
                self._ingestion_counts.get(result.ingestion_method, 0) + 1
            )
            for run in result.runs:
                self._model_counts[run.model] = self._model_counts.get(run.model, 0) + 1
                self._model_latency_totals[run.model] = (
                    self._model_latency_totals.get(run.model, 0) + run.latency_ms
                )
                if not run.parse_valid:
                    self._parsing_failures += 1
                if run.error:
                    self._error_counts["model_run_error"] = (
                        self._error_counts.get("model_run_error", 0) + 1
                    )
                structured = run.structured_result
                if isinstance(structured, dict) and structured.get("answer") == UNKNOWN_ANSWER:
                    self._unknown_answer_responses += 1

    def record_unknown_answer(self) -> None:
        with self._lock:
            self._unknown_answer_responses += 1

    def snapshot(self) -> MetricsSnapshot:
        with self._lock:
            average_request_latency = (
                self._request_latency_total / self._request_total if self._request_total else 0.0
            )
            models = {
                model: ModelMetrics(
                    requests=count,
                    average_latency_ms=(
                        self._model_latency_totals.get(model, 0) / count if count else 0.0
                    ),
                )
                for model, count in self._model_counts.items()
            }
            return MetricsSnapshot(
                requests=RequestMetrics(
                    total=self._request_total,
                    successful=self._request_successful,
                    failed=self._request_failed,
                    average_latency_ms=average_request_latency,
                ),
                models=models,
                tasks=dict(self._task_counts),
                ingestion=dict(self._ingestion_counts),
                errors=dict(self._error_counts),
                parsing_failures=self._parsing_failures,
                comparison_runs=self._comparison_runs,
                unknown_answer_responses=self._unknown_answer_responses,
            )


_metrics_store = MetricsStore()


def get_metrics_store() -> MetricsStore:
    return _metrics_store
