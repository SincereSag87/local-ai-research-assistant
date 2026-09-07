# LocalAI Research Assistant

LocalAI Research Assistant is a local-first AI engineering portfolio project for ingesting web content, extracting research-ready text, producing structured research outputs, comparing local model behavior, and exposing those capabilities through a FastAPI backend.

It uses Ollama through an OpenAI-compatible interface, so research, evaluation, CLI, and API layers stay model-independent.

## Why Local-First AI

Local-first AI keeps prompts, extracted page text, generated research outputs, and comparison results on your machine. That improves privacy, reduces dependency on hosted model services, and makes research workflows easier to run repeatedly without per-request API costs.

Ollama provides local model hosting and an OpenAI-compatible API, which lets this project use the OpenAI Python client while targeting `http://localhost:11434/v1`.

## Current Features

- Python 3.12+ project managed with `uv`
- Pydantic settings loaded from environment variables or an optional local `.env`
- OpenAI Python client configured for local Ollama
- Reusable `LLMProvider` abstraction
- Static website ingestion with BeautifulSoup and Playwright fallback
- Structured research engine for summaries, facts, topics, Q&A, and reports
- Model comparison across local Ollama models
- Lightweight deterministic evaluation metrics
- FastAPI backend with Swagger/OpenAPI
- Centralized API error responses
- Configurable local-development CORS
- CLI and API entry points over the same service layer
- Offline unit tests with mocked HTTP, browser, LLM, and API services

## Architecture

```text
HTTP Client / CLI
      |
      v
FastAPI Routes / CLI Commands
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
  api/
    app.py                 # FastAPI application factory and route registration
    dependencies.py        # Reusable provider/service/readiness dependencies
    errors.py              # Centralized domain exception mapping
    models.py              # API request and health response models
    routes/
      health.py
      research.py
      comparison.py
  core/
    config.py
  ingestion/
  llm/
  research/
  evaluation/
  services/
    research_service.py
  main.py
```

Routes stay thin. Domain behavior remains in the existing ingestion, research, evaluation, LLM, and service modules.

## API Overview

Start the API:

```powershell
uv run uvicorn app.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | API health check |
| `GET` | `/health/ollama` | Ollama readiness check |
| `POST` | `/research/generate` | Direct local model generation |
| `POST` | `/research/summary` | Summarize a webpage |
| `POST` | `/research/facts` | Extract grounded key facts |
| `POST` | `/research/topics` | Extract topics |
| `POST` | `/research/report` | Generate a structured research report |
| `POST` | `/research/ask` | Ask a grounded question about a webpage |
| `POST` | `/compare` | Compare models on one research task |

## PowerShell Examples

Health:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/health
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/health/ollama
```

Direct generation:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/research/generate `
  -ContentType "application/json" `
  -Body '{"prompt":"Explain local LLMs in three sentences.","model":"llama3.2"}'
```

Summarize a URL:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/research/summary `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","model":"llama3.2"}'
```

Extract facts with Gemma:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/research/facts `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","model":"gemma3"}'
```

Ask a grounded question:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/research/ask `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","question":"What does this person do?","model":"llama3.2"}'
```

Compare models:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/compare `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","task":"summary","models":["llama3.2","gemma3"]}'
```

Compare a grounded question:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/compare `
  -ContentType "application/json" `
  -Body '{"url":"https://edwarddonner.com","task":"ask","models":["llama3.2","gemma3"],"question":"What does this person do?"}'
```

## Example Responses

Health:

```json
{
  "status": "ok",
  "service": "local-ai-research-assistant"
}
```

Ollama readiness:

```json
{
  "status": "ok",
  "service": "ollama",
  "base_url": "http://localhost:11434/v1",
  "default_model": "llama3.2",
  "reachable": true
}
```

Error response:

```json
{
  "error": {
    "code": "OLLAMA_UNAVAILABLE",
    "message": "The local Ollama service is unavailable."
  }
}
```

## Model Comparison And Evaluation

The comparison API ingests the URL once, then runs the same research task against each requested local model. It records latency with a monotonic clock around model generation only, excluding website ingestion time.

Deterministic metrics include structured-output validity, response length, required field completeness, fact evidence presence, grounded Q&A behavior, insufficient-information behavior, and task success or failure.

These checks are transparent quality signals. They are not equivalent to human evaluation or a judge-model framework.

## Source Grounding

Research prompts instruct the model to use only extracted webpage content, avoid inventing facts, ignore boilerplate, and explicitly say when information is not present.

For question answering, the expected unknown-answer text is:

```text
The provided page does not contain enough information to answer this question.
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
```

No OpenAI API key is required.

CORS defaults are scoped to common local UI development origins for the planned Gradio phase. The API does not default to unrestricted `*`.

## Blocking And Concurrency

Phase 5 uses synchronous route functions because the current ingestion, Playwright, and local model calls are blocking. This keeps behavior honest and avoids wrapping the existing stack in fake async code. Higher-throughput concurrency, queues, and background jobs belong in a later phase.

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

## CLI

The existing CLI still works:

```powershell
uv run python -m app.main
uv run python -m app.main --url https://edwarddonner.com --task summary
uv run python -m app.main --url https://edwarddonner.com --task facts --model gemma3
uv run python -m app.main --url https://edwarddonner.com --task summary --compare llama3.2 gemma3
```

## Test And Lint

```powershell
uv run pytest
uv run ruff check .
```

The normal tests do not require live websites, Ollama, or a real browser session. Live API smoke tests should be run manually after starting Uvicorn.

## Limitations

This scraper does not attempt to defeat anti-bot systems, authentication, paywalls, or sites that intentionally block automation. Some dynamic applications may still require site-specific extraction logic even with Playwright rendering.

The current context strategy truncates long pages without semantic retrieval. Very long pages may lose details from the middle of the document until a later retrieval phase is added.

The deterministic evaluation checks are basic quality signals. They can identify parse failures, missing fields, missing evidence, latency differences, and obvious incomplete outputs, but they do not prove factual correctness or overall answer quality.

## Roadmap

1. Core local LLM layer ✅
2. Website ingestion ✅
3. Research engine ✅
4. Model comparison & evaluation ✅
5. FastAPI backend ✅
6. Gradio UI
7. Advanced evaluation/logging
8. Portfolio polish
