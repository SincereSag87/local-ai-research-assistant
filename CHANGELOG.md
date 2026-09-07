# Changelog

## v1.0.0 - Portfolio Release

- Added a local Ollama provider abstraction with `llama3.2` and `gemma3` support.
- Added static webpage ingestion with BeautifulSoup and Playwright browser fallback.
- Added normalized `WebDocument` models for source-aware research workflows.
- Added structured research summaries, key fact extraction, topic extraction, grounded Q&A, and research reports.
- Added JSON-first model responses with Pydantic validation and explicit parse errors.
- Added deterministic model comparison and lightweight evaluation metrics.
- Added FastAPI backend endpoints for research, comparison, health, readiness, and metrics.
- Added Gradio UI for research tasks, model comparison, health checks, and observability.
- Added request IDs, structured logging, in-process metrics, and a benchmark runner.
- Added pytest and Ruff coverage across core services, API routes, UI formatting/client logic, evaluation, and observability.
