from typing import Any

from pydantic import BaseModel, field_validator

from app.core.config import Settings, get_settings
from app.ingestion import WebDocument
from app.llm import ChatMessage, ChatResponse, LLMProvider
from app.observability.tracing import timer
from app.research.models import KeyFact, QuestionAnswer, ResearchReport, ResearchSummary
from app.research.parsers import parse_model
from app.research.prompts import (
    build_fact_extraction_messages,
    build_question_messages,
    build_research_report_messages,
    build_summary_messages,
    build_topic_extraction_messages,
)


class _FactsPayload(BaseModel):
    facts: list[KeyFact]


class _TopicsPayload(BaseModel):
    topics: list[str]


class _SummaryPayload(BaseModel):
    summary: str
    key_points: list[str] = []
    topics: list[str] = []


class _QuestionPayload(BaseModel):
    answer: str
    evidence: list[str] = []

    @field_validator("evidence", mode="before")
    @classmethod
    def _remove_empty_evidence(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, str) and value.strip():
            return [value]
        return []


class _ReportPayload(BaseModel):
    executive_summary: str
    key_findings: list[str] = []
    topics: list[str] = []
    notable_facts: list[KeyFact] = []
    questions_or_gaps: list[str] = []


class ResearchEngine:
    """Model-independent research tasks over an already-ingested WebDocument."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        settings: Settings | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.settings = settings or get_settings()
        self.last_model_latency_ms = 0

    def summarize(self, document: WebDocument, model: str | None = None) -> ResearchSummary:
        response = self._generate(
            messages=build_summary_messages(document, settings=self.settings),
            model=model,
        )
        payload = parse_model(response.content, _SummaryPayload)
        return ResearchSummary(
            title=document.title,
            source_url=document.final_url,
            model=response.model,
            summary=payload.summary,
            key_points=payload.key_points,
            topics=payload.topics,
            ingestion_method=document.source_type,
        )

    def extract_facts(self, document: WebDocument, model: str | None = None) -> list[KeyFact]:
        response = self._generate(
            messages=build_fact_extraction_messages(document, settings=self.settings),
            model=model,
        )
        return parse_model(response.content, _FactsPayload).facts

    def extract_topics(self, document: WebDocument, model: str | None = None) -> list[str]:
        response = self._generate(
            messages=build_topic_extraction_messages(document, settings=self.settings),
            model=model,
        )
        return parse_model(response.content, _TopicsPayload).topics

    def answer_question(
        self,
        document: WebDocument,
        question: str,
        model: str | None = None,
    ) -> QuestionAnswer:
        response = self._generate(
            messages=build_question_messages(document, question, settings=self.settings),
            model=model,
        )
        payload = parse_model(response.content, _QuestionPayload)
        return QuestionAnswer(
            question=question,
            answer=payload.answer,
            evidence=payload.evidence,
            source_url=document.final_url,
            model=response.model,
        )

    def generate_report(self, document: WebDocument, model: str | None = None) -> ResearchReport:
        response = self._generate(
            messages=build_research_report_messages(document, settings=self.settings),
            model=model,
        )
        payload = parse_model(response.content, _ReportPayload)
        return ResearchReport(
            title=document.title,
            source_url=document.final_url,
            executive_summary=payload.executive_summary,
            key_findings=payload.key_findings,
            topics=payload.topics,
            notable_facts=payload.notable_facts,
            questions_or_gaps=payload.questions_or_gaps,
            model=response.model,
            ingestion_method=document.source_type,
        )

    def _generate(self, messages: list[ChatMessage], model: str | None) -> ChatResponse:
        with timer() as model_timer:
            response = self.llm_provider.generate(messages=messages, model=model)
        self.last_model_latency_ms = model_timer.elapsed_ms
        return response
