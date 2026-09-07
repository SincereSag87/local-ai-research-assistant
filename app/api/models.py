from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.evaluation.models import ComparisonTask


class URLResearchRequest(BaseModel):
    url: HttpUrl
    model: str | None = None

    @field_validator("url")
    @classmethod
    def require_http_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("URL must use http or https")
        return value


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None


class QuestionRequest(URLResearchRequest):
    question: str = Field(min_length=1)


class ComparisonRequest(BaseModel):
    url: HttpUrl
    task: ComparisonTask
    models: list[str] = Field(min_length=1)
    question: str | None = None

    @field_validator("url")
    @classmethod
    def require_http_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme not in {"http", "https"}:
            raise ValueError("URL must use http or https")
        return value

    @field_validator("models")
    @classmethod
    def require_model_names(cls, value: list[str]) -> list[str]:
        cleaned = [model.strip() for model in value if model.strip()]
        if not cleaned:
            raise ValueError("At least one comparison model is required")
        return cleaned

    @field_validator("question")
    @classmethod
    def require_non_empty_question(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Question cannot be empty")
        return value


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class OllamaHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    base_url: str
    default_model: str
    reachable: bool
