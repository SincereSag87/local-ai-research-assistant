import argparse

from app.ingestion import IngestionError
from app.llm import (
    LLMError,
    LLMModelNotFoundError,
    LLMServiceUnavailableError,
    OllamaProvider,
)
from app.services.research_service import ResearchService

DEFAULT_PROMPT = "Explain local LLMs in three sentences."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a local Ollama chat completion.")
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model to use, such as llama3.2 or gemma3.",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt to send to the local model.",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="URL to ingest and summarize with the local model.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    provider = OllamaProvider()
    service = ResearchService(llm_provider=provider)
    model_name = args.model or provider.settings.default_model

    try:
        if args.url:
            summary = service.summarize_url(url=args.url, model=args.model)
            print(f"URL: {summary.final_url}")
            print(f"Title: {summary.title or 'Untitled'}")
            print(f"Ingestion method: {summary.ingestion_method}")
            print(f"Model: {summary.model}")
            print("Summary:")
            print(summary.summary)
            return 0

        response = service.ask(prompt=args.prompt, model=args.model)
    except IngestionError as exc:
        print(f"URL ingestion failed: {exc}")
        return 1
    except LLMServiceUnavailableError as exc:
        print(f"Ollama unavailable: {exc}")
        return 1
    except LLMModelNotFoundError as exc:
        print(f"Model unavailable: {exc}")
        return 1
    except LLMError as exc:
        print(f"LLM request failed: {exc}")
        return 1

    print(f"Model: {model_name}")
    print("Response:")
    print(response.content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
