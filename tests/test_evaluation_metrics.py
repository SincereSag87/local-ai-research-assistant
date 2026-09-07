from app.evaluation.metrics import evaluate_result
from app.research import KeyFact, QuestionAnswer, ResearchReport, ResearchSummary
from app.research.prompts import UNKNOWN_ANSWER


def test_summary_metrics_check_required_fields():
    summary = ResearchSummary(
        title="Example",
        source_url="https://example.com",
        model="llama3.2",
        summary="Useful summary.",
        key_points=["Point"],
        topics=["Topic"],
        ingestion_method="static",
    )

    metrics = evaluate_result(task="summary", result=summary, latency_ms=12)

    assert metrics.contains_required_fields is True
    assert metrics.completeness_score == 3
    assert metrics.response_length > 0
    assert metrics.latency_ms == 12


def test_facts_metrics_require_evidence():
    facts = [KeyFact(fact="Fact", evidence="Evidence", confidence="high")]

    metrics = evaluate_result(task="facts", result=facts, latency_ms=5)

    assert metrics.grounded is True
    assert metrics.fact_count == 1
    assert metrics.contains_required_fields is True


def test_qa_metrics_accept_answer_with_evidence():
    answer = QuestionAnswer(
        question="What is this?",
        answer="It is an example.",
        evidence=["example"],
        source_url="https://example.com",
        model="llama3.2",
    )

    metrics = evaluate_result(task="ask", result=answer, latency_ms=5)

    assert metrics.grounded is True
    assert metrics.answer_present_behavior == "answered_with_evidence"


def test_qa_metrics_accept_explicit_unknown_answer_without_evidence():
    answer = QuestionAnswer(
        question="What is missing?",
        answer=UNKNOWN_ANSWER,
        evidence=[],
        source_url="https://example.com",
        model="llama3.2",
    )

    metrics = evaluate_result(task="ask", result=answer, latency_ms=5)

    assert metrics.grounded is True
    assert metrics.answer_present_behavior == "explicit_insufficient_information"
    assert metrics.contains_required_fields is True


def test_report_metrics_check_report_sections():
    report = ResearchReport(
        title="Example",
        source_url="https://example.com",
        executive_summary="Executive summary",
        key_findings=["Finding"],
        topics=["Topic"],
        notable_facts=[KeyFact(fact="Fact", evidence="Evidence", confidence="medium")],
        questions_or_gaps=[],
        model="llama3.2",
        ingestion_method="static",
    )

    metrics = evaluate_result(task="report", result=report, latency_ms=20)

    assert metrics.contains_required_fields is True
    assert metrics.grounded is True
    assert metrics.fact_count == 1
