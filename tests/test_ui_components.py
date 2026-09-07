from ui.components import (
    refresh_health,
    refresh_observability,
    run_comparison_task,
    run_research_task,
)


class FakeClient:
    def __init__(self):
        self.calls = []

    def health(self):
        return {"status": "ok"}

    def ollama_health(self):
        return {
            "reachable": True,
            "default_model": "llama3.2",
            "base_url": "http://localhost:11434/v1",
        }

    def metrics(self):
        return {
            "requests": {"total": 1, "successful": 1, "failed": 0, "average_latency_ms": 10},
            "models": {"llama3.2": {"requests": 1, "average_latency_ms": 200}},
            "tasks": {"summary": 1},
            "ingestion": {"static": 1},
            "comparison_runs": 0,
            "parsing_failures": 0,
            "unknown_answer_responses": 0,
        }

    def summary(self, url, model):
        self.calls.append(("summary", url, model))
        return {
            "title": "Example",
            "source_url": url,
            "ingestion_method": "static",
            "model": model,
            "summary": "Summary",
            "key_points": [],
            "topics": [],
        }

    def ask(self, url, question, model):
        self.calls.append(("ask", url, question, model))
        return {
            "question": question,
            "answer": "Answer",
            "evidence": [],
            "source_url": url,
            "model": model,
        }

    def compare(self, url, task, models, question=None):
        self.calls.append(("compare", url, task, models, question))
        return {
            "task": task,
            "source_url": url,
            "ingestion_method": "static",
            "fastest_model": models[0],
            "valid_models": models,
            "runs": [],
        }


def test_refresh_health_uses_backend_status():
    assert "**API:** Online" in refresh_health(FakeClient())


def test_research_callback_validates_url_and_question():
    assert "Enter a URL" in run_research_task("", "Summary", "llama3.2", "")
    assert "Enter a question" in run_research_task(
        "https://example.com", "Ask", "llama3.2", ""
    )


def test_research_callback_maps_summary_and_ask():
    client = FakeClient()

    summary = run_research_task("https://example.com", "Summary", "llama3.2", "", client)
    ask = run_research_task("https://example.com", "Ask", "gemma3", "What?", client)

    assert "Summary" in summary
    assert "Answer" in ask
    assert client.calls == [
        ("summary", "https://example.com", "llama3.2"),
        ("ask", "https://example.com", "What?", "gemma3"),
    ]


def test_comparison_callback_validates_inputs_and_maps_request():
    assert "Select at least one model" in run_comparison_task(
        "https://example.com", "Summary", [], ""
    )[0]

    client = FakeClient()
    markdown, table, chart = run_comparison_task(
        "https://example.com",
        "Ask",
        ["llama3.2", "gemma3"],
        "What?",
        client,
    )

    assert "Comparison" in markdown
    assert table.empty
    assert chart.empty
    assert client.calls == [
        ("compare", "https://example.com", "ask", ["llama3.2", "gemma3"], "What?")
    ]


def test_refresh_observability_returns_markdown_tables_and_chart_data():
    markdown, model_df, task_df, ingestion_df, chart_df, task_chart_df = refresh_observability(
        FakeClient()
    )

    assert "System Observability" in markdown
    assert model_df.iloc[0]["model"] == "llama3.2"
    assert task_df.iloc[0]["task"] == "summary"
    assert ingestion_df.iloc[0]["method"] == "static"
    assert chart_df.iloc[0]["average_latency_ms"] == 200
    assert task_chart_df.iloc[0]["count"] == 1
