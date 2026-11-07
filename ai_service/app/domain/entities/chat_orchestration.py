from enum import StrEnum


class ChatIntent(StrEnum):
    """The only routing decisions supported by the chat application."""

    GENERAL = "general"
    RETRIEVAL = "retrieval"
