import re
from collections.abc import Iterable
from urllib.parse import urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from app.core.config import Settings, get_settings
from app.ingestion.base import Scraper, StaticScraperError
from app.ingestion.models import Link, SourceType, WebDocument

DEFAULT_USER_AGENT = (
    "LocalAIResearchAssistant/0.2 "
    "(portfolio project; static-first research content extraction)"
)
IRRELEVANT_SELECTORS = [
    "script",
    "style",
    "noscript",
    "svg",
    "form",
    "iframe",
    "canvas",
    "template",
]
TEXT_SELECTORS = ["main", "article", "[role='main']", "body"]
SKIPPED_LINK_SCHEMES = {"mailto", "tel", "javascript", "data"}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_web_document_from_html(
    *,
    html: str,
    url: str,
    final_url: str,
    source_type: SourceType,
    status_code: int | None = None,
) -> WebDocument:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select(",".join(IRRELEVANT_SELECTORS)):
        element.decompose()

    title = normalize_whitespace(soup.title.get_text()) if soup.title else None
    description = _extract_description(soup)
    metadata = _extract_metadata(soup)
    text = _extract_readable_text(soup)
    links = _extract_links(soup.find_all("a"), final_url)

    return WebDocument(
        url=url,
        final_url=final_url,
        title=title or None,
        text=text,
        links=links,
        description=description,
        metadata=metadata,
        source_type=source_type,
        status_code=status_code,
    )


class StaticScraper(Scraper):
    """Lightweight requests and BeautifulSoup scraper for static HTML pages."""

    def __init__(
        self,
        settings: Settings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session = session or requests.Session()

    def scrape(self, url: str) -> WebDocument:
        try:
            response = self.session.get(
                url,
                headers={"User-Agent": DEFAULT_USER_AGENT},
                timeout=self.settings.http_timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise StaticScraperError(f"Static scrape failed with HTTP status {status}.") from exc
        except requests.RequestException as exc:
            raise StaticScraperError(f"Static scrape failed for {url}: {exc}") from exc

        content_type = response.headers.get("content-type", "")
        if content_type and "html" not in content_type.lower():
            raise StaticScraperError(f"Static scrape expected HTML, received '{content_type}'.")

        return extract_web_document_from_html(
            html=response.text,
            url=url,
            final_url=response.url,
            source_type="static",
            status_code=response.status_code,
        )


def _extract_description(soup: BeautifulSoup) -> str | None:
    candidates = [
        soup.find("meta", attrs={"name": "description"}),
        soup.find("meta", attrs={"property": "og:description"}),
    ]
    for candidate in candidates:
        if not isinstance(candidate, Tag):
            continue
        content = candidate.get("content")
        if isinstance(content, str) and normalize_whitespace(content):
            return normalize_whitespace(content)
    return None


def _extract_metadata(soup: BeautifulSoup) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for meta in soup.find_all("meta"):
        if not isinstance(meta, Tag):
            continue
        key = meta.get("name") or meta.get("property")
        value = meta.get("content")
        if isinstance(key, str) and isinstance(value, str):
            clean_key = normalize_whitespace(key)
            clean_value = normalize_whitespace(value)
            if clean_key and clean_value:
                metadata[clean_key] = clean_value
    return metadata


def _extract_readable_text(soup: BeautifulSoup) -> str:
    for selector in TEXT_SELECTORS:
        container = soup.select_one(selector)
        if container:
            text = normalize_whitespace(container.get_text(" ", strip=True))
            if text:
                return text
    return normalize_whitespace(soup.get_text(" ", strip=True))


def _extract_links(anchors: Iterable[Tag], base_url: str) -> list[Link]:
    links: list[Link] = []
    seen: set[str] = set()

    for anchor in anchors:
        href = anchor.get("href")
        if not isinstance(href, str):
            continue

        absolute_url = _normalize_link(href, base_url)
        if absolute_url is None or absolute_url in seen:
            continue

        link_text = normalize_whitespace(anchor.get_text(" ", strip=True))
        seen.add(absolute_url)
        links.append(Link(text=link_text, url=absolute_url))

    return links


def _normalize_link(href: str, base_url: str) -> str | None:
    href = href.strip()
    if not href or href.startswith("#"):
        return None

    absolute_url = urljoin(base_url, href)
    absolute_url, fragment = urldefrag(absolute_url)
    parsed = urlparse(absolute_url)

    if fragment or parsed.scheme in SKIPPED_LINK_SCHEMES:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None

    return absolute_url
