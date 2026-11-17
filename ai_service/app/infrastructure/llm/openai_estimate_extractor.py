import json
from dataclasses import asdict
from decimal import Decimal
from time import perf_counter

from openai import APIError, AsyncOpenAI

from app.domain.entities.estimate_session import EstimateExtraction, EstimateSession
from app.domain.ports.estimate_extractor import EstimateExtractionError
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName
from app.infrastructure.llm.provider_errors import translate_provider_error
from app.infrastructure.llm.usage_logging import log_usage

ESTIMATE_MAX_TOKENS = 512


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
        started_at = perf_counter()
        response = None
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
                    max_tokens=ESTIMATE_MAX_TOKENS,
                )
        except APIError as exc:
            error = translate_provider_error(exc)
            raise EstimateExtractionError(error.code, retryable=error.retryable) from exc
        finally:
            usage = response.usage if response is not None else None
            log_usage(
                task="estimate_extraction", model=self._model, started_at=started_at,
                usage=usage,
                status="success" if usage is not None else "error_or_unknown_usage",
            )
        if not response.choices or response.choices[0].finish_reason != "stop":
            raise EstimateExtractionError("ESTIMATE_EXTRACTION_INVALID_RESPONSE")
        return self._parse(response.choices[0].message.content, session=session)

    @staticmethod
    def _parse(
        content: str | None, *, session: EstimateSession | None = None,
    ) -> EstimateExtraction:
        try:
            payload = json.loads(content, parse_float=Decimal) if content else None
            if not isinstance(payload, dict) or set(payload) != {"action", "updates"}:
                raise ValueError("Invalid extraction object")
            if not isinstance(payload["updates"], dict):
                raise ValueError("Invalid updates")
            updates = dict(payload["updates"])
            if session is not None and payload["action"] == "update":
                current_values = {
                    "amount": session.amount,
                    "years": session.years,
                    "rate": session.rate,
                    "method": session.method,
                    "promo_rate": session.promo_rate,
                    "promo_duration_months": session.promo_duration_months,
                }
                for name, value in tuple(updates.items()):
                    if value is None:
                        if name not in current_values:
                            raise ValueError(f"Unknown estimate field: {name}")
                        if current_values[name] is None:
                            del updates[name]
                        else:
                            return EstimateExtraction("unsupported", {})
            for name in ("rate", "promo_rate"):
                if name in updates:
                    if isinstance(updates[name], (bool, str)) or updates[name] is None:
                        raise ValueError(f"Invalid {name}")
                    updates[name] = Decimal(str(updates[name]))
            return EstimateExtraction(payload["action"], updates)
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise EstimateExtractionError("ESTIMATE_EXTRACTION_INVALID_RESPONSE") from exc
