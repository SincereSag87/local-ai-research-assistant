"""Website ingestion components."""

from app.ingestion.base import BrowserScraperError, IngestionError, Scraper, StaticScraperError
from app.ingestion.browser_scraper import BrowserScraper
from app.ingestion.models import Link, SourceType, WebDocument
from app.ingestion.static_scraper import StaticScraper
from app.ingestion.web_ingestor import WebIngestor

__all__ = [
    "BrowserScraper",
    "BrowserScraperError",
    "IngestionError",
    "Link",
    "Scraper",
    "SourceType",
    "StaticScraper",
    "StaticScraperError",
    "WebDocument",
    "WebIngestor",
]
