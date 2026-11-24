from collections.abc import AsyncIterator
from time import perf_counter

from openai import APIError, AsyncOpenAI

from app.domain.ports.chat_completion import ChatProviderUnavailable
from app.domain.ports.prompt_catalog import PromptCatalog, PromptName
from app.infrastructure.llm.provider_errors import translate_provider_error
from app.infrastructure.llm.usage_logging import log_usage
from app.infrastructure.prompts.loader import get_prompt_catalog


class OpenAIChatAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 45.0,
        max_tokens: int = 2_000,
        prompts: PromptCatalog | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens
        self._prompts = prompts if prompts is not None else get_prompt_catalog()

    async def stream_reply(
        self,
        text: str,
        *,
        history: tuple[tuple[str, str], ...] = (),
        memory_context: str = "",
        guidance: str = "",
        knowledge_context: str = "",
    ) -> AsyncIterator[str]:
        if not self._base_url or not self._api_key:
            raise ChatProviderUnavailable(code="MODEL_NOT_CONFIGURED", retryable=False)

        system_parts = [self._prompts.get(PromptName.CHAT_SYSTEM)]
        if memory_context:
            system_parts.append("## Bộ nhớ có cấu trúc của cuộc hội thoại\n" + memory_context)
        if guidance:
            system_parts.append(self._prompts.get(PromptName.TURN_GUIDANCE).format(guidance=guidance))
        if knowledge_context:
            system_parts.append(self._prompts.get(PromptName.GROUNDING).format(knowledge_context=knowledge_context))

        started_at = perf_counter()
        usage = None
        status = "error"
        try:
            async with AsyncOpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=0,
            ) as client:
                stream = await client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {
                            "role": "system",
                            "content": "\n\n".join(system_parts),
                        },
                        *[
                            {"role": role, "content": content}
                            for role, content in history[-20:]
                            if role in {"user", "assistant"}
                        ],
                        {"role": "user", "content": text},
                    ],
                    max_tokens=self._max_tokens,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                async for chunk in stream:
                    if chunk.usage is not None:
                        usage = chunk.usage
                    if not chunk.choices:
                        continue
                    content = chunk.choices[0].delta.content
                    if isinstance(content, str) and content:
                        yield content
                status = "success" if usage is not None else "usage_unavailable"
        except APIError as exc:
            raise translate_provider_error(exc) from exc
        finally:
            log_usage(
                task="chat", model=self._model, started_at=started_at, usage=usage,
                status=status,
            )
