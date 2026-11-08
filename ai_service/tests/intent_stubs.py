from app.domain.entities.chat_orchestration import ChatIntent


class StubIntentClassifier:
    """Explicit routing outcome without calling a live model in orchestration tests."""

    def __init__(self, intent: ChatIntent = ChatIntent.RETRIEVAL) -> None:
        self.intent = intent
        self.calls: list[tuple[str, tuple[tuple[str, str], ...]]] = []

    async def classify(self, text: str, *, history=()) -> ChatIntent:
        self.calls.append((text, history))
        return self.intent
