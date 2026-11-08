import re
import unicodedata


def normalize_chat_text(text: str) -> str:
    """Normalize Vietnamese accents, case and punctuation for exact social phrases."""
    decomposed = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    unaccented = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^\w\s]", " ", unaccented).split())
