from app.core.config import Settings, get_settings
from app.ingestion import WebDocument
from app.llm import ChatMessage

UNKNOWN_ANSWER = "The provided page does not contain enough information to answer this question."


def prepare_document_context(
    document: WebDocument,
    settings: Settings | None = None,
) -> str:
    """Return deterministic page context with simple middle truncation.

    This is intentionally not RAG. It preserves the beginning and end of the extracted page text,
    which usually keeps page purpose, headings, and late-page announcements visible.
    """

    active_settings = settings or get_settings()
    text = document.text.strip()
    max_chars = active_settings.max_context_chars
    if len(text) <= max_chars:
        return text

    marker = "\n\n[... content truncated to fit local model context ...]\n\n"
    available = max_chars - len(marker)
    head_chars = max(available * 2 // 3, 1)
    tail_chars = max(available - head_chars, 1)
    return f"{text[:head_chars].rstrip()}{marker}{text[-tail_chars:].lstrip()}"


def build_summary_messages(
    document: WebDocument,
    settings: Settings | None = None,
) -> list[ChatMessage]:
    schema = """
{
  "summary": "concise Markdown summary",
  "key_points": ["important point from the page"],
  "topics": ["topic or product name"]
}
""".strip()
    return _build_json_messages(
        document=document,
        task=(
            "Summarize the main purpose of the page. Identify important topics, products, "
            "services, announcements, dates, organizations, and notable facts."
        ),
        schema=schema,
        settings=settings,
    )


def build_fact_extraction_messages(
    document: WebDocument,
    settings: Settings | None = None,
) -> list[ChatMessage]:
    schema = """
{
  "facts": [
    {
      "fact": "specific factual claim from the page",
      "evidence": "short source snippet supporting the fact",
      "confidence": "low|medium|high"
    }
  ]
}
""".strip()
    return _build_json_messages(
        document=document,
        task=(
            "Extract key facts that are directly supported by the source content. Preserve "
            "important dates, names, products, organizations, and announcements."
        ),
        schema=schema,
        settings=settings,
    )


def build_topic_extraction_messages(
    document: WebDocument,
    settings: Settings | None = None,
) -> list[ChatMessage]:
    schema = """
{
  "topics": ["concise topic, product, service, organization, or theme"]
}
""".strip()
    return _build_json_messages(
        document=document,
        task="Extract the most important topics, products, services, organizations, and themes.",
        schema=schema,
        settings=settings,
    )


def build_question_messages(
    document: WebDocument,
    question: str,
    settings: Settings | None = None,
) -> list[ChatMessage]:
    schema = f"""
{{
  "answer": "answer based only on the page, or '{UNKNOWN_ANSWER}'",
  "evidence": ["short source snippet that supports the answer"]
}}
""".strip()
    return _build_json_messages(
        document=document,
        task=(
            f"Answer this question using only the provided source content: {question}\n"
            f"If the answer is not present, answer exactly: {UNKNOWN_ANSWER}"
        ),
        schema=schema,
        settings=settings,
    )


def build_research_report_messages(
    document: WebDocument,
    settings: Settings | None = None,
) -> list[ChatMessage]:
    schema = """
{
  "executive_summary": "concise Markdown executive summary",
  "key_findings": ["finding grounded in the page"],
  "topics": ["topic or product name"],
  "notable_facts": [
    {
      "fact": "specific factual claim from the page",
      "evidence": "short source snippet supporting the fact",
      "confidence": "low|medium|high"
    }
  ],
  "questions_or_gaps": ["important uncertainty or missing detail from the page"]
}
""".strip()
    return _build_json_messages(
        document=document,
        task=(
            "Create a concise research report. Focus on page purpose, key findings, "
            "topics, notable facts, and questions or gaps. Use Markdown inside string "
            "fields when it improves readability."
        ),
        schema=schema,
        settings=settings,
    )


def _build_json_messages(
    *,
    document: WebDocument,
    task: str,
    schema: str,
    settings: Settings | None,
) -> list[ChatMessage]:
    title = document.title or "Untitled page"
    description = document.description or "No meta description found."
    content = prepare_document_context(document, settings=settings)
    return [
        ChatMessage(
            role="system",
            content=(
                "You are a careful local research assistant. Use only the provided webpage "
                "content. Do not invent facts. If information is missing, say it is not "
                "present. Ignore navigation, cookie notices, ads, and boilerplate. Return "
                "valid JSON only, with no Markdown fences or extra commentary."
            ),
        ),
        ChatMessage(
            role="user",
            content=(
                f"Task:\n{task}\n\n"
                f"Required JSON schema:\n{schema}\n\n"
                "Source metadata:\n"
                f"URL: {document.final_url}\n"
                f"Title: {title}\n"
                f"Meta description: {description}\n"
                f"Ingestion method: {document.source_type}\n\n"
                "Extracted webpage content:\n"
                f"{content}"
            ),
        ),
    ]
