from app.core.config import Settings
from app.ingestion import WebDocument
from app.research.prompts import (
    UNKNOWN_ANSWER,
    build_question_messages,
    build_summary_messages,
    prepare_document_context,
)


def make_document(text: str = "This page announces Example Product on January 1, 2026."):
    return WebDocument(
        url="https://example.com",
        final_url="https://example.com/final",
        title="Example Page",
        text=text,
        links=[],
        description="Example description",
        source_type="static",
        status_code=200,
    )


def test_summary_prompt_separates_instructions_schema_and_source_content():
    messages = build_summary_messages(make_document())

    assert messages[0].role == "system"
    assert "use only the provided webpage content" in messages[0].content.lower()
    assert "valid json only" in messages[0].content.lower()
    assert messages[1].role == "user"
    assert "Required JSON schema" in messages[1].content
    assert "Extracted webpage content" in messages[1].content
    assert "Example Product" in messages[1].content


def test_question_prompt_includes_unknown_answer_instruction():
    messages = build_question_messages(make_document(), "Who founded Example?")

    assert "Who founded Example?" in messages[1].content
    assert UNKNOWN_ANSWER in messages[1].content


def test_prepare_document_context_truncates_large_content_with_marker():
    text = "A" * 4000 + "MIDDLE" + "Z" * 4000
    context = prepare_document_context(
        make_document(text),
        settings=Settings(max_context_chars=1200),
    )

    assert len(context) <= 1200
    assert "content truncated" in context
    assert context.startswith("A")
    assert context.endswith("Z")
