from app.core.config import Settings, get_settings
from app.ingestion.base import BrowserScraperError, IngestionError, Scraper, StaticScraperError
from app.ingestion.browser_scraper import BrowserScraper
from app.ingestion.models import WebDocument
from app.ingestion.static_scraper import StaticScraper

JS_REQUIRED_PATTERNS = [
    "enable javascript",
    "javascript is required",
    "requires javascript",
    "please enable js",
    "you need to enable javascript",
]
PLACEHOLDER_PATTERNS = [
    "loading...",
    "loading",
    "please wait",
]


class WebIngestor:
    """Static-first website ingestor with browser fallback.

    A static document is considered usable when it has enough normalized text and does not look
    like a JavaScript-required placeholder page. This keeps the common path fast and lightweight
    while preserving a fallback for rendered sites.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        static_scraper: Scraper | None = None,
        browser_scraper: Scraper | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.static_scraper = static_scraper or StaticScraper(settings=self.settings)
        self.browser_scraper = browser_scraper or BrowserScraper(settings=self.settings)

    def ingest(self, url: str) -> WebDocument:
        static_error: StaticScraperError | None = None
        try:
            document = self.static_scraper.scrape(url)
            if self.is_usable(document):
                return document
        except StaticScraperError as exc:
            static_error = exc

        try:
            return self.browser_scraper.scrape(url)
        except BrowserScraperError as exc:
            if static_error:
                raise IngestionError(
                    "Static and browser ingestion both failed. "
                    f"Static: {static_error} Browser: {exc}"
                ) from exc
            raise IngestionError(
                f"Browser fallback failed after unusable static content: {exc}"
            ) from exc

    def is_usable(self, document: WebDocument) -> bool:
        text = document.text.strip()
        if len(text) < self.settings.min_content_length:
            return False

        lowered = text.lower()
        if any(pattern in lowered for pattern in JS_REQUIRED_PATTERNS):
            return False

        if any(lowered == pattern for pattern in PLACEHOLDER_PATTERNS):
            return False

        return True
