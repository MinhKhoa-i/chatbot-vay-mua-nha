import asyncio
import logging
from collections.abc import AsyncIterator

from app.application.services.chat_response_policy import ChatResponsePolicy
from app.application.services.request_fingerprint import chat_request_fingerprint
from app.application.services.retrieval_query import RetrievalQueryBuilder
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.knowledge_evidence import GroundedContext
from app.domain.entities.chat_request import ChatEvent, ChatRequest, ChatSnapshot, ChatSnapshotUpdate, ChatTurnError
from app.domain.errors import ChatError, RetrievalError, UnexpectedChatError
from app.domain.ports.chat_completion import ChatCompletionPort, ChatProviderUnavailable
from app.domain.ports.chat_turn_repository import ChatTurnRepository
from app.domain.ports.knowledge_retrieval import KnowledgeRetriever
from app.domain.ports.prompt_catalog import PromptCatalog
from app.domain.services.chat_intent_classifier import ChatIntentClassifier

logger = logging.getLogger(__name__)


class StreamChatUseCase:
    """Coordinates turns; technical failures propagate to the presentation boundary."""

    def __init__(
        self,
        completion: ChatCompletionPort,
        repository: ChatTurnRepository,
        *,
        prompts: PromptCatalog,
        retrieval: KnowledgeRetriever | None = None,
        classifier: ChatIntentClassifier | None = None,
        response_policy: ChatResponsePolicy | None = None,
    ) -> None:
        self._completion = completion
        self._repository = repository
        self._classifier = classifier or ChatIntentClassifier()
        self._query_builder = RetrievalQueryBuilder(self._classifier, prompts)
        self._retrieval = retrieval
        self._response_policy = response_policy or ChatResponsePolicy(prompts)

    async def execute(self, request: ChatRequest) -> AsyncIterator[ChatEvent]:
        snapshot = None
        stage = "claim"
        try:
            request_hash = chat_request_fingerprint(
                request.conversation_id, request.text, request.expected_version
            )
            claim = await self._repository.claim(request, request_hash)
            if claim.kind == "replay":
                body = claim.response_body or {}
                if claim.response_status and claim.response_status < 300:
                    yield ChatEvent("replay", body)
                else:
                    yield ChatEvent("error", body)
                return
            if claim.kind != "claimed" or claim.snapshot is None:
                data = {"code": claim.error_code or "STATE_UNAVAILABLE", "retryable": claim.kind in {"processing", "busy", "retry"}}
                if claim.retry_after is not None:
                    data["retry_after"] = claim.retry_after
                yield ChatEvent("error", data)
                return

            snapshot = claim.snapshot
            stage = "classification"
            intent = self._classifier.classify(request.text)
            stage = "retrieval"
            grounded = await self._retrieve(intent, request.text, snapshot.history)
            stage = "prompt"
            deterministic = self._response_policy.deterministic_reply(intent, request.text, grounded)
            answer_parts: list[str] = []
            if deterministic is not None:
                answer_parts.append(deterministic)
                yield ChatEvent("delta", {"text": deterministic})
            else:
                guidance = self._response_policy.retrieval_guidance
                stage = "model"
                try:
                    async with asyncio.timeout(45):
                        async for fragment in self._completion.stream_reply(
                            request.text, history=snapshot.history, guidance=guidance,
                            knowledge_context=grounded.prompt_context,
                        ):
                            answer_parts.append(fragment)
                            yield ChatEvent("delta", {"text": fragment})
                except TimeoutError as exc:
                    raise ChatProviderUnavailable(code="MODEL_TIMEOUT") from exc
            answer = "".join(answer_parts)
            if grounded.citations and deterministic is None:
                citation_footer = "\n\nNguồn tham khảo: " + "; ".join(grounded.citations)
                answer += citation_footer
                yield ChatEvent("delta", {"text": citation_footer})
            stage = "commit"
            commit = await self._repository.commit(
                request, request_id=snapshot.request_id, lease_token=snapshot.lease_token,
                snapshot_version=snapshot.conversation_version, answer=answer,
                state_update=ChatSnapshotUpdate(intent=intent),
            )
            if commit.response_status >= 400:
                yield ChatEvent("error", {"code": commit.error_code or "REQUEST_FAILED", "retryable": commit.retryable})
            else:
                yield ChatEvent("done", commit.response_body)
        except ChatTurnError:
            # Lease/conflict decisions belong to the repository; never overwrite them.
            raise
        except ChatError as exc:
            if snapshot is not None:
                await self._record_failure(request, snapshot, exc)
            raise
        except Exception as exc:
            error = UnexpectedChatError(stage=stage)
            if snapshot is not None:
                await self._record_failure(request, snapshot, error)
            raise error from exc

    async def _record_failure(self, request: ChatRequest, snapshot: ChatSnapshot, error: ChatError) -> None:
        try:
            await self._repository.fail(
                request, request_id=snapshot.request_id, lease_token=snapshot.lease_token,
                error_code=error.code, response_status=error.status_code, retryable=error.retryable,
            )
        except Exception:
            # A secondary persistence error must not replace the original failure.
            logger.exception("Failed to record chat failure (original_code=%s)", error.code)

    async def _retrieve(
        self, intent: ChatIntent, text: str, history: tuple[tuple[str, str], ...]
    ) -> GroundedContext:
        if intent == ChatIntent.GENERAL:
            return GroundedContext((), "", ())
        if self._retrieval is None:
            raise RetrievalError("RETRIEVAL_NOT_CONFIGURED", retryable=False)
        # Prompt errors must not be mislabeled as a search failure.
        query = self._query_builder.build(text, history)
        try:
            async with asyncio.timeout(15):
                return await self._retrieval.retrieve(query)
        except ChatError:
            raise
        except TimeoutError as exc:
            raise RetrievalError("RETRIEVAL_TIMEOUT") from exc
        except Exception as exc:
            raise RetrievalError() from exc
