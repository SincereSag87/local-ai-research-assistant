import argparse
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.api.dependencies import get_research_service
from app.evaluation.formatter import format_comparison_text
from app.evaluation.models import ComparisonTask, ModelComparisonResult, ModelRunResult
from app.services.research_service import ResearchService

BenchmarkOutput = Literal["text", "json"]


class BenchmarkCase(BaseModel):
    name: str
    task: ComparisonTask
    url: HttpUrl
    models: list[str] = Field(min_length=1)
    question: str | None = None


class BenchmarkConfig(BaseModel):
    cases: list[BenchmarkCase] = Field(min_length=1)


class BenchmarkModelAggregate(BaseModel):
    model: str
    runs: int
    success_rate: float
    parse_rate: float
    grounding_rate: float
    average_latency_ms: float


class BenchmarkResult(BaseModel):
    cases: list[ModelComparisonResult]
    aggregates: dict[str, BenchmarkModelAggregate]


def load_benchmark_config(path: str | Path) -> BenchmarkConfig:
    with Path(path).open(encoding="utf-8") as file:
        return BenchmarkConfig.model_validate(json.load(file))


def run_benchmark(
    config: BenchmarkConfig,
    service: ResearchService | None = None,
) -> BenchmarkResult:
    active_service = service or get_research_service()
    results: list[ModelComparisonResult] = []
    for case in config.cases:
        try:
            result = active_service.compare_url_task(
                url=str(case.url),
                task=case.task,
                models=case.models,
                question=case.question,
            )
        except Exception as exc:
            result = _failed_case_result(case, exc)
        results.append(result)
    return BenchmarkResult(cases=results, aggregates=_aggregate(results))


def format_benchmark_text(result: BenchmarkResult) -> str:
    lines = ["Benchmark Results", ""]
    lines.extend(["Model | Runs | Success Rate | Parse Rate | Grounding Rate | Avg Latency"])
    lines.extend(["--- | ---: | ---: | ---: | ---: | ---:"])
    for aggregate in result.aggregates.values():
        lines.append(
            " | ".join(
                [
                    aggregate.model,
                    str(aggregate.runs),
                    f"{aggregate.success_rate:.0%}",
                    f"{aggregate.parse_rate:.0%}",
                    f"{aggregate.grounding_rate:.0%}",
                    f"{aggregate.average_latency_ms:,.0f} ms",
                ]
            )
        )

    lines.append("")
    for index, case_result in enumerate(result.cases, start=1):
        lines.append(f"Case {index}:")
        lines.append(format_comparison_text(case_result))
        lines.append("")
    return "\n".join(lines)


def _failed_case_result(case: BenchmarkCase, exc: Exception) -> ModelComparisonResult:
    runs = [
        ModelRunResult(
            model=model,
            task=case.task,
            success=False,
            latency_ms=0,
            response_text="",
            structured_result=None,
            response_chars=0,
            parse_valid=False,
            metrics=None,
            error=f"{type(exc).__name__}: {exc}",
        )
        for model in case.models
    ]
    return ModelComparisonResult(
        task=case.task,
        source_url=case.url,
        ingestion_method="unknown",
        runs=runs,
        fastest_model=None,
        valid_models=[],
        summary="Benchmark case failed before model comparison completed.",
    )


def _aggregate(results: list[ModelComparisonResult]) -> dict[str, BenchmarkModelAggregate]:
    buckets: dict[str, list[ModelRunResult]] = {}
    for result in results:
        for run in result.runs:
            buckets.setdefault(run.model, []).append(run)

    aggregates = {}
    for model, runs in buckets.items():
        total = len(runs)
        successes = sum(1 for run in runs if run.success)
        parse_valid = sum(1 for run in runs if run.parse_valid)
        grounded = sum(1 for run in runs if run.metrics and run.metrics.grounded)
        latency_total = sum(run.latency_ms for run in runs)
        aggregates[model] = BenchmarkModelAggregate(
            model=model,
            runs=total,
            success_rate=successes / total if total else 0.0,
            parse_rate=parse_valid / total if total else 0.0,
            grounding_rate=grounded / total if total else 0.0,
            average_latency_ms=latency_total / total if total else 0.0,
        )
    return aggregates


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local model comparison benchmarks.")
    parser.add_argument("--config", required=True, help="Path to a benchmark JSON config file.")
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Terminal output format.",
    )
    args = parser.parse_args()

    result = run_benchmark(load_benchmark_config(args.config))
    if args.output == "json":
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return
    print(format_benchmark_text(result))


if __name__ == "__main__":
    main()
