from ui.formatters import (
    format_comparison,
    format_facts,
    format_health,
    format_question,
    format_report,
    format_summary,
    format_topics,
)


def test_format_health():
    markdown = format_health(
        {"status": "ok"},
        {
            "reachable": True,
            "default_model": "llama3.2",
            "base_url": "http://localhost:11434/v1",
        },
    )

    assert "**API:** Online" in markdown
    assert "**Ollama:** Reachable" in markdown


def test_format_summary():
    markdown = format_summary(
        {
            "title": "Example",
            "source_url": "https://example.com",
            "ingestion_method": "static",
            "model": "llama3.2",
            "summary": "Useful summary.",
            "key_points": ["Point"],
            "topics": ["Topic"],
        }
    )

    assert "# Example" in markdown
    assert "Useful summary." in markdown
    assert "- Point" in markdown


def test_format_facts():
    markdown = format_facts(
        [{"fact": "Fact", "evidence": "Evidence", "confidence": "high"}]
    )

    assert "## Key Facts" in markdown
    assert "Evidence" in markdown
    assert "high" in markdown


def test_format_topics():
    assert "- AI" in format_topics(["AI"])


def test_format_question():
    markdown = format_question(
        {
            "question": "What is this?",
            "answer": "Answer",
            "evidence": ["Evidence"],
            "source_url": "https://example.com",
            "model": "gemma3",
        }
    )

    assert "## Question" in markdown
    assert "Answer" in markdown
    assert "- Evidence" in markdown


def test_format_report():
    markdown = format_report(
        {
            "title": "Example",
            "source_url": "https://example.com",
            "ingestion_method": "static",
            "model": "llama3.2",
            "executive_summary": "Executive summary",
            "key_findings": ["Finding"],
            "topics": ["Topic"],
            "notable_facts": [
                {"fact": "Fact", "evidence": "Evidence", "confidence": "medium"}
            ],
            "questions_or_gaps": ["Gap"],
        }
    )

    assert "## Executive Summary" in markdown
    assert "- Fact" in markdown
    assert "- Gap" in markdown


def test_format_comparison_returns_markdown_table_and_chart_data():
    markdown, table, chart = format_comparison(
        {
            "task": "summary",
            "source_url": "https://example.com",
            "ingestion_method": "static",
            "fastest_model": "llama3.2",
            "valid_models": ["llama3.2"],
            "runs": [
                {
                    "model": "llama3.2",
                    "success": True,
                    "latency_ms": 1500,
                    "parse_valid": True,
                    "response_chars": 120,
                    "structured_result": {"summary": "Summary"},
                    "metrics": {
                        "contains_required_fields": True,
                        "grounded": True,
                        "word_count": 20,
                        "fact_count": 0,
                    },
                }
            ],
        }
    )

    assert "Fastest model" in markdown
    assert table.iloc[0]["model"] == "llama3.2"
    assert chart.iloc[0]["latency_seconds"] == 1.5
