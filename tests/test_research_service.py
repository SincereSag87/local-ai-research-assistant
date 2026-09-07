from app.ingestion import WebDocument
from app.llm import ChatResponse
from app.services.research_service import ResearchService


class FakeProvider:
    def __init__(self):
        self.messages = None
        self.model = None

    def generate(self, messages, model=None):
        self.messages = messages
        self.model = model
        return ChatResponse(model=model or "llama3.2", content="## Summary\nUseful page summary.")


class FakeIngestor:
    def ingest(self, url: str) -> WebDocument:
        return WebDocument(
            url=url,
            final_url="https://example.com/final",
            title="Example Page",
            text="This page describes an example product and a notable announcement.",
            links=[],
            description="Example description",
            source_type="static",
            status_code=200,
        )


def test_research_service_summarizes_url_with_structured_result():
    provider = FakeProvider()
    service = ResearchService(llm_provider=provider, web_ingestor=FakeIngestor())

    result = service.summarize_url("https://example.com", model="gemma3")

    assert str(result.source_url) == "https://example.com/"
    assert str(result.final_url) == "https://example.com/final"
    assert result.title == "Example Page"
    assert result.model == "gemma3"
    assert result.ingestion_method == "static"
    assert "Useful page summary" in result.summary
    assert "do not invent facts" in provider.messages[0].content.lower()
    assert "notable announcement" in provider.messages[1].content
    assert provider.model == "gemma3"
