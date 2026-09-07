from types import SimpleNamespace

import pytest
from openai import APIConnectionError, NotFoundError
from pydantic import HttpUrl

from app.core.config import Settings
from app.llm import (
    ChatMessage,
    LLMModelNotFoundError,
    LLMResponseError,
    LLMServiceUnavailableError,
    OllamaProvider,
)


class FakeCompletions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        if self.error:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)


def make_settings(default_model: str = "llama3.2") -> Settings:
    return Settings(
        ollama_base_url=HttpUrl("http://localhost:11434/v1"),
        default_model=default_model,
    )


def make_response(content: str = "Local LLMs run on your own hardware."):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


def test_generate_uses_default_model_and_returns_content():
    completions = FakeCompletions(response=make_response())
    provider = OllamaProvider(settings=make_settings(), client=FakeClient(completions))

    response = provider.generate([ChatMessage(role="user", content="Explain local LLMs.")])

    assert response.model == "llama3.2"
    assert response.content == "Local LLMs run on your own hardware."
    assert completions.last_request["model"] == "llama3.2"
    assert completions.last_request["messages"] == [
        {"role": "user", "content": "Explain local LLMs."}
    ]


def test_generate_supports_model_override():
    completions = FakeCompletions(response=make_response("Gemma response."))
    provider = OllamaProvider(settings=make_settings(), client=FakeClient(completions))

    response = provider.generate(
        [ChatMessage(role="user", content="Explain local LLMs.")],
        model="gemma3",
    )

    assert response.model == "gemma3"
    assert completions.last_request["model"] == "gemma3"


def test_connection_error_becomes_service_unavailable():
    completions = FakeCompletions(error=APIConnectionError(request=None))
    provider = OllamaProvider(settings=make_settings(), client=FakeClient(completions))

    with pytest.raises(LLMServiceUnavailableError, match="Could not connect to Ollama"):
        provider.generate([ChatMessage(role="user", content="Hello")])


def test_not_found_error_becomes_model_not_found():
    response = SimpleNamespace(status_code=404, headers={}, request=None)
    error = NotFoundError("model not found", response=response, body=None)
    completions = FakeCompletions(error=error)
    provider = OllamaProvider(settings=make_settings(), client=FakeClient(completions))

    with pytest.raises(LLMModelNotFoundError, match="ollama pull gemma3"):
        provider.generate([ChatMessage(role="user", content="Hello")], model="gemma3")


def test_malformed_response_raises_response_error():
    completions = FakeCompletions(response=SimpleNamespace(choices=[]))
    provider = OllamaProvider(settings=make_settings(), client=FakeClient(completions))

    with pytest.raises(LLMResponseError, match="malformed"):
        provider.generate([ChatMessage(role="user", content="Hello")])


def test_empty_response_raises_response_error():
    completions = FakeCompletions(response=make_response(""))
    provider = OllamaProvider(settings=make_settings(), client=FakeClient(completions))

    with pytest.raises(LLMResponseError, match="empty"):
        provider.generate([ChatMessage(role="user", content="Hello")])

