from collections.abc import AsyncIterator

from openai import APIError, AsyncOpenAI


class ChatProviderUnavailable(RuntimeError):
    """Raised when the configured chat provider cannot complete a stream."""


class OpenAIChatAdapter:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 45.0,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds

    async def stream_reply(self, text: str) -> AsyncIterator[str]:
        if not self._base_url or not self._api_key:
            raise ChatProviderUnavailable("chat provider is not configured")

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
                            "content": (
                                "Bạn là trợ lý AI cung cấp thông tin tham khảo về vay mua nhà tại Việt Nam. "
                                "Trả lời bằng tiếng Việt, rõ ràng, lịch sự. Không phê duyệt khoản vay, không "
                                "cam kết lãi suất/điều kiện, không bịa dữ liệu ngân hàng hay nguồn. Không tự "
                                "tính số tiền trả nợ; nếu thiếu dữ liệu đã xác minh, hãy nêu rõ giới hạn và hỏi "
                                "thêm. Thông tin chỉ mang tính tham khảo; người dùng cần xác nhận trực tiếp "
                                "với ngân hàng trước quyết định."
                            ),
                        },
                        {"role": "user", "content": text},
                    ],
                    stream=True,
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    content = chunk.choices[0].delta.content
                    if isinstance(content, str) and content:
                        yield content
        except APIError as exc:
            raise ChatProviderUnavailable("chat provider unavailable or rejected request") from exc
