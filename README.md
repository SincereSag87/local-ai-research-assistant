# LocalAI Research Assistant

LocalAI Research Assistant is a local-first AI engineering portfolio project for ingesting web content, extracting research-ready text, and producing structured research outputs with locally hosted language models. It uses Ollama through an OpenAI-compatible interface, so the research engine stays model-independent and does not require hosted API keys.

This is an original portfolio project designed to demonstrate practical AI engineering patterns with privacy-conscious local inference.

## Why Local-First AI

Local-first AI keeps prompts, extracted page text, and generated research outputs on your machine. That improves privacy, reduces dependency on external model services, and makes research workflows easier to run repeatedly without per-request API costs.

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
- Research engine for summaries, key facts, topics, question answering, and reports
- Structured Pydantic research outputs
- Grounded prompts that require answers to use only extracted page content
- CLI modes for direct prompts and URL research tasks
- Offline unit tests with mocked HTTP, browser, and LLM dependencies
- Ruff linting

## Architecture

```text
URL
  |
  v
WebIngestor
  |
  v
WebDocument
  |
  v
Research Engine
  |-- Summary
  |-- Key Facts
  |-- Topics
  |-- Question Answering
  |-- Research Report
  |
  v
LLMProvider
  |
  v
Structured Result
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
  research/
    models.py              # Structured research output models
    prompts.py             # Model-independent prompt builders
    parsers.py             # JSON parsing and Pydantic validation
    engine.py              # Research task orchestration over WebDocument
  services/
    research_service.py    # URL ingestion plus research engine orchestration
  main.py                  # CLI entry point
```

## Website Ingestion Strategy

The ingestor tries static scraping first because it is faster, has lower overhead, and does not require launching a browser. Static scraping handles many content pages, blogs, docs, marketing pages, and simple websites well.

If the static result is too short or looks like a JavaScript-required placeholder, the ingestor falls back to Playwright. The fallback uses headless Chromium to render the page, then sends the rendered HTML through the same normalization path as the static scraper.

The current usability heuristic checks minimum extracted text length, obvious JavaScript-required messages, and placeholder loading content.

## Research Engine

The research engine consumes `WebDocument` objects rather than raw strings. It builds task-specific prompts, calls any `LLMProvider`, parses JSON responses, and validates them with Pydantic models.

Supported outputs:

- `ResearchSummary`
- `KeyFact`
- `QuestionAnswer`
- `ResearchReport`

The prompts are provider-independent and are kept separate from orchestration logic. That makes the same research task runnable against `llama3.2`, `gemma3`, or future models without changing the research flow.

## Source Grounding

Research prompts instruct the model to use only the extracted webpage content, avoid inventing facts, ignore boilerplate, and explicitly say when information is not present.

For question answering, the expected unknown-answer text is:

```text
The provided page does not contain enough information to answer this question.
```

Answers and facts include evidence snippets when practical.

## Context Limit

Phase 3 uses a simple deterministic context strategy rather than full RAG. Extracted page text is capped by `MAX_CONTEXT_CHARS`. If content is too large, the engine preserves the beginning and end of the page text with a clear truncation marker in the middle.

Embeddings, vector databases, and chunk retrieval are intentionally left for later phases.

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
MAX_CONTEXT_CHARS=12000
```

No OpenAI API key is required.

## Run

Run the original direct prompt smoke test:

```powershell
uv run python -m app.main
```

Use a different model:

```powershell
uv run python -m app.main --model gemma3
```

Summarize a URL:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task summary
```

Extract key facts:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task facts
```

Extract topics:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task topics
```

Ask a grounded question:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task ask --question "What is Edward Donner's professional background?"
```

Generate a Markdown-style report:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task report
```

Run any URL task with another installed model:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task facts --model gemma3
```

## Test And Lint

```powershell
uv run pytest
uv run ruff check .
```

The normal unit tests do not require live websites, Ollama, or a real browser session. Live smoke tests should be run manually through the CLI.

## Limitations

This scraper does not attempt to defeat anti-bot systems, authentication, paywalls, or sites that intentionally block automation. Some dynamic applications may still require site-specific extraction logic even with Playwright rendering.

The current context strategy truncates long pages without semantic retrieval. Very long pages may lose details from the middle of the document until a later retrieval phase is added.

The ingestion layer is designed for useful research extraction, not perfect archival reproduction of every page element.

## Roadmap

1. Core local LLM layer ✅
2. Website ingestion ✅
3. Research engine ✅
4. Model comparison
5. FastAPI backend
6. Gradio UI
7. Evaluation, testing, and logging
8. Portfolio polish
