from pydantic import BaseModel, HttpUrl

from app.ingestion import WebDocument, WebIngestor
from app.llm import ChatMessage, ChatResponse, LLMProvider


class UrlSummaryResult(BaseModel):
    source_url: HttpUrl
    final_url: HttpUrl
    title: str | None
    model: str
    summary: str
    ingestion_method: str
    metadata: dict[str, str]


class ResearchService:
    """Thin service layer for research-oriented LLM interactions."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        web_ingestor: WebIngestor | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.web_ingestor = web_ingestor or WebIngestor()

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

    def summarize_url(self, url: str, model: str | None = None) -> UrlSummaryResult:
        document = self.web_ingestor.ingest(url)
        response = self.llm_provider.generate(
            messages=self._build_summary_messages(document),
            model=model,
        )
        return UrlSummaryResult(
            source_url=document.url,
            final_url=document.final_url,
            title=document.title,
            model=response.model,
            summary=response.content,
            ingestion_method=document.source_type,
            metadata={
                "description": document.description or "",
                "status_code": str(document.status_code or ""),
                "link_count": str(len(document.links)),
            },
        )

    def _build_summary_messages(self, document: WebDocument) -> list[ChatMessage]:
        title = document.title or "Untitled page"
        description = document.description or "No meta description found."
        content = document.text[:12_000]
        return [
            ChatMessage(
                role="system",
                content=(
                    "You are a careful research assistant. Summarize only facts present "
                    "in the extracted page content. Ignore navigation, cookie notices, "
                    "ads, and boilerplate. Do not invent facts."
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    "Produce a readable Markdown summary of this web page.\n\n"
                    "Include:\n"
                    "- the main purpose of the page\n"
                    "- important topics, products, or services\n"
                    "- relevant announcements or notable facts\n\n"
                    f"URL: {document.final_url}\n"
                    f"Title: {title}\n"
                    f"Meta description: {description}\n\n"
                    "Extracted page text:\n"
                    f"{content}"
                ),
            ),
        ]
