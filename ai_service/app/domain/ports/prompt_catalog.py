from enum import StrEnum
from typing import Protocol


class PromptName(StrEnum):
    CHAT_SYSTEM = "chat_system"
    TURN_GUIDANCE = "turn_guidance"
    GROUNDING = "grounding"
    RETRIEVAL_GUIDANCE = "retrieval_guidance"
    RETRIEVAL_QUERY = "retrieval_query"
    GREETING = "greeting"
    THANKS = "thanks"
    FAREWELL = "farewell"
    NO_EVIDENCE = "no_evidence"


class PromptCatalog(Protocol):
    """Application-owned text resources; implementations decide how to load them."""

    def get(self, name: PromptName) -> str: ...
