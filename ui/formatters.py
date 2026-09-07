from typing import Any

import pandas as pd


def format_health(api_health: dict[str, Any], ollama_health: dict[str, Any]) -> str:
    api_status = "Online" if api_health.get("status") == "ok" else "Unavailable"
    ollama_status = "Reachable" if ollama_health.get("reachable") else "Unavailable"
    default_model = ollama_health.get("default_model", "unknown")
    base_url = ollama_health.get("base_url", "unknown")
    return (
        f"**API:** {api_status}\n\n"
        f"**Ollama:** {ollama_status}\n\n"
        f"**Default model:** `{default_model}`\n\n"
        f"**Backend model endpoint:** `{base_url}`"
    )


def format_observability(
    api_health: dict[str, Any],
    ollama_health: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    requests = metrics.get("requests", {})
    markdown = "\n\n".join(
        [
            "## System Observability",
            format_health(api_health, ollama_health),
            (
                f"**Total requests:** {requests.get('total', 0)}\n\n"
                f"**Successful requests:** {requests.get('successful', 0)}\n\n"
                f"**Failed requests:** {requests.get('failed', 0)}\n\n"
                f"**Average request latency:** "
                f"{requests.get('average_latency_ms', 0):,.0f} ms\n\n"
                f"**Comparison runs:** {metrics.get('comparison_runs', 0)}\n\n"
                f"**Parsing failures:** {metrics.get('parsing_failures', 0)}\n\n"
                f"**Unknown-answer responses:** "
                f"{metrics.get('unknown_answer_responses', 0)}"
            ),
        ]
    )
    return (
        markdown,
        _models_dataframe(metrics.get("models", {})),
        _counts_dataframe(metrics.get("tasks", {}), "task"),
        _counts_dataframe(metrics.get("ingestion", {}), "method"),
    )


def format_summary(result: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            _header(result),
            f"## Summary\n{result.get('summary', '')}",
            _list_section("Key Points", result.get("key_points", [])),
            _list_section("Topics", result.get("topics", [])),
        ]
    )


def format_facts(facts: list[dict[str, Any]]) -> str:
    if not facts:
        return "## Key Facts\nNo facts were returned."
    lines = ["## Key Facts"]
    for index, fact in enumerate(facts, start=1):
        lines.extend(
            [
                f"### {index}. {fact.get('fact', '')}",
                f"**Evidence:** {fact.get('evidence', '')}",
                f"**Confidence:** {fact.get('confidence', 'unknown')}",
            ]
        )
    return "\n\n".join(lines)


def format_topics(topics: list[str]) -> str:
    return _list_section("Topics", topics)


def format_question(result: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            f"## Question\n{result.get('question', '')}",
            f"## Answer\n{result.get('answer', '')}",
            _list_section("Evidence", result.get("evidence", [])),
            f"**Source:** {result.get('source_url', '')}\n\n**Model:** `{result.get('model', '')}`",
        ]
    )


def format_report(result: dict[str, Any]) -> str:
    facts = result.get("notable_facts", [])
    fact_lines = []
    for fact in facts:
        fact_lines.append(
            "\n".join(
                [
                    f"- {fact.get('fact', '')}",
                    f"  - Evidence: {fact.get('evidence', '')}",
                    f"  - Confidence: {fact.get('confidence', 'unknown')}",
                ]
            )
        )
    return "\n\n".join(
        [
            _header(result),
            f"## Executive Summary\n{result.get('executive_summary', '')}",
            _list_section("Key Findings", result.get("key_findings", [])),
            _list_section("Topics", result.get("topics", [])),
            "## Notable Facts\n" + ("\n".join(fact_lines) if fact_lines else "- None"),
            _list_section("Questions Or Gaps", result.get("questions_or_gaps", [])),
        ]
    )


def format_comparison(result: dict[str, Any]) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    runs = result.get("runs", [])
    metric_rows = []
    detail_sections = [
        f"## Comparison\n**Task:** `{result.get('task')}`\n\n"
        f"**Source:** {result.get('source_url')}\n\n"
        f"**Ingestion:** `{result.get('ingestion_method')}`\n\n"
        f"**Fastest model:** `{result.get('fastest_model') or 'None'}`\n\n"
        f"**Valid models:** {', '.join(result.get('valid_models', [])) or 'None'}"
    ]

    for run in runs:
        metrics = run.get("metrics") or {}
        metric_rows.append(
            {
                "model": run.get("model"),
                "success": bool(run.get("success")),
                "latency_ms": run.get("latency_ms", 0),
                "latency_seconds": round((run.get("latency_ms", 0) or 0) / 1000, 2),
                "valid": bool(run.get("parse_valid")),
                "complete": bool(metrics.get("contains_required_fields")),
                "grounded": bool(metrics.get("grounded")),
                "chars": run.get("response_chars", 0),
                "words": metrics.get("word_count", 0),
                "facts": metrics.get("fact_count", 0),
            }
        )
        detail_sections.append(_format_run_detail(run))

    metrics_df = pd.DataFrame(metric_rows)
    chart_df = metrics_df[["model", "latency_seconds"]] if not metrics_df.empty else metrics_df
    return "\n\n".join(detail_sections), metrics_df, chart_df


def _format_run_detail(run: dict[str, Any]) -> str:
    lines = [
        f"## {run.get('model')}",
        f"- Success: {_yes_no(run.get('success'))}",
        f"- Latency: {run.get('latency_ms', 0):,} ms",
        f"- Structured output: {'valid' if run.get('parse_valid') else 'invalid'}",
    ]
    if run.get("error"):
        lines.append(f"- Error: {run.get('error')}")
        return "\n".join(lines)

    structured = run.get("structured_result")
    if isinstance(structured, dict):
        if structured.get("summary"):
            lines.append(f"\n### Response\n{structured.get('summary')}")
        elif structured.get("answer"):
            lines.append(f"\n### Response\n{structured.get('answer')}")
        elif structured.get("executive_summary"):
            lines.append(f"\n### Response\n{structured.get('executive_summary')}")
    elif isinstance(structured, list):
        lines.append("\n### Response")
        for item in structured[:8]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('fact') or item}")
            else:
                lines.append(f"- {item}")
    return "\n".join(lines)


def _header(result: dict[str, Any]) -> str:
    return (
        f"# {result.get('title') or 'Research Result'}\n\n"
        f"**Source:** {result.get('source_url', '')}\n\n"
        f"**Ingestion:** `{result.get('ingestion_method', 'unknown')}`\n\n"
        f"**Model:** `{result.get('model', '')}`"
    )


def _list_section(title: str, items: list[str]) -> str:
    if not items:
        return f"## {title}\n- None"
    return f"## {title}\n" + "\n".join(f"- {item}" for item in items)


def _yes_no(value: Any) -> str:
    return "Yes" if value else "No"


def _models_dataframe(models: dict[str, Any]) -> pd.DataFrame:
    rows = [
        {
            "model": model,
            "requests": values.get("requests", 0),
            "average_latency_ms": round(values.get("average_latency_ms", 0)),
            "average_latency_seconds": round(values.get("average_latency_ms", 0) / 1000, 2),
        }
        for model, values in models.items()
    ]
    return pd.DataFrame(rows, columns=[
        "model",
        "requests",
        "average_latency_ms",
        "average_latency_seconds",
    ])


def _counts_dataframe(values: dict[str, int], name_column: str) -> pd.DataFrame:
    rows = [{name_column: key, "count": value} for key, value in values.items()]
    return pd.DataFrame(rows, columns=[name_column, "count"])
