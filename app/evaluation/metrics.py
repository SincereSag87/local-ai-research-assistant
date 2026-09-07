from typing import Any

from pydantic import BaseModel

from app.evaluation.models import ComparisonTask, EvaluationMetrics
from app.research.models import KeyFact, QuestionAnswer, ResearchReport, ResearchSummary
from app.research.prompts import UNKNOWN_ANSWER


def evaluate_result(
    *,
    task: ComparisonTask,
    result: Any,
    latency_ms: int,
) -> EvaluationMetrics:
    response_text = _result_to_text(result)
    checks = _completeness_checks(task, result)
    grounded = _grounding_check(task, result)
    answer_behavior = _answer_present_behavior(task, result)
    fact_count = _fact_count(task, result)

    return EvaluationMetrics(
        grounded=grounded,
        contains_required_fields=all(checks.values()),
        answer_present_behavior=answer_behavior,
        completeness_score=sum(1 for passed in checks.values() if passed),
        completeness_checks=checks,
        response_length=len(response_text),
        word_count=len(response_text.split()),
        bullet_count=response_text.count("\n- ") + response_text.count("\n* "),
        fact_count=fact_count,
        latency_ms=latency_ms,
    )


def _completeness_checks(task: ComparisonTask, result: Any) -> dict[str, bool]:
    if task == "summary" and isinstance(result, ResearchSummary):
        return {
            "summary": bool(result.summary.strip()),
            "key_points": bool(result.key_points),
            "topics": bool(result.topics),
        }

    if task == "facts" and isinstance(result, list):
        facts = [fact for fact in result if isinstance(fact, KeyFact)]
        return {
            "facts": bool(facts),
            "facts_have_evidence": all(bool(fact.evidence.strip()) for fact in facts),
        }

    if task == "topics" and isinstance(result, list):
        return {"topics": bool([topic for topic in result if isinstance(topic, str) and topic])}

    if task == "ask" and isinstance(result, QuestionAnswer):
        answer = result.answer.strip()
        unknown = answer == UNKNOWN_ANSWER
        return {
            "answer": bool(answer),
            "evidence_or_unknown": bool(result.evidence) or unknown,
        }

    if task == "report" and isinstance(result, ResearchReport):
        return {
            "executive_summary": bool(result.executive_summary.strip()),
            "key_findings": bool(result.key_findings),
            "topics": bool(result.topics),
            "notable_facts": bool(result.notable_facts),
        }

    return {"recognized_result": False}


def _grounding_check(task: ComparisonTask, result: Any) -> bool:
    if task == "facts" and isinstance(result, list):
        facts = [fact for fact in result if isinstance(fact, KeyFact)]
        return bool(facts) and all(bool(fact.evidence.strip()) for fact in facts)

    if task == "ask" and isinstance(result, QuestionAnswer):
        if result.answer == UNKNOWN_ANSWER:
            return True
        return bool(result.evidence)

    if task == "report" and isinstance(result, ResearchReport):
        return all(bool(fact.evidence.strip()) for fact in result.notable_facts)

    return True


def _answer_present_behavior(task: ComparisonTask, result: Any) -> str | None:
    if task != "ask" or not isinstance(result, QuestionAnswer):
        return None
    if result.answer == UNKNOWN_ANSWER:
        return "explicit_insufficient_information"
    if result.evidence:
        return "answered_with_evidence"
    return "answered_without_evidence"


def _fact_count(task: ComparisonTask, result: Any) -> int:
    if task == "facts" and isinstance(result, list):
        return len([fact for fact in result if isinstance(fact, KeyFact)])
    if task == "report" and isinstance(result, ResearchReport):
        return len(result.notable_facts)
    return 0


def _result_to_text(result: Any) -> str:
    if isinstance(result, BaseModel):
        return result.model_dump_json()
    if isinstance(result, list):
        parts = []
        for item in result:
            if isinstance(item, BaseModel):
                parts.append(item.model_dump_json())
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(result)
