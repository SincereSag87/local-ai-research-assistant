import json

from app.evaluation.models import ModelComparisonResult, ModelRunResult


def format_comparison_text(result: ModelComparisonResult) -> str:
    lines = [
        f"Task: {result.task}",
        f"Source: {result.source_url}",
        f"Ingestion: {result.ingestion_method}",
        "",
    ]
    for run in result.runs:
        lines.extend(_format_run(run))
        lines.append("")

    valid_models = ", ".join(result.valid_models) if result.valid_models else "None"
    fastest = result.fastest_model or "None"
    lines.extend(
        [
            "Comparison",
            f"Fastest: {fastest}",
            f"Valid models: {valid_models}",
            f"Notes: {result.summary}",
        ]
    )
    return "\n".join(lines)


def format_comparison_json(result: ModelComparisonResult) -> str:
    return json.dumps(result.model_dump(mode="json"), indent=2)


def _format_run(run: ModelRunResult) -> list[str]:
    lines = [
        f"Model: {run.model}",
        f"Latency: {run.latency_ms:,} ms",
        f"Structured output: {'valid' if run.parse_valid else 'invalid'}",
        f"Task success: {'PASS' if run.success else 'FAIL'}",
    ]
    if run.error:
        lines.append(f"Error: {run.error}")
        return lines

    if run.metrics is None:
        return lines

    lines.extend(
        [
            f"Response length: {run.metrics.response_length:,} chars",
            f"Completeness: {'PASS' if run.metrics.contains_required_fields else 'FAIL'}",
            f"Grounding: {'PASS' if run.metrics.grounded else 'FAIL'}",
        ]
    )
    if run.metrics.answer_present_behavior:
        lines.append(f"Answer behavior: {run.metrics.answer_present_behavior}")
    if run.metrics.fact_count:
        lines.append(f"Facts: {run.metrics.fact_count}")
    return lines
