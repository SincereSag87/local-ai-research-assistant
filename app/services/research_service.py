from app.llm import ChatMessage, ChatResponse, LLMProvider


class ResearchService:
    """Thin service layer for research-oriented LLM interactions."""

    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def ask(self, prompt: str, model: str | None = None) -> ChatResponse:
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "You are a concise research assistant that explains "
                    "technical topics clearly."
                ),
            ),
            ChatMessage(role="user", content=prompt),
        ]
        return self.llm_provider.generate(messages=messages, model=model)
