from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.knowledge_evidence import GroundedContext
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName
from app.domain.services.chat_intent_classifier import normalize_chat_text


class ChatResponsePolicy:
    """Social replies are local; knowledge answers require usable retrieved evidence."""

    def __init__(self, prompts: PromptCatalog) -> None:
        self._prompts = prompts

    @property
    def retrieval_guidance(self) -> str:
        return self._prompts.get(PromptName.RETRIEVAL_GUIDANCE)

    def deterministic_reply(self, intent: ChatIntent, text: str, grounded: GroundedContext) -> str | None:
        if intent == ChatIntent.GENERAL:
            return self._general_reply(text)
        if not grounded.evidence or not grounded.prompt_context.strip():
            return self._prompts.get(PromptName.NO_EVIDENCE)
        return None

    def _general_reply(self, text: str) -> str:
        normalized = normalize_chat_text(text)
        if any(phrase in normalized for phrase in ("tam biet", "hen gap lai", "goodbye", "bye")):
            return self._prompts.get(PromptName.FAREWELL)
        if any(phrase in normalized for phrase in ("cam on", "thank you", "thanks")):
            return self._prompts.get(PromptName.THANKS)
        return self._prompts.get(PromptName.GREETING)
