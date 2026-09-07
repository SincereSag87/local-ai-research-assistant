# Portfolio Notes

## One-Sentence Description

Built a local-first AI research platform using Ollama, FastAPI, Gradio, Playwright, BeautifulSoup, and Pydantic to ingest webpages, run grounded research tasks, compare local models, and expose observability metrics.

## Resume Bullets

- Built a local-first AI research assistant with a provider-agnostic LLM layer, enabling the same research workflows to run against `llama3.2` and `gemma3` through Ollama's OpenAI-compatible API.
- Implemented static-first web ingestion with BeautifulSoup and Playwright fallback, producing normalized `WebDocument` objects for structured summaries, fact extraction, topic extraction, grounded Q&A, and research reports.
- Added FastAPI and Gradio interfaces plus deterministic evaluation, model latency comparison, request IDs, structured logging, local metrics, and benchmark tooling for an interview-ready AI engineering demo.

## 30-Second Interview Explanation

LocalAI Research Assistant is a local-first research system that takes a webpage URL, extracts usable content with a static scraper or Playwright fallback, and sends grounded prompts to local Ollama models. The research engine returns structured Pydantic-validated outputs for summaries, facts, topics, Q&A, and reports. I exposed the same core services through a CLI, FastAPI backend, and Gradio UI, then added model comparison, deterministic evaluation, request IDs, structured logs, metrics, and benchmark support.

## Technical Talking Points

- Provider abstraction keeps research logic independent from Ollama-specific client code.
- Static-first ingestion reduces overhead and only launches Playwright when content quality requires it.
- Prompt builders separate source content from instructions and require the model to use only provided page text.
- JSON plus Pydantic validation catches malformed model output instead of trusting free-form responses.
- Model comparison reuses the same `WebDocument` for each model so latency and output quality are compared against the same source content.
- Observability is local-first: request IDs, timings, counters, and structured logs without an external telemetry service.

## Key Engineering Tradeoffs

- Synchronous API routes match the blocking nature of requests, Playwright, and local model generation; production scale would require queueing or background jobs.
- In-process metrics are simple and demo-friendly, but they reset on process restart and are not a persistent analytics store.
- Deterministic evaluation is transparent and testable, but it is not equivalent to human review or a judge-model framework.
- Context truncation keeps prompts bounded without adding embeddings or vector retrieval, which are intentionally left for future work.
