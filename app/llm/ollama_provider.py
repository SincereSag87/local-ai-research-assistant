from collections.abc import Sequence

from openai import APIConnectionError, NotFoundError, OpenAI, OpenAIError

from app.core.config import Settings, get_settings
from app.llm.base import (
    LLMError,
    LLMModelNotFoundError,
    LLMProvider,
    LLMResponseError,
    LLMServiceUnavailableError,
)
from app.llm.models import ChatMessage, ChatResponse


class OllamaProvider(LLMProvider):
    """LLM provider backed by Ollama's OpenAI-compatible chat completions API."""

    def __init__(self, settings: Settings | None = None, client: OpenAI | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or OpenAI(
            base_url=str(self.settings.ollama_base_url),
            api_key="ollama",
        )

    def generate(
        self,
        messages: Sequence[ChatMessage],
        model: str | None = None,
    ) -> ChatResponse:
        selected_model = model or self.settings.default_model

        try:
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[message.model_dump() for message in messages],
            )
        except APIConnectionError as exc:
            raise LLMServiceUnavailableError(
                "Could not connect to Ollama at "
                f"{self.settings.ollama_base_url}. Start Ollama and try again."
            ) from exc
        except NotFoundError as exc:
            raise LLMModelNotFoundError(
                f"Model '{selected_model}' is not installed in Ollama. "
                f"Install it with: ollama pull {selected_model}"
            ) from exc
        except OpenAIError as exc:
            if "model" in str(exc).lower() and "not found" in str(exc).lower():
                raise LLMModelNotFoundError(
                    f"Model '{selected_model}' is not installed in Ollama. "
                    f"Install it with: ollama pull {selected_model}"
                ) from exc
            raise LLMError(f"Ollama request failed: {exc}") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMResponseError("Ollama returned a malformed chat completion response.") from exc

        if not content:
            raise LLMResponseError("Ollama returned an empty response.")

        return ChatResponse(model=selected_model, content=content)

