import argparse
from collections.abc import Sequence

from app.evaluation.formatter import format_comparison_json, format_comparison_text
from app.ingestion import IngestionError
from app.llm import (
    LLMError,
    LLMModelNotFoundError,
    LLMServiceUnavailableError,
    OllamaProvider,
)
from app.research import (
    KeyFact,
    QuestionAnswer,
    ResearchParseError,
    ResearchReport,
    ResearchSummary,
)
from app.services.research_service import ResearchService

DEFAULT_PROMPT = "Explain local LLMs in three sentences."
TASKS = ("summary", "facts", "topics", "ask", "report")


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
        help="URL to ingest and research with the local model.",
    )
    parser.add_argument(
        "--task",
        default="summary",
        choices=TASKS,
        help="Research task to run when --url is provided.",
    )
    parser.add_argument(
        "--question",
        default=None,
        help="Question to answer when --task ask is selected.",
    )
    parser.add_argument(
        "--compare",
        nargs="+",
        default=None,
        help="Compare the selected task across models, such as llama3.2 gemma3.",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format for comparison results.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    provider = OllamaProvider()
    service = ResearchService(llm_provider=provider)
    model_name = args.model or provider.settings.default_model

    try:
        if args.url:
            if args.task == "ask" and not args.question:
                print("--question is required when --task ask is selected.")
                return 1
            if args.compare:
                comparison = service.compare_url_task(
                    url=args.url,
                    task=args.task,
                    question=args.question,
                    models=args.compare,
                )
                if args.output == "json":
                    print(format_comparison_json(comparison))
                else:
                    print(format_comparison_text(comparison))
                return 0
            _run_url_task(
                service=service,
                url=args.url,
                task=args.task,
                question=args.question,
                model=args.model,
            )
            return 0

        response = service.ask(prompt=args.prompt, model=args.model)
    except IngestionError as exc:
        print(f"URL ingestion failed: {exc}")
        return 1
    except ResearchParseError as exc:
        print(f"Research output parsing failed: {exc}")
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


def _run_url_task(
    *,
    service: ResearchService,
    url: str,
    task: str,
    question: str | None,
    model: str | None,
) -> None:
    if task == "summary":
        _print_summary(service.summarize_url(url=url, model=model))
    elif task == "facts":
        _print_facts(url=url, facts=service.extract_facts_from_url(url=url, model=model))
    elif task == "topics":
        _print_topics(url=url, topics=service.extract_topics_from_url(url=url, model=model))
    elif task == "ask":
        if question is None:
            raise ValueError("question is required")
        _print_answer(service.answer_url_question(url=url, question=question, model=model))
    elif task == "report":
        _print_report(service.generate_url_report(url=url, model=model))


def _print_summary(summary: ResearchSummary) -> None:
    print(f"URL: {summary.source_url}")
    print(f"Title: {summary.title or 'Untitled'}")
    print(f"Ingestion method: {summary.ingestion_method}")
    print(f"Model: {summary.model}")
    print("Summary:")
    print(summary.summary)
    if summary.key_points:
        print("\nKey points:")
        _print_list(summary.key_points)
    if summary.topics:
        print("\nTopics:")
        _print_list(summary.topics)


def _print_facts(*, url: str, facts: Sequence[KeyFact]) -> None:
    print(f"URL: {url}")
    print("Key facts:")
    if not facts:
        print("- None")
        return
    for index, fact in enumerate(facts, start=1):
        print(f"{index}. {fact.fact}")
        print(f"   Evidence: {fact.evidence}")
        print(f"   Confidence: {fact.confidence}")


def _print_topics(*, url: str, topics: Sequence[str]) -> None:
    print(f"URL: {url}")
    print("Topics:")
    _print_list(topics)


def _print_answer(answer: QuestionAnswer) -> None:
    print(f"URL: {answer.source_url}")
    print(f"Question: {answer.question}")
    print(f"Model: {answer.model}")
    print("Answer:")
    print(answer.answer)
    if answer.evidence:
        print("\nEvidence:")
        _print_list(answer.evidence)


def _print_report(report: ResearchReport) -> None:
    print(f"# {report.title or 'Research Report'}")
    print(f"URL: {report.source_url}")
    print(f"Ingestion method: {report.ingestion_method}")
    print(f"Model: {report.model}")
    print("\n## Executive Summary")
    print(report.executive_summary)
    print("\n## Key Findings")
    _print_list(report.key_findings)
    print("\n## Topics")
    _print_list(report.topics)
    print("\n## Notable Facts")
    if not report.notable_facts:
        print("- None")
    for fact in report.notable_facts:
        print(f"- {fact.fact}")
        print(f"  Evidence: {fact.evidence}")
        print(f"  Confidence: {fact.confidence}")
    print("\n## Questions Or Gaps")
    _print_list(report.questions_or_gaps)


def _print_list(items: Sequence[str]) -> None:
    if not items:
        print("- None")
        return
    for item in items:
        print(f"- {item}")


if __name__ == "__main__":
    raise SystemExit(main())
