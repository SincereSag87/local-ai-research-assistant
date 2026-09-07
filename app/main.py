import argparse

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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    provider = OllamaProvider()
    service = ResearchService(llm_provider=provider)
    model_name = args.model or provider.settings.default_model

    try:
        response = service.ask(prompt=args.prompt, model=args.model)
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

