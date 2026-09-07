from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    request_id: str | None = None
    event: str
    task: str | None = None
    url: str | None = None
    model: str | None = None
    ingestion_method: str | None = None
    ingestion_ms: int | None = None
    model_latency_ms: int | None = None
    total_latency_ms: int | None = None
    success: bool
    parse_valid: bool | None = None
    error_category: str | None = None


class RequestMetrics(BaseModel):
    total: int = 0
    successful: int = 0
    failed: int = 0
    average_latency_ms: float = 0.0


class ModelMetrics(BaseModel):
    requests: int = 0
    average_latency_ms: float = 0.0


class MetricsSnapshot(BaseModel):
    requests: RequestMetrics = Field(default_factory=RequestMetrics)
    models: dict[str, ModelMetrics] = Field(default_factory=dict)
    tasks: dict[str, int] = Field(default_factory=dict)
    ingestion: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, int] = Field(default_factory=dict)
    parsing_failures: int = 0
    comparison_runs: int = 0
    unknown_answer_responses: int = 0
