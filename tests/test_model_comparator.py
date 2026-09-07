import json

from app.evaluation import ModelComparator
from app.evaluation.formatter import format_comparison_json, format_comparison_text
from app.ingestion import WebDocument
from app.llm import ChatResponse


class FakeProvider:
    def __init__(self, responses_by_model: dict[str, str | Exception]):
        self.responses_by_model = responses_by_model
        self.models_seen = []

    def generate(self, messages, model=None):
        self.models_seen.append(model)
        response = self.responses_by_model[model]
        if isinstance(response, Exception):
            raise response
        return ChatResponse(model=model or "llama3.2", content=response)


def make_document() -> WebDocument:
    return WebDocument(
        url="https://example.com",
        final_url="https://example.com/final",
        title="Example",
        text="This page describes AI engineering resources and local model workflows.",
        links=[],
        source_type="static",
        status_code=200,
    )


def test_comparator_records_latency_for_two_successful_models(monkeypatch):
    times = iter([1.0, 1.25, 3.0, 3.5])
    monkeypatch.setattr("app.evaluation.comparator.time.monotonic", lambda: next(times))
    provider = FakeProvider(
        {
            "llama3.2": json.dumps(
                {"summary": "Summary", "key_points": ["Point"], "topics": ["AI"]}
            ),
            "gemma3": json.dumps(
                {"summary": "Summary 2", "key_points": ["Point"], "topics": ["AI"]}
            ),
        }
    )

    result = ModelComparator(provider).compare_summary(make_document(), ["llama3.2", "gemma3"])

    assert [run.model for run in result.runs] == ["llama3.2", "gemma3"]
    assert [run.latency_ms for run in result.runs] == [250, 500]
    assert result.fastest_model == "llama3.2"
    assert result.valid_models == ["llama3.2", "gemma3"]
    assert provider.models_seen == ["llama3.2", "gemma3"]


def test_comparator_isolates_one_model_failure():
    provider = FakeProvider(
        {
            "llama3.2": json.dumps(
                {"summary": "Summary", "key_points": ["Point"], "topics": ["AI"]}
            ),
            "gemma3": RuntimeError("model unavailable"),
        }
    )

    result = ModelComparator(provider).compare_summary(make_document(), ["llama3.2", "gemma3"])

    assert result.runs[0].success is True
    assert result.runs[1].success is False
    assert "model unavailable" in result.runs[1].error
    assert result.valid_models == ["llama3.2"]


def test_comparator_captures_malformed_structured_output():
    provider = FakeProvider(
        {
            "llama3.2": "not json",
            "gemma3": json.dumps(
                {"summary": "Summary", "key_points": ["Point"], "topics": ["AI"]}
            ),
        }
    )

    result = ModelComparator(provider).compare_summary(make_document(), ["llama3.2", "gemma3"])

    assert result.runs[0].success is False
    assert result.runs[0].parse_valid is False
    assert "Structured output parsing failed" in result.runs[0].error
    assert result.runs[1].success is True


def test_comparator_supports_facts_question_and_report():
    provider = FakeProvider(
        {
            "llama3.2": json.dumps(
                {
                    "facts": [
                        {"fact": "Fact", "evidence": "Evidence", "confidence": "high"}
                    ]
                }
            ),
            "gemma3": json.dumps({"answer": "Answer", "evidence": ["Evidence"]}),
            "report-model": json.dumps(
                {
                    "executive_summary": "Report",
                    "key_findings": ["Finding"],
                    "topics": ["Topic"],
                    "notable_facts": [
                        {"fact": "Fact", "evidence": "Evidence", "confidence": "medium"}
                    ],
                    "questions_or_gaps": ["Gap"],
                }
            ),
        }
    )
    comparator = ModelComparator(provider)
    document = make_document()

    facts = comparator.compare_facts(document, ["llama3.2"])
    question = comparator.compare_question(document, "What is this?", ["gemma3"])
    report = comparator.compare_report(document, ["report-model"])

    assert facts.runs[0].metrics.fact_count == 1
    assert question.runs[0].metrics.answer_present_behavior == "answered_with_evidence"
    assert report.runs[0].metrics.contains_required_fields is True


def test_formatter_outputs_text_and_json():
    provider = FakeProvider(
        {
            "llama3.2": json.dumps(
                {"summary": "Summary", "key_points": ["Point"], "topics": ["AI"]}
            )
        }
    )
    result = ModelComparator(provider).compare_summary(make_document(), ["llama3.2"])

    text = format_comparison_text(result)
    json_text = format_comparison_json(result)

    assert "Fastest: llama3.2" in text
    assert json.loads(json_text)["valid_models"] == ["llama3.2"]
