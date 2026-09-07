from collections.abc import Sequence

from app.evaluation import ModelComparator, ModelComparisonResult
from app.ingestion import WebIngestor
from app.llm import ChatMessage, ChatResponse, LLMProvider
from app.research import KeyFact, QuestionAnswer, ResearchEngine, ResearchReport, ResearchSummary


class ResearchService:
    """Application service layer for direct prompts and URL research tasks."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        web_ingestor: WebIngestor | None = None,
        research_engine: ResearchEngine | None = None,
        model_comparator: ModelComparator | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.web_ingestor = web_ingestor or WebIngestor()
        self.research_engine = research_engine or ResearchEngine(llm_provider=llm_provider)
        self.model_comparator = model_comparator or ModelComparator(llm_provider=llm_provider)

    def ask(self, prompt: str, model: str | None = None) -> ChatResponse:
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are a concise research assistant that explains "
                    "technical topics clearly."
                ),
            ),
            ChatMessage(role="user", content=prompt),
        ]
        return self.llm_provider.generate(messages=messages, model=model)

    def summarize_url(self, url: str, model: str | None = None) -> ResearchSummary:
        document = self.web_ingestor.ingest(url)
        return self.research_engine.summarize(document=document, model=model)

    def extract_facts_from_url(self, url: str, model: str | None = None) -> list[KeyFact]:
        document = self.web_ingestor.ingest(url)
        return self.research_engine.extract_facts(document=document, model=model)

    def extract_topics_from_url(self, url: str, model: str | None = None) -> list[str]:
        document = self.web_ingestor.ingest(url)
        return self.research_engine.extract_topics(document=document, model=model)

    def answer_url_question(
        self,
        url: str,
        question: str,
        model: str | None = None,
    ) -> QuestionAnswer:
        document = self.web_ingestor.ingest(url)
        return self.research_engine.answer_question(
            document=document,
            question=question,
            model=model,
        )

    def generate_url_report(self, url: str, model: str | None = None) -> ResearchReport:
        document = self.web_ingestor.ingest(url)
        return self.research_engine.generate_report(document=document, model=model)

    def compare_url_task(
        self,
        *,
        url: str,
        task: str,
        models: Sequence[str],
        question: str | None = None,
    ) -> ModelComparisonResult:
        document = self.web_ingestor.ingest(url)
        if task == "summary":
            return self.model_comparator.compare_summary(document=document, models=models)
        if task == "facts":
            return self.model_comparator.compare_facts(document=document, models=models)
        if task == "topics":
            return self.model_comparator.compare_topics(document=document, models=models)
        if task == "ask":
            if question is None:
                raise ValueError("question is required for ask comparison")
            return self.model_comparator.compare_question(
                document=document,
                question=question,
                models=models,
            )
        if task == "report":
            return self.model_comparator.compare_report(document=document, models=models)
        raise ValueError(f"Unsupported comparison task: {task}")
