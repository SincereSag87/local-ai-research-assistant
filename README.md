# LocalAI Research Assistant

LocalAI Research Assistant is a local-first AI engineering portfolio project for ingesting web content, producing structured research outputs, comparing local model behavior, exposing a FastAPI backend, and providing a polished Gradio web UI.

It uses Ollama through an OpenAI-compatible interface, so research, evaluation, API, CLI, and UI layers stay model-independent.

## Quick Start

Terminal 1, start the FastAPI backend:

```powershell
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Terminal 2, start the Gradio UI:

```powershell
uv run python -m ui.app
```

Open:

```text
http://127.0.0.1:7860
```

## Why Local-First AI

Local-first AI keeps prompts, extracted page text, generated research outputs, metrics, and comparison results on your machine. That improves privacy, reduces dependency on hosted model services, and makes research workflows easier to run repeatedly without per-request API costs.

Ollama provides local model hosting and an OpenAI-compatible API, which lets this project use the OpenAI Python client while targeting `http://localhost:11434/v1`.

## Current Features

- Python 3.12+ project managed with `uv`
- Pydantic settings loaded from environment variables or an optional local `.env`
- OpenAI Python client configured for local Ollama
- Static website ingestion with BeautifulSoup and Playwright fallback
- Structured research engine for summaries, facts, topics, Q&A, and reports
- Model comparison across local Ollama models
- Deterministic evaluation checks for parsing, completeness, grounding, and latency
- FastAPI backend with Swagger/OpenAPI
- Gradio Blocks UI for interactive demos
- Health panel for API and Ollama readiness
- System observability tab backed by `/metrics`
- Structured logging with request IDs
- Local benchmark runner for comparing tasks across models
- Centralized API client and UI error handling
- CLI, API, and UI entry points over the same service stack

## Architecture

```text
Gradio UI
   |
   v
FastAPI Backend
   |
   |-- Observability Middleware --> Request IDs, Logs, Metrics
   |
   v
ResearchService
   |
   |-- WebIngestor --> WebDocument
   |-- ResearchEngine --> LLMProvider --> Ollama
   |-- ModelComparator --> Evaluation Metrics
   |
   v
Structured JSON Results
```

```text
app/
  api/                   # FastAPI backend, middleware, routes, error mapping
  ingestion/             # Static scraper and Playwright fallback
  llm/                   # LLM provider abstraction and Ollama provider
  research/              # Prompt builders, parsers, and research engine
  evaluation/            # Model comparison, metrics, formatter, benchmark runner
  observability/         # Logging, request IDs, timers, local metrics store
  services/              # Orchestration layer shared by API and CLI

ui/
  app.py                 # Gradio Blocks application
  api_client.py          # Reusable HTTP client for the FastAPI backend
  components.py          # UI callbacks and component-level helpers
  formatters.py          # Markdown/table/chart formatting helpers
```

## Observability

Phase 7 adds local-first observability without introducing an external monitoring platform.

The backend records:

- total request count
- successful and failed requests
- average request latency
- task counts
- selected model counts
- average model latency by model
- scraper/ingestion method counts
- parsing failure count
- comparison run count
- unknown-answer response count
- error category counts

Every API request receives an `X-Request-ID` response header. If the client sends a safe `X-Request-ID`, the backend reuses it; otherwise it generates a UUID4 request ID. The request ID is also included in structured logs.

Metrics endpoint:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/metrics
```

Sample metrics shape:

```json
{
  "requests": {
    "total": 25,
    "successful": 23,
    "failed": 2,
    "average_latency_ms": 1520.4
  },
  "models": {
    "llama3.2": {
      "requests": 15,
      "average_latency_ms": 18000
    }
  },
  "tasks": {
    "summary": 8,
    "facts": 5,
    "ask": 7
  },
  "ingestion": {
    "static": 22,
    "browser": 3
  },
  "errors": {},
  "parsing_failures": 0,
  "comparison_runs": 4,
  "unknown_answer_responses": 2
}
```

The tracing is intentionally lightweight. It uses local timers around request handling, ingestion, model calls, parsing/evaluation, and completion. This is not distributed tracing.

## Structured Logging

Logging uses Python's standard `logging` module. The default format is JSON-like records to stdout.

Configurable settings:

```text
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=
```

If `LOG_FILE` is set, logs should be written to an ignored runtime directory such as `logs/`.

The system avoids logging:

- scraped page bodies
- full prompts
- full environment variables
- API keys or secrets
- generated benchmark output files

URLs are logged because they are useful for this portfolio project. In a real production system, URL logging should be reviewed against privacy and data-handling policy.

Tracked error categories include:

- `ingestion_error`
- `ollama_unavailable`
- `model_not_found`
- `parse_error`
- `validation_error`
- `llm_error`
- `internal_error`
- `model_run_error`

## Benchmark Runner

The benchmark runner executes comparison cases across local models and reports deterministic aggregate signals. It does not claim statistical significance or replace human review.

Run the included sample:

```powershell
uv run python -m app.evaluation.benchmark --config benchmarks/sample.json
```

JSON output:

```powershell
uv run python -m app.evaluation.benchmark --config benchmarks/sample.json --output json
```

Each benchmark run records:

- model
- task
- success/failure
- structured parse validity
- grounding check
- completeness check
- latency
- response size
- error if present

Aggregate output includes success rate, parse rate, grounding rate, and average latency by model. Generated benchmark reports should be written to ignored runtime folders if file output is added later.

## Gradio UI

The UI includes:

- webpage URL input
- model selector for `llama3.2` and `gemma3`
- research task selector
- grounded question input for Ask
- Markdown-rendered research output
- model comparison tab
- latency metrics table
- latency bar chart
- backend/Ollama health status panel
- System / Observability tab with metrics tables and simple charts

The UI does not contain research or scraping logic. It calls the FastAPI endpoints over HTTP.

## API Backend

Start the API:

```powershell
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

