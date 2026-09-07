import json

import pytest

from app.core.config import Settings
from app.ingestion import WebDocument
from app.llm import ChatResponse
from app.research import ResearchEngine, ResearchParseError
from app.research.prompts import UNKNOWN_ANSWER


class FakeProvider:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls = []

    def generate(self, messages, model=None):
        self.calls.append({"messages": messages, "model": model})
        content = self.responses.pop(0)
        return ChatResponse(model=model or "llama3.2", content=content)


def make_document(text: str = "Edward Donner teaches AI engineering and agentic coding."):
    return WebDocument(
        url="https://edwarddonner.com",
        final_url="https://edwarddonner.com",
        title="Home - Edward Donner",
        text=text,
        links=[],
        description="AI resources",
        source_type="static",
        status_code=200,
    )


def test_engine_generates_structured_summary_and_propagates_model_override():
    provider = FakeProvider(
        [
            json.dumps(
                {
                    "summary": "Edward Donner publishes AI engineering resources.",
                    "key_points": ["AI Engineering MLOps Track is listed."],
                    "topics": ["AI engineering", "MLOps"],
                }
            )
        ]
    )
    engine = ResearchEngine(provider, settings=Settings(max_context_chars=2000))

    result = engine.summarize(make_document(), model="gemma3")

    assert result.model == "gemma3"
    assert result.ingestion_method == "static"
    assert result.topics == ["AI engineering", "MLOps"]
    assert provider.calls[0]["model"] == "gemma3"


def test_engine_extracts_key_facts():
    provider = FakeProvider(
        [
            json.dumps(
                {
                    "facts": [
                        {
                            "fact": "The page lists an AI Engineering MLOps Track.",
                            "evidence": "AI Engineering MLOps Track",
                            "confidence": "high",
                        }
                    ]
                }
            )
        ]
    )

    facts = ResearchEngine(provider).extract_facts(make_document())

    assert facts[0].fact.startswith("The page lists")
    assert facts[0].confidence == "high"


def test_engine_extracts_topics():
    provider = FakeProvider([json.dumps({"topics": ["AI", "Agents"]})])

    assert ResearchEngine(provider).extract_topics(make_document()) == ["AI", "Agents"]


def test_engine_answers_question_with_evidence():
    provider = FakeProvider(
        [
            json.dumps(
                {
                    "answer": "Edward Donner teaches AI engineering.",
                    "evidence": ["teaches AI engineering"],
                }
            )
        ]
    )

    answer = ResearchEngine(provider).answer_question(
        make_document(),
        "What does Edward Donner do?",
    )

    assert answer.answer == "Edward Donner teaches AI engineering."
    assert answer.evidence == ["teaches AI engineering"]


def test_engine_drops_null_question_evidence_from_model_output():
    provider = FakeProvider(
        [
            json.dumps(
                {
                    "answer": "The page does not provide a detailed professional background.",
                    "evidence": [None],
                }
            )
        ]
    )

    answer = ResearchEngine(provider).answer_question(
        make_document(),
        "What is Edward Donner's professional background?",
    )

    assert answer.evidence == []


def test_engine_preserves_unknown_answer_behavior_from_model_output():
    provider = FakeProvider([json.dumps({"answer": UNKNOWN_ANSWER, "evidence": []})])

    answer = ResearchEngine(provider).answer_question(
        make_document(),
        "What is his favorite database?",
    )

    assert answer.answer == UNKNOWN_ANSWER
    assert answer.evidence == []


def test_engine_generates_report():
    provider = FakeProvider(
        [
            json.dumps(
                {
                    "executive_summary": "The page is an AI resource hub.",
                    "key_findings": ["It lists AI courses."],
                    "topics": ["AI courses"],
                    "notable_facts": [
                        {
                            "fact": "The page mentions AI engineering.",
                            "evidence": "AI engineering",
                            "confidence": "medium",
                        }
                    ],
                    "questions_or_gaps": ["Detailed biography is not present."],
                }
            )
        ]
    )

    report = ResearchEngine(provider).generate_report(make_document())

    assert report.executive_summary == "The page is an AI resource hub."
    assert report.notable_facts[0].evidence == "AI engineering"
    assert report.questions_or_gaps == ["Detailed biography is not present."]


def test_engine_raises_on_malformed_model_output():
    provider = FakeProvider(["not json"])

    with pytest.raises(ResearchParseError):
        ResearchEngine(provider).summarize(make_document())


def test_engine_applies_context_truncation_to_prompt():
    provider = FakeProvider([json.dumps({"topics": ["AI"]})])
    document = make_document("A" * 3000 + "Z" * 3000)

    ResearchEngine(provider, settings=Settings(max_context_chars=1500)).extract_topics(document)

    prompt = provider.calls[0]["messages"][1].content
    assert "content truncated" in prompt
    assert len(prompt) < 3000
