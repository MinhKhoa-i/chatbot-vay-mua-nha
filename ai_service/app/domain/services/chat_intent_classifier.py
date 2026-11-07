import re
import unicodedata

from app.domain.entities.chat_orchestration import ChatIntent


def normalize_chat_text(text: str) -> str:
    """Normalize Vietnamese accents, case and punctuation for exact social phrases."""
    decomposed = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    unaccented = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^\w\s]", " ", unaccented).split())


class ChatIntentClassifier:
    """Only complete social messages skip retrieval; uncertain messages fail closed."""

    _SOCIAL_PHRASE = (
        r"(?:xin chao|chao|hello|hi|hey|cam on|xin cam on|thank you|thanks|"
        r"tam biet|chao tam biet|hen gap lai|goodbye|bye|"
        r"chuc (?:ban )?(?:mot ngay tot lanh|ngay tot lanh|buoi sang tot lanh))"
        r"(?: (?:ban|bot|chatbot|nhe|nha|a|oi|nhieu|rat nhieu))*"
    )
    _SOCIAL_MESSAGE = re.compile(rf"{_SOCIAL_PHRASE}(?: {_SOCIAL_PHRASE})*")

    def classify(self, text: str) -> ChatIntent:
        normalized = normalize_chat_text(text)
        if self._SOCIAL_MESSAGE.fullmatch(normalized):
            return ChatIntent.GENERAL
        return ChatIntent.RETRIEVAL
