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
