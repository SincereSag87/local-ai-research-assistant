from typing import Any

import httpx

from app.core.config import get_settings


class LocalAIClientError(Exception):
    """Base UI API client error."""


class LocalAIAPIError(LocalAIClientError):
    """Raised when the backend returns a structured API error."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class LocalAITimeoutError(LocalAIClientError):
    """Raised when the backend request times out."""


class LocalAIConnectionError(LocalAIClientError):
    """Raised when the backend cannot be reached."""


class LocalAIAPIClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 180.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or str(settings.api_base_url)).rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def ollama_health(self) -> dict[str, Any]:
        return self._request("GET", "/health/ollama")

    def generate(self, prompt: str, model: str | None = None) -> dict[str, Any]:
        return self._request("POST", "/research/generate", json={"prompt": prompt, "model": model})

    def summary(self, url: str, model: str | None = None) -> dict[str, Any]:
        return self._research_request("/research/summary", url=url, model=model)

    def facts(self, url: str, model: str | None = None) -> list[dict[str, Any]]:
        return self._research_request("/research/facts", url=url, model=model)

    def topics(self, url: str, model: str | None = None) -> list[str]:
        return self._research_request("/research/topics", url=url, model=model)

    def report(self, url: str, model: str | None = None) -> dict[str, Any]:
        return self._research_request("/research/report", url=url, model=model)

    def ask(self, url: str, question: str, model: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            "/research/ask",
            json={"url": url, "question": question, "model": model},
        )

    def compare(
        self,
        url: str,
        task: str,
        models: list[str],
        question: str | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/compare",
            json={"url": url, "task": task, "models": models, "question": question},
        )

    def _research_request(self, path: str, *, url: str, model: str | None) -> Any:
        return self._request("POST", path, json={"url": url, "model": model})

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> Any:
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = client.request(method, path, json=json)
        except httpx.TimeoutException as exc:
            raise LocalAITimeoutError("The backend request timed out.") from exc
        except httpx.ConnectError as exc:
            raise LocalAIConnectionError(
                f"Could not connect to the FastAPI backend at {self.base_url}."
            ) from exc
        except httpx.HTTPError as exc:
            raise LocalAIConnectionError(f"The backend request failed: {exc}") from exc

        if response.is_error:
            self._raise_api_error(response)
        return response.json()

    def _raise_api_error(self, response: httpx.Response) -> None:
        try:
            payload = response.json()
        except ValueError as exc:
            raise LocalAIAPIError(
                code="HTTP_ERROR",
                message=f"Backend returned HTTP {response.status_code}.",
                status_code=response.status_code,
            ) from exc

        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        detail = payload.get("detail") if isinstance(payload, dict) else None
        code = error.get("code") or "REQUEST_FAILED"
        message = error.get("message") or _format_detail(detail) or "The backend request failed."
        raise LocalAIAPIError(code=code, message=message, status_code=response.status_code)


def format_client_error(error: Exception) -> str:
    if isinstance(error, LocalAIAPIError):
        return f"{error.code}: {error}"
    if isinstance(error, LocalAITimeoutError):
        return "Request timed out. The local model may still be generating."
    if isinstance(error, LocalAIConnectionError):
        return str(error)
    return "An unexpected UI error occurred."


def _format_detail(detail: Any) -> str | None:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail:
        messages = []
        for item in detail:
            if isinstance(item, dict):
                location = ".".join(str(part) for part in item.get("loc", []))
                message = item.get("msg", "Invalid request")
                messages.append(f"{location}: {message}" if location else message)
        return "; ".join(messages)
    return None
