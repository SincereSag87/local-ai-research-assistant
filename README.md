# LocalAI Research Assistant

LocalAI Research Assistant is a local-first AI engineering portfolio project for researching, summarizing, and comparing information with locally hosted language models. Phase 1 builds the foundation: configuration, a reusable LLM provider interface, an Ollama-backed provider, and a command-line smoke test.

This is an original portfolio project designed to demonstrate practical AI engineering patterns without depending on hosted model APIs.

## Why Local-First AI

Local-first AI keeps prompts and outputs on your machine, reduces dependency on external services, and makes model behavior easier to inspect. It is a strong fit for research workflows where privacy, repeatability, and cost control matter.

Ollama provides a simple way to run models locally while exposing an OpenAI-compatible API. This project uses that interface so the LLM layer can stay clean and provider-oriented.

## Architecture

```text
app/
  core/
    config.py              # Pydantic settings for local runtime configuration
  llm/
    base.py                # Provider interface and provider-level exceptions
    models.py              # Structured chat request/response types
    ollama_provider.py     # Ollama implementation using OpenAI-compatible API
  services/
    research_service.py    # Application service layer
  main.py                  # CLI smoke test
tests/
  test_ollama_provider.py  # Unit tests with mocked provider client
```

## Phase 1 Features

- Python 3.12+ project managed with `uv`
- Pydantic settings loaded from environment variables or an optional local `.env`
- OpenAI Python client configured for Ollama at `http://localhost:11434/v1`
- Reusable `LLMProvider` abstraction
- Ollama provider with model selection
- Default model: `llama3.2`
- Optional model override, including `gemma3`
- Structured chat message and response models
- Graceful errors for unavailable Ollama, missing models, connection failures, and malformed responses
- Unit tests that do not require a live Ollama server
- Ruff linting configuration

## Prerequisites

- Python 3.12 or newer
- `uv`
- Ollama running locally

Install `uv` from the official documentation:

```powershell
pipx install uv
```

Install Ollama from:

```text
https://ollama.com
```

Start Ollama and pull the default model:

```powershell
ollama pull llama3.2
```

To test Gemma as an alternate model:

```powershell
ollama pull gemma3
```

## Setup

Install dependencies and create the virtual environment:

```powershell
uv sync
```

Copy `.env.example` to `.env` only if you want to override local defaults:

```powershell
Copy-Item .env.example .env
```

Available settings:

```text
OLLAMA_BASE_URL=http://localhost:11434/v1
DEFAULT_MODEL=llama3.2
```

No OpenAI API key is required.

## Run

Run the CLI smoke test with the default model:

```powershell
uv run python -m app.main
```

Run with Gemma if `gemma3` is installed:

```powershell
uv run python -m app.main --model gemma3
```

Use a custom prompt:

```powershell
uv run python -m app.main --prompt "Explain retrieval augmented generation in three sentences."
```

## Test And Lint

```powershell
uv run pytest
uv run ruff check .
```

The unit tests mock the OpenAI-compatible client and do not require Ollama to be running.

## Roadmap

1. Core local LLM layer
2. Website ingestion with BeautifulSoup and Playwright
3. Research and summarization engine
4. Model comparison
5. FastAPI backend
6. Gradio UI
7. Evaluation, testing, and logging
8. Portfolio polish

