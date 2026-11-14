import json
from dataclasses import asdict
from decimal import Decimal

from openai import APIError, AsyncOpenAI

from app.domain.entities.estimate_session import EstimateExtraction, EstimateSession
from app.domain.ports.estimate_extractor import EstimateExtractionError
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName
from app.infrastructure.llm.provider_errors import translate_provider_error


class OpenAIEstimateExtractor:
    def __init__(
        self, *, base_url: str, api_key: str, model: str, prompts: PromptCatalog,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._prompts = prompts
        self._timeout = timeout_seconds

    async def extract(self, text: str, session: EstimateSession) -> EstimateExtraction:
        if not self._base_url or not self._api_key or not self._model:
            raise EstimateExtractionError("ESTIMATE_EXTRACTION_NOT_CONFIGURED", retryable=False)
        instruction = self._prompts.get(PromptName.ESTIMATE_EXTRACTION)
        try:
            async with AsyncOpenAI(
                base_url=self._base_url, api_key=self._api_key,
                timeout=self._timeout, max_retries=0,
            ) as client:
                response = await client.chat.completions.create(
                    model=self._model, stream=False, response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": instruction},
                        {"role": "user", "content": json.dumps({
                            "session": asdict(session), "message": text,
                        }, default=str, ensure_ascii=False)},
                    ],
                )
        except APIError as exc:
            error = translate_provider_error(exc)
            raise EstimateExtractionError(error.code, retryable=error.retryable) from exc
        if not response.choices or response.choices[0].finish_reason != "stop":
            raise EstimateExtractionError("ESTIMATE_EXTRACTION_INVALID_RESPONSE")
        return self._parse(response.choices[0].message.content)

    @staticmethod
    def _parse(content: str | None) -> EstimateExtraction:
        try:
            payload = json.loads(content, parse_float=Decimal) if content else None
            if not isinstance(payload, dict) or set(payload) != {"action", "updates"}:
                raise ValueError("Invalid extraction object")
            if not isinstance(payload["updates"], dict):
                raise ValueError("Invalid updates")
            updates = payload["updates"]
            for name in ("rate", "promo_rate"):
                if name in updates:
                    if isinstance(updates[name], (bool, str)) or updates[name] is None:
                        raise ValueError(f"Invalid {name}")
                    updates[name] = Decimal(str(updates[name]))
            return EstimateExtraction(payload["action"], updates)
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise EstimateExtractionError("ESTIMATE_EXTRACTION_INVALID_RESPONSE") from exc
