from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.llm.models import ChatMessage, ChatResponse


class LLMError(Exception):
    """Base exception for LLM provider failures."""


class LLMServiceUnavailableError(LLMError):
    """Raised when the local LLM service is unavailable."""


class LLMModelNotFoundError(LLMError):
    """Raised when the requested model is not installed or unavailable."""


class LLMResponseError(LLMError):
    """Raised when a provider returns an invalid or unusable response."""


class LLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        messages: Sequence[ChatMessage],
        model: str | None = None,
    ) -> ChatResponse:
        """Generate a chat completion from structured messages."""

