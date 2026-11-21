from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.knowledge_evidence import GroundedContext
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName


class ChatResponsePolicy:
    """General chat uses the model; knowledge answers require usable retrieved evidence."""

    @property
    def general_guidance(self) -> str:
        return self._prompts.get(PromptName.GENERAL_GUIDANCE)

    def __init__(self, prompts: PromptCatalog) -> None:
        self._prompts = prompts

    @property
    def retrieval_guidance(self) -> str:
        return self._prompts.get(PromptName.RETRIEVAL_GUIDANCE)

    def deterministic_reply(self, intent: ChatIntent, text: str, grounded: GroundedContext) -> str | None:
        if intent == ChatIntent.GENERAL:
            return None
        if not grounded.evidence or not grounded.prompt_context.strip():
            return self._prompts.get(PromptName.NO_EVIDENCE)
        return None
