from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.dependencies import get_ollama_readiness, get_research_service
from app.core.config import Settings
from app.evaluation import ModelComparisonResult
from app.ingestion import IngestionError
from app.llm import LLMModelNotFoundError, LLMServiceUnavailableError
from app.research import (
    KeyFact,
    QuestionAnswer,
    ResearchParseError,
    ResearchReport,
    ResearchSummary,
)


class FakeResearchService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def summarize_url(self, url: str, model: str | None = None) -> ResearchSummary:
        self._maybe_raise()
        self.calls.append(("summary", {"url": url, "model": model}))
        return ResearchSummary(
            title="Example",
            source_url=url,
            model=model or "llama3.2",
            summary="Summary",
            key_points=["Point"],
            topics=["Topic"],
            ingestion_method="static",
        )

    def ask(self, prompt: str, model: str | None = None):
        self._maybe_raise()
        self.calls.append(("generate", {"prompt": prompt, "model": model}))
        return {"model": model or "llama3.2", "content": "Generated response"}

    def extract_facts_from_url(self, url: str, model: str | None = None) -> list[KeyFact]:
        self._maybe_raise()
        self.calls.append(("facts", {"url": url, "model": model}))
        return [KeyFact(fact="Fact", evidence="Evidence", confidence="high")]

    def extract_topics_from_url(self, url: str, model: str | None = None) -> list[str]:
        self._maybe_raise()
        self.calls.append(("topics", {"url": url, "model": model}))
        return ["Topic"]

    def generate_url_report(self, url: str, model: str | None = None) -> ResearchReport:
        self._maybe_raise()
        self.calls.append(("report", {"url": url, "model": model}))
        return ResearchReport(
            title="Example",
            source_url=url,
            executive_summary="Executive summary",
            key_findings=["Finding"],
            topics=["Topic"],
            notable_facts=[KeyFact(fact="Fact", evidence="Evidence", confidence="medium")],
            questions_or_gaps=[],
            model=model or "llama3.2",
            ingestion_method="static",
        )

    def answer_url_question(
        self,
        url: str,
        question: str,
        model: str | None = None,
    ) -> QuestionAnswer:
        self._maybe_raise()
        self.calls.append(("ask", {"url": url, "question": question, "model": model}))
        return QuestionAnswer(
            question=question,
            answer="Answer",
            evidence=["Evidence"],
            source_url=url,
            model=model or "llama3.2",
        )

    def compare_url_task(
        self,
        *,
        url: str,
        task: str,
        models: list[str],
        question: str | None = None,
    ) -> ModelComparisonResult:
        self._maybe_raise()
        self.calls.append(
            ("compare", {"url": url, "task": task, "models": models, "question": question})
        )
        return ModelComparisonResult(
            task=task,
            source_url=url,
            ingestion_method="static",
            runs=[],
            fastest_model=models[0],
            valid_models=models,
            summary="Compared models.",
        )

    def _maybe_raise(self) -> None:
        if self.error:
            raise self.error


@pytest.fixture
def fake_service() -> FakeResearchService:
    return FakeResearchService()


@pytest.fixture
def client(fake_service: FakeResearchService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_research_service] = lambda: fake_service
    app.dependency_overrides[get_ollama_readiness] = lambda: {
        "status": "ok",
        "service": "ollama",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "reachable": True,
    }
    return TestClient(app, raise_server_exceptions=False)


def make_client_with_error(error: Exception) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_research_service] = lambda: FakeResearchService(error=error)
    return TestClient(app, raise_server_exceptions=False)


def test_health(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "local-ai-research-assistant"}


def test_ollama_health_reachable(client: TestClient):
    response = client.get("/health/ollama")

    assert response.status_code == 200
    assert response.json()["reachable"] is True


def test_ollama_health_unavailable():
    app = create_app()
    app.dependency_overrides[get_ollama_readiness] = lambda: {
        "status": "degraded",
        "service": "ollama",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "reachable": False,
    }
    response = TestClient(app).get("/health/ollama")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["reachable"] is False


