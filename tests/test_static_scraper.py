from types import SimpleNamespace

import pytest
import requests

from app.core.config import Settings
from app.ingestion import StaticScraper, StaticScraperError

HTML = """
<!doctype html>
<html>
  <head>
    <title> Test Page </title>
    <meta name="description" content="A useful test page.">
    <meta property="og:type" content="article">
    <style>.hidden { display: none; }</style>
    <script>window.app = true;</script>
  </head>
  <body>
    <nav>Navigation links</nav>
    <main>
      <h1>Research Topic</h1>
      <p>This page explains useful research content.</p>
      <form><input value="ignore me"></form>
      <a href="/about">About</a>
      <a href="/about">Duplicate About</a>
      <a href="https://example.com/report#section">Report Fragment</a>
      <a href="mailto:test@example.com">Email</a>
      <a href="javascript:void(0)">Script</a>
    </main>
  </body>
</html>
"""


class FakeResponse:
    def __init__(
        self,
        text: str = HTML,
        url: str = "https://example.com/final",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.text = text
        self.url = url
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError("bad status")
            error.response = self
            raise error


class FakeSession:
    def __init__(
        self,
        response: FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response or FakeResponse()
        self.error = error
        self.last_request = None

    def get(self, *args, **kwargs):
        self.last_request = SimpleNamespace(args=args, kwargs=kwargs)
        if self.error:
            raise self.error
        return self.response


def make_settings() -> Settings:
    return Settings(http_timeout=3, browser_timeout=1000, min_content_length=50)


def test_static_scraper_extracts_title_text_metadata_and_links():
    session = FakeSession()
    scraper = StaticScraper(settings=make_settings(), session=session)

    document = scraper.scrape("https://example.com/page")

    assert document.title == "Test Page"
    assert document.description == "A useful test page."
    assert document.metadata["og:type"] == "article"
    assert "window.app" not in document.text
    assert "ignore me" not in document.text
    assert "Research Topic" in document.text
    assert str(document.final_url) == "https://example.com/final"
    assert document.status_code == 200
    assert document.source_type == "static"
    assert [str(link.url) for link in document.links] == ["https://example.com/about"]
    assert session.last_request.kwargs["allow_redirects"] is True
    assert session.last_request.kwargs["timeout"] == 3
    assert "User-Agent" in session.last_request.kwargs["headers"]


def test_static_scraper_rejects_http_errors():
    session = FakeSession(response=FakeResponse(status_code=404))
    scraper = StaticScraper(settings=make_settings(), session=session)

    with pytest.raises(StaticScraperError, match="HTTP status 404"):
        scraper.scrape("https://example.com/missing")


def test_static_scraper_rejects_non_html_content():
    response = FakeResponse(headers={"content-type": "application/pdf"})
    scraper = StaticScraper(settings=make_settings(), session=FakeSession(response=response))

    with pytest.raises(StaticScraperError, match="expected HTML"):
        scraper.scrape("https://example.com/file.pdf")


def test_static_scraper_wraps_request_errors():
    scraper = StaticScraper(
        settings=make_settings(),
        session=FakeSession(error=requests.ConnectionError("network down")),
    )

    with pytest.raises(StaticScraperError, match="network down"):
        scraper.scrape("https://example.com")
