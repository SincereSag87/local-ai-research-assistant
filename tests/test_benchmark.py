from app.evaluation.benchmark import (
    BenchmarkCase,
    BenchmarkConfig,
    format_benchmark_text,
    run_benchmark,
)
from app.evaluation.models import EvaluationMetrics, ModelComparisonResult, ModelRunResult


class FakeBenchmarkService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls = []

    def compare_url_task(self, *, url, task, models, question=None):
        self.calls.append({"url": url, "task": task, "models": models, "question": question})
        if self.should_fail:
            raise RuntimeError("ingestion failed")
        return ModelComparisonResult(
            task=task,
            source_url=url,
            ingestion_method="static",
            runs=[
                ModelRunResult(
                    model=models[0],
                    task=task,
                    success=True,
                    latency_ms=100,
                    response_text="ok",
                    structured_result={"summary": "ok"},
                    response_chars=2,
                    parse_valid=True,
                    metrics=EvaluationMetrics(
                        grounded=True,
                        contains_required_fields=True,
                        completeness_score=1,
                        response_length=2,
                        latency_ms=100,
                    ),
                )
            ],
            fastest_model=models[0],
            valid_models=[models[0]],
            summary="ok",
        )


def test_benchmark_aggregates_successful_runs():
    service = FakeBenchmarkService()
    config = BenchmarkConfig(
        cases=[
            BenchmarkCase(
                name="summary",
                task="summary",
                url="https://example.com",
                models=["llama3.2"],
            )
        ]
    )

    result = run_benchmark(config, service=service)

    assert service.calls == [
        {
            "url": "https://example.com/",
            "task": "summary",
            "models": ["llama3.2"],
            "question": None,
        }
    ]
    assert result.aggregates["llama3.2"].success_rate == 1.0
    assert result.aggregates["llama3.2"].parse_rate == 1.0
    assert result.aggregates["llama3.2"].grounding_rate == 1.0
    assert "Benchmark Results" in format_benchmark_text(result)


def test_benchmark_isolates_case_failure():
    service = FakeBenchmarkService(should_fail=True)
    config = BenchmarkConfig(
        cases=[
            BenchmarkCase(
                name="summary",
                task="summary",
                url="https://example.com",
                models=["llama3.2", "gemma3"],
            )
        ]
    )

    result = run_benchmark(config, service=service)

    assert result.cases[0].runs[0].success is False
    assert result.cases[0].runs[1].success is False
    assert result.aggregates["llama3.2"].success_rate == 0.0
    assert "ingestion failed" in result.cases[0].runs[0].error
