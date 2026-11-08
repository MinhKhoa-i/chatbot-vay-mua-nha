from app.domain.ports.prompt_catalog import PromptCatalog, PromptName


class RetrievalQueryBuilder:
    """Bound conversational search context without treating model replies as evidence."""

    def __init__(self, prompts: PromptCatalog) -> None:
        self._prompts = prompts

    def build(self, text: str, history: tuple[tuple[str, str], ...] = ()) -> str:
        previous_questions = [
            content[:1_000]
            for role, content in history[-20:]
            if role == "user"
        ][-2:]
        if not previous_questions:
            return text
        return self._prompts.get(PromptName.RETRIEVAL_QUERY).format(
            previous_questions="\n".join(previous_questions), text=text,
        )
