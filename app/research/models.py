from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

ConfidenceLabel = Literal["low", "medium", "high"]


class KeyFact(BaseModel):
    fact: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    confidence: ConfidenceLabel = "medium"


class ResearchSummary(BaseModel):
    title: str | None = None
    source_url: HttpUrl
    model: str
    summary: str = Field(min_length=1)
    key_points: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    ingestion_method: str


class QuestionAnswer(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    source_url: HttpUrl
    model: str


class ResearchReport(BaseModel):
    title: str | None = None
    source_url: HttpUrl
    executive_summary: str = Field(min_length=1)
    key_findings: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    notable_facts: list[KeyFact] = Field(default_factory=list)
    questions_or_gaps: list[str] = Field(default_factory=list)
    model: str
    ingestion_method: str
