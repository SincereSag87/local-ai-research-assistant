# LocalAI Research Assistant

LocalAI Research Assistant is a local-first AI engineering portfolio project for ingesting web content, extracting research-ready text, producing structured research outputs, and comparing local model behavior. It uses Ollama through an OpenAI-compatible interface, so research and evaluation logic stay model-independent.

This is an original portfolio project designed to demonstrate practical AI engineering patterns with privacy-conscious local inference.

## Why Local-First AI

Local-first AI keeps prompts, extracted page text, generated research outputs, and comparison results on your machine. That improves privacy, reduces dependency on hosted model services, and makes research workflows easier to run repeatedly without per-request API costs.

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
- Model comparison across local Ollama models
- Lightweight deterministic evaluation metrics
- Text and JSON comparison output
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
ResearchEngine
  |
  |-- llama3.2
  |-- gemma3
  |
  v
ModelComparator
  |
  v
Evaluation Metrics
  |
  v
ModelComparisonResult
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
  evaluation/
    models.py              # Comparison and metric result models
    metrics.py             # Deterministic task-specific checks
    comparator.py          # Multi-model comparison runner
    formatter.py           # Text and JSON comparison formatting
  services/
    research_service.py    # URL ingestion plus research/evaluation orchestration
  main.py                  # CLI entry point
```

## Website Ingestion Strategy

The ingestor tries static scraping first because it is faster, has lower overhead, and does not require launching a browser. If the static result is too short or looks like a JavaScript-required placeholder, the ingestor falls back to Playwright.

## Research Engine

The research engine consumes `WebDocument` objects rather than raw strings. It builds task-specific prompts, calls any `LLMProvider`, parses JSON responses, and validates them with Pydantic models.

Supported outputs:

- `ResearchSummary`
- `KeyFact`
- `QuestionAnswer`
- `ResearchReport`

The prompts are provider-independent, so the same research task can run against `llama3.2`, `gemma3`, or future models without changing research logic.

## Model Comparison

Phase 4 adds side-by-side comparison for the same research task over the same ingested `WebDocument`. The website is not refetched for each model. Only model generation and structured parsing are repeated per model.

Comparison supports:

- summaries
- key facts
- topics
- grounded question answering
- research reports

The comparator records per-model success or failure and continues running remaining models if one model fails.

## Evaluation Metrics

Evaluation is deterministic and intentionally lightweight. It is useful for portfolio demos and regression checks, but it is not a replacement for human review or a judge-model evaluation system.

Supported checks include:

- model-call latency in milliseconds
- response character count and word count
- structured output validity
- required field completeness
- fact evidence presence
- grounded Q&A behavior
- explicit insufficient-information behavior
- task success or failure

The CLI reports fastest model and valid models, but it does not declare a best model based only on speed.

## Source Grounding

Research prompts instruct the model to use only extracted webpage content, avoid inventing facts, ignore boilerplate, and explicitly say when information is not present.

For question answering, the expected unknown-answer text is:

```text
The provided page does not contain enough information to answer this question.
```

Answers and facts include evidence snippets when practical.

## Context Limit

The project uses a simple deterministic context strategy rather than full RAG. Extracted page text is capped by `MAX_CONTEXT_CHARS`. If content is too large, the engine preserves the beginning and end of the page text with a clear truncation marker in the middle.

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

Pull the primary local models:

```powershell
ollama pull llama3.2
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

Run a single-model research task:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task summary
uv run python -m app.main --url https://edwarddonner.com --task facts
uv run python -m app.main --url https://edwarddonner.com --task topics
uv run python -m app.main --url https://edwarddonner.com --task report
uv run python -m app.main --url https://edwarddonner.com --task ask --question "What does this person do?"
```

Compare `llama3.2` and `gemma3`:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task summary --compare llama3.2 gemma3
uv run python -m app.main --url https://edwarddonner.com --task facts --compare llama3.2 gemma3
uv run python -m app.main --url https://edwarddonner.com --task report --compare llama3.2 gemma3
uv run python -m app.main --url https://edwarddonner.com --task ask --question "What does this person do?" --compare llama3.2 gemma3
```

Emit comparison JSON:

```powershell
uv run python -m app.main --url https://edwarddonner.com --task summary --compare llama3.2 gemma3 --output json
```

Sample comparison output:

```text
Task: summary
Source: https://edwarddonner.com/
Ingestion: static

Model: llama3.2
Latency: 2,814 ms
Structured output: valid
Task success: PASS
Response length: 620 chars
Completeness: PASS
Grounding: PASS

Model: gemma3
Latency: 4,102 ms
Structured output: valid
Task success: PASS
Response length: 715 chars
Completeness: PASS
Grounding: PASS

Comparison
Fastest: llama3.2
Valid models: llama3.2, gemma3
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

The deterministic evaluation checks are basic quality signals. They can identify parse failures, missing fields, missing evidence, latency differences, and obvious incomplete outputs, but they do not prove factual correctness or overall answer quality.

## Roadmap

1. Core local LLM layer ✅
2. Website ingestion ✅
3. Research engine ✅
4. Model comparison & evaluation ✅
5. FastAPI backend
6. Gradio UI
7. Advanced evaluation/logging
8. Portfolio polish
