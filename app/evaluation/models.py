from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

ComparisonTask = Literal["summary", "facts", "topics", "ask", "report"]


class EvaluationMetrics(BaseModel):
    grounded: bool
    contains_required_fields: bool
    answer_present_behavior: str | None = None
    completeness_score: int = Field(ge=0)
    completeness_checks: dict[str, bool] = Field(default_factory=dict)
    response_length: int = 0
    word_count: int = 0
    bullet_count: int = 0
    fact_count: int = 0
    latency_ms: int


class ModelRunResult(BaseModel):
    model: str
    task: ComparisonTask
    success: bool
    latency_ms: int
    response_text: str
    structured_result: Any = None
    response_chars: int
    parse_valid: bool
    metrics: EvaluationMetrics | None = None
    error: str | None = None


class ModelComparisonResult(BaseModel):
    task: ComparisonTask
    source_url: HttpUrl
    ingestion_method: str
    runs: list[ModelRunResult]
    fastest_model: str | None = None
    valid_models: list[str] = Field(default_factory=list)
    summary: str
