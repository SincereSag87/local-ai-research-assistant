from typing import Any

import pandas as pd

from ui.api_client import LocalAIAPIClient, format_client_error
from ui.formatters import (
    format_comparison,
    format_facts,
    format_health,
    format_observability,
    format_question,
    format_report,
    format_summary,
    format_topics,
)

TASK_LABELS = {
    "Summary": "summary",
    "Facts": "facts",
    "Topics": "topics",
    "Ask": "ask",
    "Report": "report",
}
MODEL_CHOICES = ["llama3.2", "gemma3"]
EMPTY_DF = pd.DataFrame(columns=["model", "latency_seconds"])
EMPTY_MODEL_METRICS_DF = pd.DataFrame(
    columns=["model", "requests", "average_latency_ms", "average_latency_seconds"]
)
EMPTY_TASK_DF = pd.DataFrame(columns=["task", "count"])
EMPTY_INGESTION_DF = pd.DataFrame(columns=["method", "count"])


def refresh_health(client: LocalAIAPIClient | None = None) -> str:
    active_client = client or LocalAIAPIClient()
    try:
        return format_health(active_client.health(), active_client.ollama_health())
    except Exception as exc:
        return f"**API:** Offline\n\n**Status:** {format_client_error(exc)}"


def refresh_observability(
    client: LocalAIAPIClient | None = None,
) -> tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    active_client = client or LocalAIAPIClient()
    try:
        markdown, model_df, task_df, ingestion_df = format_observability(
            active_client.health(),
            active_client.ollama_health(),
            active_client.metrics(),
        )
        return markdown, model_df, task_df, ingestion_df, model_df, task_df
    except Exception as exc:
        return (
            f"## System Observability\n\nUnable to load metrics: {format_client_error(exc)}",
            EMPTY_MODEL_METRICS_DF,
            EMPTY_TASK_DF,
            EMPTY_INGESTION_DF,
            EMPTY_MODEL_METRICS_DF,
            EMPTY_TASK_DF,
        )


def run_research_task(
    url: str,
    task_label: str,
    model: str,
    question: str,
    client: LocalAIAPIClient | None = None,
) -> str:
    if not url.strip():
        return "Enter a URL before running a research task."
    task = TASK_LABELS[task_label]
    if task == "ask" and not question.strip():
        return "Enter a question before running the Ask task."

    active_client = client or LocalAIAPIClient()
    try:
        if task == "summary":
            return format_summary(active_client.summary(url=url, model=model))
        if task == "facts":
            return format_facts(active_client.facts(url=url, model=model))
        if task == "topics":
            return format_topics(active_client.topics(url=url, model=model))
        if task == "ask":
            return format_question(active_client.ask(url=url, question=question, model=model))
        if task == "report":
            return format_report(active_client.report(url=url, model=model))
    except Exception as exc:
        return f"Research request failed: {format_client_error(exc)}"

    return "Unsupported task selected."


def run_comparison_task(
    url: str,
    task_label: str,
    models: list[str],
    question: str,
    client: LocalAIAPIClient | None = None,
) -> tuple[str, pd.DataFrame, pd.DataFrame]:
    if not url.strip():
        return "Enter a URL before running model comparison.", pd.DataFrame(), EMPTY_DF
    if not models:
        return "Select at least one model to compare.", pd.DataFrame(), EMPTY_DF

    task = TASK_LABELS[task_label]
    if task == "ask" and not question.strip():
        return "Enter a question before comparing the Ask task.", pd.DataFrame(), EMPTY_DF

    active_client = client or LocalAIAPIClient()
    try:
        result = active_client.compare(
            url=url,
            task=task,
            models=models,
            question=question if task == "ask" else None,
        )
        return format_comparison(result)
    except Exception as exc:
        return f"Comparison request failed: {format_client_error(exc)}", pd.DataFrame(), EMPTY_DF


def question_visibility(task_label: str) -> dict[str, Any]:
    try:
        import gradio as gr

        return gr.update(visible=task_label == "Ask")
    except ImportError:
        return {"visible": task_label == "Ask"}
