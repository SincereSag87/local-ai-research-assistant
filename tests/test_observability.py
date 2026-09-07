import uuid

from app.evaluation.models import EvaluationMetrics, ModelComparisonResult, ModelRunResult
from app.observability.metrics import MetricsStore
from app.observability.models import TraceEvent
from app.observability.tracing import generate_request_id, timer


def test_generate_request_id_returns_uuid():
    request_id = generate_request_id()

    assert str(uuid.UUID(request_id)) == request_id


def test_timer_records_elapsed_ms(monkeypatch):
    times = iter([10.0, 10.125])
    monkeypatch.setattr("app.observability.tracing.time.perf_counter", lambda: next(times))

    with timer() as result:
        assert result.elapsed_ms == 0

    assert result.elapsed_ms == 125


def test_metrics_store_records_success_failure_and_categories():
    store = MetricsStore()

    store.record_http_request(success=True, latency_ms=100)
    store.record_http_request(success=False, latency_ms=300)
    store.record_error("validation_error")
    store.record_event(
        TraceEvent(
            event="research_task",
            task="summary",
            url="https://example.com",
            model="llama3.2",
            ingestion_method="static",
            model_latency_ms=500,
            total_latency_ms=700,
            success=True,
            parse_valid=True,
        )
    )
    store.record_event(
        TraceEvent(
            event="research_task",
            task="facts",
            model="gemma3",
            ingestion_method="browser",
            success=False,
            parse_valid=False,
            error_category="parse_error",
        )
    )

    snapshot = store.snapshot()

    assert snapshot.requests.total == 2
    assert snapshot.requests.successful == 1
    assert snapshot.requests.failed == 1
    assert snapshot.requests.average_latency_ms == 200
    assert snapshot.models["llama3.2"].requests == 1
    assert snapshot.models["llama3.2"].average_latency_ms == 500
    assert snapshot.tasks == {"summary": 1, "facts": 1}
    assert snapshot.ingestion == {"static": 1, "browser": 1}
    assert snapshot.errors["validation_error"] == 1
    assert snapshot.errors["parse_error"] == 1
    assert snapshot.parsing_failures == 1


def test_metrics_store_records_comparison_and_unknown_answer():
    store = MetricsStore()
    result = ModelComparisonResult(
        task="ask",
        source_url="https://example.com",
        ingestion_method="static",
        runs=[
            ModelRunResult(
                model="llama3.2",
                task="ask",
                success=True,
                latency_ms=1000,
                response_text="{}",
                structured_result={
                    "answer": (
                        "The provided page does not contain enough information to answer "
                        "this question."
                    )
                },
                response_chars=2,
                parse_valid=True,
                metrics=EvaluationMetrics(
                    grounded=True,
                    contains_required_fields=True,
                    answer_present_behavior="explicit_insufficient_information",
                    completeness_score=2,
                    response_length=2,
                    latency_ms=1000,
                ),
            ),
            ModelRunResult(
                model="gemma3",
                task="ask",
                success=False,
                latency_ms=0,
                response_text="",
                response_chars=0,
                parse_valid=False,
                error="missing model",
            ),
        ],
        fastest_model="llama3.2",
        valid_models=["llama3.2"],
        summary="One model succeeded.",
    )

    store.record_comparison(result)
    snapshot = store.snapshot()

    assert snapshot.comparison_runs == 1
    assert snapshot.tasks["ask"] == 1
    assert snapshot.ingestion["static"] == 1
    assert snapshot.models["llama3.2"].average_latency_ms == 1000
    assert snapshot.parsing_failures == 1
    assert snapshot.errors["model_run_error"] == 1
    assert snapshot.unknown_answer_responses == 1
