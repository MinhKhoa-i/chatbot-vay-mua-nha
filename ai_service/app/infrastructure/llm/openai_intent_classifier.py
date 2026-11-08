import json

from openai import APIError, AsyncOpenAI

from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.ports.chat_intent_classifier import IntentClassificationError
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName
from app.infrastructure.llm.provider_errors import translate_provider_error


class OpenAIIntentClassifier:
    """Classify through an OpenAI-compatible provider; only validated labels escape."""

    def __init__(
        self, *, base_url: str, api_key: str, model: str, prompts: PromptCatalog,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._prompts = prompts
        self._timeout = timeout_seconds

    async def classify(
        self, text: str, *, history: tuple[tuple[str, str], ...] = (),
    ) -> ChatIntent:
        if not self._base_url or not self._api_key or not self._model:
            raise IntentClassificationError("CLASSIFICATION_NOT_CONFIGURED", retryable=False)
        instruction = self._prompts.get(PromptName.INTENT_CLASSIFICATION)
        try:
            async with AsyncOpenAI(
                base_url=self._base_url, api_key=self._api_key,
                timeout=self._timeout, max_retries=0,
            ) as client:
                response = await client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": instruction},
                        *[
                            {"role": role, "content": content[:1_000]}
                            for role, content in history[-6:]
                            if role in {"user", "assistant"}
                        ],
                        {"role": "user", "content": text},
                    ],
                    stream=False,
                    response_format={"type": "json_object"},
                )
        except APIError as exc:
            provider_error = translate_provider_error(exc)
            raise IntentClassificationError(
                provider_error.code, retryable=provider_error.retryable,
            ) from exc
        if not response.choices or response.choices[0].finish_reason != "stop":
            raise IntentClassificationError("CLASSIFICATION_INVALID_RESPONSE")
        return self._parse_intent(response.choices[0].message.content)

    @staticmethod
    def _parse_intent(content: str | None) -> ChatIntent:
        try:
            payload = json.loads(content) if content else None
            if not isinstance(payload, dict) or set(payload) != {"intent"}:
                raise ValueError("Expected exactly one intent field")
            return ChatIntent(payload["intent"])
        except (TypeError, ValueError) as exc:
            raise IntentClassificationError("CLASSIFICATION_INVALID_RESPONSE") from exc
