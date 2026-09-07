import pytest

from app.core.config import Settings
from app.ingestion import (
    BrowserScraperError,
    IngestionError,
    StaticScraperError,
    WebDocument,
    WebIngestor,
)


class FakeScraper:
    def __init__(self, document: WebDocument | None = None, error: Exception | None = None) -> None:
        self.document = document
        self.error = error
        self.calls = 0

    def scrape(self, url: str) -> WebDocument:
        self.calls += 1
        if self.error:
            raise self.error
        if self.document is None:
            raise AssertionError("FakeScraper needs a document or error")
        return self.document


def make_settings() -> Settings:
    return Settings(min_content_length=20)


def make_document(text: str, source_type: str = "static") -> WebDocument:
    return WebDocument(
        url="https://example.com",
        final_url="https://example.com",
        title="Example",
        text=text,
        links=[],
        source_type=source_type,
        status_code=200,
    )


def test_ingestor_returns_usable_static_document_without_browser():
    static = FakeScraper(document=make_document("This is enough useful page content."))
    browser = FakeScraper(document=make_document("browser", source_type="browser"))
    ingestor = WebIngestor(settings=make_settings(), static_scraper=static, browser_scraper=browser)

    document = ingestor.ingest("https://example.com")

    assert document.source_type == "static"
    assert static.calls == 1
    assert browser.calls == 0


def test_ingestor_falls_back_when_static_content_is_too_short():
    static = FakeScraper(document=make_document("short"))
    browser = FakeScraper(document=make_document("Rendered content is long enough.", "browser"))
    ingestor = WebIngestor(settings=make_settings(), static_scraper=static, browser_scraper=browser)

    document = ingestor.ingest("https://example.com")

    assert document.source_type == "browser"
    assert browser.calls == 1


def test_ingestor_falls_back_when_static_scraper_fails():
    static = FakeScraper(error=StaticScraperError("static failed"))
    browser = FakeScraper(document=make_document("Rendered content is long enough.", "browser"))
    ingestor = WebIngestor(settings=make_settings(), static_scraper=static, browser_scraper=browser)

    document = ingestor.ingest("https://example.com")

    assert document.source_type == "browser"


def test_ingestor_raises_when_both_scrapers_fail():
    static = FakeScraper(error=StaticScraperError("static failed"))
    browser = FakeScraper(error=BrowserScraperError("browser failed"))
    ingestor = WebIngestor(settings=make_settings(), static_scraper=static, browser_scraper=browser)

    with pytest.raises(IngestionError, match="both failed"):
        ingestor.ingest("https://example.com")


def test_ingestor_treats_javascript_placeholder_as_unusable():
    static = FakeScraper(
        document=make_document("JavaScript is required. Please enable JavaScript in your browser.")
    )
    browser = FakeScraper(document=make_document("Rendered content is long enough.", "browser"))
    ingestor = WebIngestor(settings=make_settings(), static_scraper=static, browser_scraper=browser)

    document = ingestor.ingest("https://example.com")

    assert document.source_type == "browser"
