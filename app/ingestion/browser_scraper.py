from app.core.config import Settings, get_settings
from app.ingestion.base import BrowserScraperError, Scraper
from app.ingestion.models import WebDocument
from app.ingestion.static_scraper import DEFAULT_USER_AGENT, extract_web_document_from_html


class BrowserScraper(Scraper):
    """Playwright scraper for JavaScript-rendered pages."""

    def __init__(self, settings: Settings | None = None, headless: bool = True) -> None:
        self.settings = settings or get_settings()
        self.headless = headless

    def scrape(self, url: str) -> WebDocument:
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserScraperError(
                "Playwright is not installed. Run 'uv sync' and try again."
            ) from exc

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                try:
                    page = browser.new_page(
                        viewport={"width": 1365, "height": 900},
                        user_agent=DEFAULT_USER_AGENT,
                    )
                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=self.settings.browser_timeout,
                    )
                    try:
                        page.wait_for_load_state("networkidle", timeout=2_500)
                    except PlaywrightTimeoutError:
                        pass

                    status_code = response.status if response is not None else None
                    if status_code is not None and status_code >= 400:
                        raise BrowserScraperError(
                            f"Browser scrape failed with HTTP status {status_code}."
                        )

                    document = extract_web_document_from_html(
                        html=page.content(),
                        url=url,
                        final_url=page.url,
                        source_type="browser",
                        status_code=status_code,
                    )
                finally:
                    browser.close()
        except PlaywrightTimeoutError as exc:
            raise BrowserScraperError(f"Browser navigation timed out for {url}.") from exc
        except BrowserScraperError:
            raise
        except PlaywrightError as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "playwright install" in message:
                raise BrowserScraperError(
                    "Chromium is not installed for Playwright. "
                    "Run 'uv run playwright install chromium' and try again."
                ) from exc
            raise BrowserScraperError(f"Browser scrape failed for {url}.") from exc
        except Exception as exc:
            raise BrowserScraperError(f"Browser could not scrape {url}.") from exc

        if len(document.text) < self.settings.min_content_length:
            raise BrowserScraperError("Browser scrape did not find enough readable page content.")

        return document
