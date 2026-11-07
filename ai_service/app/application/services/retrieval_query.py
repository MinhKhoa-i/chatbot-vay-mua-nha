from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName
from app.domain.services.chat_intent_classifier import ChatIntentClassifier


class RetrievalQueryBuilder:
    """Bound conversational search context without treating model replies as evidence."""

    def __init__(self, classifier: ChatIntentClassifier, prompts: PromptCatalog) -> None:
        self._classifier = classifier
        self._prompts = prompts

    def build(self, text: str, history: tuple[tuple[str, str], ...] = ()) -> str:
        previous_questions = [
            content[:1_000]
            for role, content in history[-20:]
            if role == "user" and self._classifier.classify(content) == ChatIntent.RETRIEVAL
        ][-2:]
        if not previous_questions:
            return text
        return self._prompts.get(PromptName.RETRIEVAL_QUERY).format(
            previous_questions="\n".join(previous_questions), text=text,
        )
