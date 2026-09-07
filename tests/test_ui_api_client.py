import httpx
import pytest

from ui.api_client import (
    LocalAIAPIClient,
    LocalAIAPIError,
    LocalAIConnectionError,
    LocalAITimeoutError,
)


def make_client(handler):
    return LocalAIAPIClient(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    )


def test_api_client_health_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok"})

    assert make_client(handler).health() == {"status": "ok"}


def test_api_client_metrics_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/metrics"
        return httpx.Response(200, json={"requests": {"total": 2}})

    assert make_client(handler).metrics() == {"requests": {"total": 2}}


def test_api_client_research_request_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/research/summary"
        assert request.read() == b'{"url":"https://example.com","model":"gemma3"}'
        return httpx.Response(200, json={"summary": "ok"})

    assert make_client(handler).summary("https://example.com", "gemma3") == {"summary": "ok"}


def test_api_client_compare_request_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/compare"
        assert request.read() == (
            b'{"url":"https://example.com","task":"ask","models":["llama3.2","gemma3"],'
            b'"question":"What is this?"}'
        )
        return httpx.Response(200, json={"task": "ask"})

    result = make_client(handler).compare(
        url="https://example.com",
        task="ask",
        models=["llama3.2", "gemma3"],
        question="What is this?",
    )

    assert result == {"task": "ask"}


def test_api_client_api_error_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"error": {"code": "OLLAMA_UNAVAILABLE", "message": "Ollama is down."}},
        )

    with pytest.raises(LocalAIAPIError) as exc_info:
        make_client(handler).health()

    assert exc_info.value.code == "OLLAMA_UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == "Ollama is down."


def test_api_client_validation_error_detail_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": [{"loc": ["body", "url"], "msg": "Input should be a valid URL"}]},
        )

    with pytest.raises(LocalAIAPIError, match="body.url"):
        make_client(handler).summary("bad", "llama3.2")


def test_api_client_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow", request=request)

    with pytest.raises(LocalAITimeoutError):
        make_client(handler).health()


def test_api_client_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(LocalAIConnectionError):
        make_client(handler).health()
