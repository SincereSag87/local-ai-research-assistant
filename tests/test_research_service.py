from app.evaluation import ModelComparisonResult
from app.ingestion import WebDocument
from app.llm import ChatResponse
from app.research import KeyFact, QuestionAnswer, ResearchReport, ResearchSummary
from app.services.research_service import ResearchService


class FakeProvider:
    def __init__(self):
        self.messages = None
        self.model = None

    def generate(self, messages, model=None):
        self.messages = messages
        self.model = model
        return ChatResponse(model=model or "llama3.2", content="## Summary\nUseful page summary.")


class FakeEngine:
    def __init__(self):
        self.calls = []

    def summarize(self, document, model=None):
        self.calls.append(("summary", document, model))
        return ResearchSummary(
            title=document.title,
            source_url=document.final_url,
            model=model or "llama3.2",
            summary="Summary",
            key_points=["Point"],
            topics=["Topic"],
            ingestion_method=document.source_type,
        )

    def extract_facts(self, document, model=None):
        self.calls.append(("facts", document, model))
        return [KeyFact(fact="Fact", evidence="Evidence", confidence="high")]

    def extract_topics(self, document, model=None):
        self.calls.append(("topics", document, model))
        return ["Topic"]

    def answer_question(self, document, question, model=None):
        self.calls.append(("ask", document, question, model))
        return QuestionAnswer(
            question=question,
            answer="Answer",
            evidence=["Evidence"],
            source_url=document.final_url,
            model=model or "llama3.2",
        )

    def generate_report(self, document, model=None):
        self.calls.append(("report", document, model))
        return ResearchReport(
            title=document.title,
            source_url=document.final_url,
            executive_summary="Report",
            key_findings=["Finding"],
            topics=["Topic"],
            notable_facts=[],
            questions_or_gaps=[],
            model=model or "llama3.2",
            ingestion_method=document.source_type,
        )


class FakeComparator:
    def __init__(self):
        self.calls = []

    def compare_summary(self, document, models):
        self.calls.append(("summary", document, models))
        return make_comparison_result(document, "summary", models)

    def compare_facts(self, document, models):
        self.calls.append(("facts", document, models))
        return make_comparison_result(document, "facts", models)

    def compare_topics(self, document, models):
        self.calls.append(("topics", document, models))
        return make_comparison_result(document, "topics", models)

    def compare_question(self, document, question, models):
        self.calls.append(("ask", document, question, models))
        return make_comparison_result(document, "ask", models)

    def compare_report(self, document, models):
        self.calls.append(("report", document, models))
        return make_comparison_result(document, "report", models)


class FakeIngestor:
    def __init__(self):
        self.calls = 0

    def ingest(self, url: str) -> WebDocument:
        self.calls += 1
        return WebDocument(
            url=url,
            final_url="https://example.com/final",
            title="Example Page",
            text="This page describes an example product and a notable announcement.",
            links=[],
            description="Example description",
            source_type="static",
            status_code=200,
        )


def make_comparison_result(document, task, models):
    return ModelComparisonResult(
        task=task,
        source_url=document.final_url,
        ingestion_method=document.source_type,
        runs=[],
        fastest_model=models[0],
        valid_models=list(models),
        summary="Compared models.",
    )


def test_research_service_summarizes_url_with_structured_result():
    engine = FakeEngine()
    service = ResearchService(
        llm_provider=FakeProvider(),
        web_ingestor=FakeIngestor(),
        research_engine=engine,
    )

    result = service.summarize_url("https://example.com", model="gemma3")

    assert str(result.source_url) == "https://example.com/final"
    assert result.title == "Example Page"
    assert result.model == "gemma3"
    assert result.ingestion_method == "static"
    assert result.summary == "Summary"
    assert engine.calls[0][0] == "summary"
    assert engine.calls[0][2] == "gemma3"


def test_research_service_orchestrates_facts_topics_question_and_report():
    engine = FakeEngine()
    service = ResearchService(
        llm_provider=FakeProvider(),
        web_ingestor=FakeIngestor(),
        research_engine=engine,
    )

    facts = service.extract_facts_from_url("https://example.com", model="gemma3")
    topics = service.extract_topics_from_url("https://example.com")
    answer = service.answer_url_question("https://example.com", "What is listed?", model="gemma3")
    report = service.generate_url_report("https://example.com")

    assert facts[0].fact == "Fact"
    assert topics == ["Topic"]
    assert answer.question == "What is listed?"
    assert report.executive_summary == "Report"
    assert [call[0] for call in engine.calls] == ["facts", "topics", "ask", "report"]
    assert engine.calls[0][2] == "gemma3"
    assert engine.calls[2][3] == "gemma3"


def test_research_service_compares_url_task_with_single_ingestion():
    ingestor = FakeIngestor()
    comparator = FakeComparator()
    service = ResearchService(
        llm_provider=FakeProvider(),
        web_ingestor=ingestor,
        research_engine=FakeEngine(),
        model_comparator=comparator,
    )

    result = service.compare_url_task(
        url="https://example.com",
        task="ask",
        question="What is listed?",
        models=["llama3.2", "gemma3"],
    )

    assert result.valid_models == ["llama3.2", "gemma3"]
    assert ingestor.calls == 1
    assert comparator.calls[0][0] == "ask"
    assert comparator.calls[0][3] == ["llama3.2", "gemma3"]