def test_ollama_readiness_checks_openai_compatible_models_url(monkeypatch):
    captured = {}

    class FakeResponse:
        ok = True

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("app.api.dependencies.requests.get", fake_get)

    readiness = get_ollama_readiness(Settings(ollama_base_url="http://localhost:11434/v1"))

    assert readiness["reachable"] is True
    assert captured["url"] == "http://localhost:11434/v1/models"


def test_research_summary_endpoint(client: TestClient, fake_service: FakeResearchService):
    response = client.post(
        "/research/summary",
        json={"url": "https://example.com", "model": "gemma3"},
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Summary"
    assert fake_service.calls == [
        ("summary", {"url": "https://example.com/", "model": "gemma3"})
    ]


def test_research_generate_endpoint(client: TestClient, fake_service: FakeResearchService):
    response = client.post(
        "/research/generate",
        json={"prompt": "Explain local LLMs.", "model": "llama3.2"},
    )

    assert response.status_code == 200
    assert response.json()["content"] == "Generated response"
    assert fake_service.calls == [
        ("generate", {"prompt": "Explain local LLMs.", "model": "llama3.2"})
    ]


def test_research_facts_topics_report_and_ask(
    client: TestClient,
    fake_service: FakeResearchService,
):
    assert client.post("/research/facts", json={"url": "https://example.com"}).status_code == 200
    assert client.post("/research/topics", json={"url": "https://example.com"}).status_code == 200
    assert client.post("/research/report", json={"url": "https://example.com"}).status_code == 200
    ask_response = client.post(
        "/research/ask",
        json={"url": "https://example.com", "question": "What is this?", "model": "llama3.2"},
    )

    assert ask_response.status_code == 200
    assert ask_response.json()["answer"] == "Answer"
    assert [call[0] for call in fake_service.calls] == ["facts", "topics", "report", "ask"]
    assert fake_service.calls[-1][1] == {
        "url": "https://example.com/",
        "question": "What is this?",
        "model": "llama3.2",
    }


def test_compare_endpoint(client: TestClient, fake_service: FakeResearchService):
    response = client.post(
        "/compare",
        json={
            "url": "https://example.com",
            "task": "ask",
            "models": ["llama3.2", "gemma3"],
            "question": "What is this?",
        },
    )

    assert response.status_code == 200
    assert response.json()["valid_models"] == ["llama3.2", "gemma3"]
    assert fake_service.calls == [
        (
            "compare",
            {
                "url": "https://example.com/",
                "task": "ask",
                "models": ["llama3.2", "gemma3"],
                "question": "What is this?",
            },
        )
    ]


def test_compare_requires_question_for_ask(client: TestClient):
    response = client.post(
        "/compare",
        json={"url": "https://example.com", "task": "ask", "models": ["llama3.2"]},
    )

    assert response.status_code == 422


def test_validation_errors(client: TestClient):
    assert client.post("/research/summary", json={"url": "ftp://example.com"}).status_code == 422
    assert client.post("/research/ask", json={"url": "https://example.com"}).status_code == 422
    assert (
        client.post(
            "/compare",
            json={"url": "https://example.com", "task": "summary", "models": []},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/compare",
            json={"url": "https://example.com", "task": "unsupported", "models": ["llama3.2"]},
        ).status_code
        == 422
    )


def test_error_mapping():
    cases = [
        (IngestionError("bad url"), 422, "INGESTION_FAILED"),
        (LLMServiceUnavailableError("down"), 503, "OLLAMA_UNAVAILABLE"),
        (LLMModelNotFoundError("missing"), 503, "MODEL_UNAVAILABLE"),
        (ResearchParseError("bad json"), 502, "RESEARCH_PARSE_FAILED"),
        (RuntimeError("boom"), 500, "INTERNAL_ERROR"),
    ]

    for error, expected_status, expected_code in cases:
        response = make_client_with_error(error).post(
            "/research/summary",
            json={"url": "https://example.com"},
        )
        assert response.status_code == expected_status
        assert response.json()["error"]["code"] == expected_code


def test_openapi_contains_major_endpoints(client: TestClient):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/research/generate" in paths
    assert "/research/summary" in paths
    assert "/research/ask" in paths
    assert "/compare" in paths
