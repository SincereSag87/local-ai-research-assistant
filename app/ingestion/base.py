from abc import ABC, abstractmethod

from app.ingestion.models import WebDocument


class IngestionError(Exception):
    """Base exception for website ingestion failures."""


class StaticScraperError(IngestionError):
    """Raised when static HTTP scraping fails."""


class BrowserScraperError(IngestionError):
    """Raised when browser-based scraping fails."""


class Scraper(ABC):
    @abstractmethod
    def scrape(self, url: str) -> WebDocument:
        """Fetch a URL and return normalized research content."""
