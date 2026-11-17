import logging
from time import perf_counter
from typing import Any

from openai.types.completion_usage import CompletionUsage

logger = logging.getLogger(__name__)


def log_usage(
    *, task: str, model: str, started_at: float, usage: CompletionUsage | None, status: str,
) -> None:
    logger.info(
        "LLM request usage (task=%s model=%s duration_ms=%d prompt_tokens=%s "
        "completion_tokens=%s total_tokens=%s cost=%s status=%s)",
        task,
        model,
        int((perf_counter() - started_at) * 1_000),
        getattr(usage, "prompt_tokens", None) if usage is not None else "unknown",
        getattr(usage, "completion_tokens", None) if usage is not None else "unknown",
        getattr(usage, "total_tokens", None) if usage is not None else "unknown",
        getattr(usage, "cost", "unknown") if usage is not None else "unknown",
        status,
    )
