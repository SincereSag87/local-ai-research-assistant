# LocalAI Research Assistant

LocalAI Research Assistant is a local-first AI engineering portfolio project for ingesting web content, extracting research-ready text, and summarizing it with locally hosted language models. It uses Ollama through an OpenAI-compatible interface so the core LLM layer stays provider-oriented without requiring hosted API keys.

This is an original portfolio project designed to demonstrate practical AI engineering patterns with privacy-conscious local inference.

## Why Local-First AI

Local-first AI keeps prompts, extracted page text, and generated summaries on your machine. That improves privacy, reduces dependency on external model services, and makes research workflows easier to run repeatedly without per-request API costs.

Ollama provides local model hosting and an OpenAI-compatible API, which lets this project use the OpenAI Python client while targeting `http://localhost:11434/v1`.

## Current Features

- Python 3.12+ project managed with `uv`
- Pydantic settings loaded from environment variables or an optional local `.env`
- OpenAI Python client configured for local Ollama
- Reusable `LLMProvider` abstraction
- Ollama provider with model selection
- Default model: `llama3.2`
- Optional model override, including `gemma3`
- Static website ingestion with `requests` and BeautifulSoup
- Browser fallback ingestion with Playwright and Chromium
- Shared `WebDocument` model for normalized web content
- URL summarization through `ResearchService`
- CLI modes for direct prompts and URL summaries
- Offline unit tests with mocked HTTP, browser, and LLM dependencies
- Ruff linting

## Architecture

```text
URL
  |
  v
Static Scraper
  |
  v
Content usable?
  |-- Yes --> Normalize content --> WebDocument
  |
  |-- No --> Playwright fallback --> Normalize content --> WebDocument
                                                    |
                                                    v
                                             ResearchService
                                                    |
                                                    v
                                             Ollama Provider
                                                    |
                                                    v
                                                 Summary
```

```text
app/
  core/
    config.py              # Pydantic settings for local runtime configuration
  ingestion/
    base.py                # Scraper interface and ingestion exceptions
    models.py              # WebDocument and Link models
    static_scraper.py      # requests + BeautifulSoup static scraper
    browser_scraper.py     # Playwright Chromium scraper
    web_ingestor.py        # Static-first fallback orchestration
  llm/
    base.py                # Provider interface and provider-level exceptions
    models.py              # Structured chat request/response types
    ollama_provider.py     # Ollama implementation using OpenAI-compatible API
  services/
    research_service.py    # Prompt and URL summarization service layer
  main.py                  # CLI entry point
tests/
  test_static_scraper.py
  test_browser_scraper.py
  test_web_ingestor.py
  test_research_service.py
  test_ollama_provider.py
```

## Website Ingestion Strategy

The ingestor tries static scraping first because it is faster, has lower overhead, and does not require launching a browser. Static scraping handles many content pages, blogs, docs, marketing pages, and simple websites well.

If the static result is too short or looks like a JavaScript-required placeholder, the ingestor falls back to Playwright. The fallback uses headless Chromium to render the page, then sends the rendered HTML through the same normalization path as the static scraper.

The current usability heuristic checks:

- minimum extracted text length
- obvious JavaScript-required messages
- placeholder-only content such as loading screens

## Prerequisites

- Python 3.12 or newer
- `uv`
- Ollama running locally
- Playwright Chromium for JavaScript-rendered pages

Install `uv`:

```powershell
pipx install uv
```

Install Ollama from:

```text
https://ollama.com
```

Pull the default model:

```powershell
ollama pull llama3.2
```

Optional alternate model:

```powershell
ollama pull gemma3
```

## Setup

Install Python dependencies:

```powershell
uv sync
```

Install Playwright's Chromium browser:

```powershell
uv run playwright install chromium
```

Copy `.env.example` to `.env` only if you want to override local defaults:

```powershell
Copy-Item .env.example .env
```

Available settings:

```text
OLLAMA_BASE_URL=http://localhost:11434/v1
DEFAULT_MODEL=llama3.2
HTTP_TIMEOUT=15
BROWSER_TIMEOUT=20000
MIN_CONTENT_LENGTH=200
```

No OpenAI API key is required.

## Run

Run the original Phase 1 prompt smoke test:

```powershell
uv run python -m app.main
```

Use a different model:

```powershell
uv run python -m app.main --model gemma3
```

Summarize a URL:

```powershell
uv run python -m app.main --url https://edwarddonner.com
```

Summarize a URL with Gemma:

```powershell
uv run python -m app.main --url https://openai.com --model gemma3
```

Use a custom direct prompt:

```powershell
uv run python -m app.main --prompt "Explain retrieval augmented generation in three sentences."
```

URL summary output includes:

```text
URL:
Title:
Ingestion method:
Model:
Summary:
```

## Test And Lint

```powershell
uv run pytest
uv run ruff check .
```

The normal unit tests do not require live websites, Ollama, or a real browser session. Live smoke tests should be run manually through the CLI.

## Limitations

This scraper does not attempt to defeat anti-bot systems, authentication, paywalls, or sites that intentionally block automation. Some dynamic applications may still require site-specific extraction logic even with Playwright rendering.

The ingestion layer is designed for useful research extraction, not perfect archival reproduction of every page element.

## Roadmap

1. Core local LLM layer
2. Website ingestion with BeautifulSoup and Playwright
3. Research and summarization engine
4. Model comparison
5. FastAPI backend
6. Gradio UI
7. Evaluation, testing, and logging
8. Portfolio polish

