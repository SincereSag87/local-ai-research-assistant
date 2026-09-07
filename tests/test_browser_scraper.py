import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.core.config import Settings
from app.ingestion import BrowserScraper, BrowserScraperError

RENDERED_HTML = """
<html>
  <head><title>Rendered Page</title></head>
  <body><main><h1>Rendered Content</h1><p>This content came from a browser render.</p></main></body>
</html>
"""


class FakePage:
    url = "https://example.com/rendered"

    def goto(self, *args, **kwargs):
        self.goto_args = args
        self.goto_kwargs = kwargs
        return SimpleNamespace(status=200)

    def wait_for_load_state(self, *args, **kwargs):
        self.wait_args = args
        self.wait_kwargs = kwargs

    def content(self):
        return RENDERED_HTML


class FakeBrowser:
    def __init__(self):
        self.page = FakePage()
        self.closed = False

    def new_page(self, **kwargs):
        self.new_page_kwargs = kwargs
        return self.page

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, browser):
        self.browser = browser
        self.launch_kwargs = None

    def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return self.browser


class FakeSyncPlaywright:
    def __init__(self, chromium):
        self.chromium = chromium

    def __enter__(self):
        return SimpleNamespace(chromium=self.chromium)

    def __exit__(self, *args):
        return None


def install_fake_playwright(monkeypatch, *, sync_playwright):
    module = ModuleType("playwright.sync_api")
    module.Error = RuntimeError
    module.TimeoutError = TimeoutError
    module.sync_playwright = sync_playwright
    package = ModuleType("playwright")
    package.sync_api = module
    monkeypatch.setitem(sys.modules, "playwright", package)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)


def make_settings() -> Settings:
    return Settings(browser_timeout=1234, min_content_length=20)


def test_browser_scraper_returns_rendered_document(monkeypatch):
    browser = FakeBrowser()
    chromium = FakeChromium(browser)
    install_fake_playwright(
        monkeypatch,
        sync_playwright=lambda: FakeSyncPlaywright(chromium),
    )

    document = BrowserScraper(settings=make_settings()).scrape("https://example.com")

    assert document.source_type == "browser"
    assert document.title == "Rendered Page"
    assert "Rendered Content" in document.text
    assert str(document.final_url) == "https://example.com/rendered"
    assert document.status_code == 200
    assert chromium.launch_kwargs == {"headless": True}
    assert browser.page.goto_kwargs["wait_until"] == "domcontentloaded"
    assert browser.page.goto_kwargs["timeout"] == 1234
    assert browser.closed is True


def test_browser_scraper_wraps_navigation_timeout(monkeypatch):
    def raise_timeout():
        raise TimeoutError("timed out")

    install_fake_playwright(monkeypatch, sync_playwright=raise_timeout)

    with pytest.raises(BrowserScraperError, match="timed out"):
        BrowserScraper(settings=make_settings()).scrape("https://example.com")


def test_browser_scraper_rejects_http_errors(monkeypatch):
    class ErrorPage(FakePage):
        def goto(self, *args, **kwargs):
            return SimpleNamespace(status=500)

    browser = FakeBrowser()
    browser.page = ErrorPage()
    chromium = FakeChromium(browser)
    install_fake_playwright(monkeypatch, sync_playwright=lambda: FakeSyncPlaywright(chromium))

    with pytest.raises(BrowserScraperError, match="HTTP status 500"):
        BrowserScraper(settings=make_settings()).scrape("https://example.com")
