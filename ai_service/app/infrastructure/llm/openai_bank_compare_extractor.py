import json
from dataclasses import asdict
from decimal import Decimal
from time import perf_counter

from openai import APIError, AsyncOpenAI

from app.domain.entities.bank_compare_session import (
    BANK_COMPARE_FIELDS,
    BankCompareExtraction,
    BankCompareSession,
)
from app.domain.ports.bank_compare_extractor import BankCompareExtractionError
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName
from app.infrastructure.llm.provider_errors import translate_provider_error
from app.infrastructure.llm.usage_logging import log_usage

BANK_COMPARE_MAX_TOKENS = 512


class OpenAIBankCompareExtractor:
    def __init__(
        self, *, base_url: str, api_key: str, model: str, prompts: PromptCatalog,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._prompts = prompts
        self._timeout = timeout_seconds

    async def extract(self, text: str, session: BankCompareSession) -> BankCompareExtraction:
        if not self._base_url or not self._api_key or not self._model:
            raise BankCompareExtractionError("BANK_COMPARE_EXTRACTION_NOT_CONFIGURED", retryable=False)
        instruction = self._prompts.get(PromptName.BANK_COMPARE_EXTRACTION)
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
                    max_tokens=BANK_COMPARE_MAX_TOKENS,
                )
        except APIError as exc:
            error = translate_provider_error(exc)
            raise BankCompareExtractionError(error.code, retryable=error.retryable) from exc
        finally:
            usage = response.usage if response is not None else None
            log_usage(
                task="bank_compare_extraction", model=self._model, started_at=started_at,
                usage=usage,
                status="success" if usage is not None else "error_or_unknown_usage",
            )
        if response is None:
            raise BankCompareExtractionError("BANK_COMPARE_EXTRACTION_INVALID_RESPONSE")
        choices = response.choices
        if not choices or choices[0].finish_reason != "stop":
            raise BankCompareExtractionError("BANK_COMPARE_EXTRACTION_INVALID_RESPONSE")
        return self._parse(choices[0].message.content, session=session)

    @staticmethod
    def _parse(
        content: str | None, *, session: BankCompareSession | None = None,
    ) -> BankCompareExtraction:
        try:
            payload = json.loads(content, parse_float=Decimal) if content else None
            if not isinstance(payload, dict) or set(payload) != {"action", "updates"}:
                raise ValueError("Invalid extraction object")
            if not isinstance(payload["updates"], dict):
                raise ValueError("Invalid updates")
            updates = dict(payload["updates"])
            if not set(updates) <= BANK_COMPARE_FIELDS:
                raise ValueError("Unknown bank comparison field")
            if any(value is None for value in updates.values()):
                if session is None or any(
                    value is None or getattr(session, name, None) is not None
                    for name, value in updates.items()
                ):
                    raise ValueError("Null updates are not allowed")
                return BankCompareExtraction("unrelated", {})
            if any(isinstance(value, bool) for value in updates.values()):
                raise ValueError("Boolean updates are not allowed")
            for name in ("assumed_floating_rate", "base_rate"):
                if name in updates:
                    if isinstance(updates[name], str):
                        raise ValueError(f"Invalid {name}")
                    updates[name] = Decimal(str(updates[name]))
            extraction = BankCompareExtraction(payload["action"], updates)
            if session is not None and extraction.action == "update":
                session.updated(updates)
            return extraction
        except (ValueError, TypeError, ArithmeticError) as exc:
            raise BankCompareExtractionError("BANK_COMPARE_EXTRACTION_INVALID_RESPONSE") from exc