Key endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | API health check |
| `GET` | `/health/ollama` | Ollama readiness check |
| `GET` | `/metrics` | Local application metrics |
| `POST` | `/research/generate` | Direct local model generation |
| `POST` | `/research/summary` | Summarize a webpage |
| `POST` | `/research/facts` | Extract grounded key facts |
| `POST` | `/research/topics` | Extract topics |
| `POST` | `/research/report` | Generate a structured research report |
| `POST` | `/research/ask` | Ask a grounded question about a webpage |
| `POST` | `/compare` | Compare models on one research task |

PowerShell API examples:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/health

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/research/summary `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","model":"llama3.2"}'

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/research/ask `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","question":"What does this person do?","model":"gemma3"}'

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/compare `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","task":"summary","models":["llama3.2","gemma3"]}'
```

## Configuration

Available settings:

```text
OLLAMA_BASE_URL=http://localhost:11434/v1
DEFAULT_MODEL=llama3.2
HTTP_TIMEOUT=15
BROWSER_TIMEOUT=20000
MIN_CONTENT_LENGTH=200
MAX_CONTEXT_CHARS=12000
API_HOST=127.0.0.1
API_PORT=8000
CORS_ORIGINS=http://localhost:7860,http://127.0.0.1:7860
API_BASE_URL=http://127.0.0.1:8000
GRADIO_HOST=127.0.0.1
GRADIO_PORT=7860
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=
```

No OpenAI API key is required.

The UI uses `API_BASE_URL` to call the backend. CORS defaults are scoped to common local UI development origins and do not use unrestricted `*`.

## Setup

Install dependencies:

```powershell
uv sync
```

Install Playwright's Chromium browser:

```powershell
uv run playwright install chromium
```

Pull the primary local models:

```powershell
ollama pull llama3.2
ollama pull gemma3
```

Copy `.env.example` to `.env` only if you want to override local defaults:

```powershell
Copy-Item .env.example .env
```

## CLI

The existing CLI still works:

```powershell
uv run python -m app.main
uv run python -m app.main --url https://edwarddonner.com --task summary
uv run python -m app.main --url https://edwarddonner.com --task facts --model gemma3
uv run python -m app.main --url https://edwarddonner.com --task summary --compare llama3.2 gemma3
```

## Screenshots

Screenshots are intentionally not committed yet. This section is reserved for portfolio polish after the UI stabilizes.

## Error Handling

The UI translates API errors into concise messages for unavailable backend, unavailable Ollama, missing models, invalid URLs, scraping failures, parsing failures, and request timeouts. Python stack traces are not shown in the interface.

API errors use a consistent JSON shape:

```json
{
  "error": {
    "code": "OLLAMA_UNAVAILABLE",
    "message": "The local Ollama service is unavailable."
  }
}
```

## Blocking And Concurrency

The FastAPI routes and Gradio callbacks call blocking ingestion, Playwright, and local model operations. This is acceptable for the local portfolio demo. Higher-throughput concurrency, queues, persistent metrics, and background jobs belong in later phases.

## Test And Lint

```powershell
uv run pytest
uv run ruff check .
```

The normal tests do not require live websites, Ollama, a real browser session, FastAPI running, or Gradio running. Live UI smoke tests should be run manually with the backend and UI servers running.

## Limitations

This scraper does not attempt to defeat anti-bot systems, authentication, paywalls, or sites that intentionally block automation. Some dynamic applications may still require site-specific extraction logic even with Playwright rendering.

The current context strategy truncates long pages without semantic retrieval. Very long pages may lose details from the middle of the document until a later retrieval phase is added.

The deterministic evaluation checks are basic quality signals. They can identify parse failures, missing fields, missing evidence, latency differences, and obvious incomplete outputs, but they do not prove factual correctness or overall answer quality.

Metrics are in-process and reset when the API process restarts. Persistent observability storage belongs in a later phase.

## Roadmap

1. Core local LLM layer [done]
2. Website ingestion [done]
3. Research engine [done]
4. Model comparison & evaluation [done]
5. FastAPI backend [done]
6. Gradio UI [done]
7. Observability & benchmarking [done]
8. Portfolio polish
