import asyncio
import logging
import re
from collections.abc import AsyncIterator

from app.application.services.chat_response_policy import ChatResponsePolicy
from app.application.services.request_fingerprint import chat_request_fingerprint
from app.application.services.retrieval_query import RetrievalQueryBuilder
from app.application.use_cases.estimate_loan import EstimateLoanUseCase
from app.domain.ports.loan_calculator import LoanCalculationError
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.knowledge_evidence import GroundedContext
from app.domain.entities.chat_request import ChatEvent, ChatRequest, ChatSnapshot, ChatSnapshotUpdate, ChatTurnError
from app.domain.errors import ChatError, RetrievalError, UnexpectedChatError
from app.domain.ports.chat_completion import ChatCompletionPort, ChatProviderUnavailable
from app.domain.ports.chat_intent_classifier import ChatIntentClassifier, IntentClassificationError
from app.domain.ports.chat_turn_repository import ChatTurnRepository
from app.domain.ports.knowledge_retrieval import KnowledgeRetriever
from app.domain.ports.prompt_catalog import PromptCatalog

logger = logging.getLogger(__name__)
_CITATION_LABEL_PATTERN = re.compile(r"\[(\d+)\]")


def _cited_sources(answer: str, citations: tuple[str, ...]) -> tuple[str, ...]:
    """Return retrieved citations whose exact numeric labels appear in the answer."""
    cited_labels = set(_CITATION_LABEL_PATTERN.findall(answer))
    return tuple(
        citation for index, citation in enumerate(citations, start=1)
        if str(index) in cited_labels
    )


class StreamChatUseCase:
    """Coordinates turns; technical failures propagate to the presentation boundary."""

    def __init__(
        self,
        completion: ChatCompletionPort,
        repository: ChatTurnRepository,
        *,
        prompts: PromptCatalog,
        classifier: ChatIntentClassifier,
        retrieval: KnowledgeRetriever | None = None,
        response_policy: ChatResponsePolicy | None = None,
        estimate: EstimateLoanUseCase | None = None,
    ) -> None:
        self._estimate = estimate
        self._completion = completion
        self._repository = repository
        self._classifier = classifier
        self._query_builder = RetrievalQueryBuilder(prompts)
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
                    body.setdefault("estimate", None)
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
            estimate_turn = None
            if snapshot.estimate_session.active and self._estimate is not None:
                stage = "estimate"
                estimate_turn = await self._estimate.execute(request.text, snapshot.estimate_session)
            stage = "classification"
            try:
                if estimate_turn is not None and estimate_turn.handled:
                    intent = ChatIntent.ESTIMATE
                else:
                    async with asyncio.timeout(10):
                        intent = await self._classifier.classify(request.text, history=snapshot.history)
            except TimeoutError as exc:
                raise IntentClassificationError("CLASSIFICATION_TIMEOUT") from exc
            estimate_state = None
            estimate_result = None
            if intent == ChatIntent.ESTIMATE:
                stage = "estimate"
                if self._estimate is None:
                    raise LoanCalculationError("ESTIMATE_NOT_CONFIGURED", retryable=False)
                if estimate_turn is None:
                    estimate_turn = await self._estimate.execute(request.text, snapshot.estimate_session)
                if not estimate_turn.handled:
                    # An unrelated message must never authorize a calculator call.
                    intent = ChatIntent.RETRIEVAL
                else:
                    estimate_state = estimate_turn.session
                    estimate_result = estimate_turn.result
            if intent == ChatIntent.ESTIMATE:
                grounded = GroundedContext((), "", ())
                deterministic = estimate_turn.answer
            else:
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
            cited_sources = _cited_sources(answer, grounded.citations)
            if cited_sources and deterministic is None:
                citation_footer = "\n\nNguồn tham khảo: " + "; ".join(cited_sources)
                answer += citation_footer
                yield ChatEvent("delta", {"text": citation_footer})
            stage = "commit"
            commit = await self._repository.commit(
                request, request_id=snapshot.request_id, lease_token=snapshot.lease_token,
                snapshot_version=snapshot.conversation_version, answer=answer,
                state_update=ChatSnapshotUpdate(intent=intent, estimate_session=estimate_state),
                estimate=estimate_result,
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
