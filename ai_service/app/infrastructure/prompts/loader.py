from functools import lru_cache
from pathlib import Path

from app.domain.errors import ChatError
from app.domain.ports.prompt_catalog import PromptName


class PromptLoadError(ChatError):
    """A required prompt resource is unavailable or invalid."""

    def __init__(self, message: str) -> None:
        super().__init__("PROMPT_UNAVAILABLE", stage="prompt")
        self.args = (message,)


class MarkdownPromptCatalog:
    """Load named UTF-8 Markdown resources once per catalog instance."""

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = (directory if directory is not None else Path(__file__).parent).resolve()
        self._cache: dict[PromptName, str] = {}

    def get(self, name: PromptName) -> str:
        name = PromptName(name)
        if name not in self._cache:
            path = self._directory / f"{name.value}.md"
            try:
                content = path.read_text(encoding="utf-8-sig").strip()
            except (OSError, UnicodeError) as exc:
                raise PromptLoadError(f"Cannot load prompt: {name.value}") from exc
            if not content:
                raise PromptLoadError(f"Prompt is empty: {name.value}")
            template_values = {
                PromptName.TURN_GUIDANCE: {"guidance": ""},
                PromptName.GROUNDING: {"knowledge_context": ""},
                PromptName.RETRIEVAL_QUERY: {"previous_questions": "", "text": ""},
                PromptName.ESTIMATE_QUESTIONS: {"fields": ""},
                PromptName.ESTIMATE_CONFIRMATION: {"amount": "", "years": "", "rate_text": "", "method_text": ""},
                PromptName.ESTIMATE_RESULT: {
                    "amount": "", "years": "", "rate_text": "", "method_text": "", "payment_label": "",
                    "monthly_payment": "", "total_interest": "", "payment_note": "",
                },
                PromptName.ESTIMATE_PROMO_TOO_LONG: {"promo_duration_months": "", "years": ""},
            }
            if name in template_values:
                try:
                    content.format(**template_values[name])
                except (KeyError, IndexError, ValueError, AttributeError, TypeError) as exc:
                    raise PromptLoadError(f"Invalid prompt template: {name.value}") from exc
            self._cache[name] = content
        return self._cache[name]


@lru_cache(maxsize=1)
def get_prompt_catalog() -> MarkdownPromptCatalog:
    catalog = MarkdownPromptCatalog()
    # Validate all required resources before accepting chat traffic.
    for name in PromptName:
        catalog.get(name)
    return catalog
