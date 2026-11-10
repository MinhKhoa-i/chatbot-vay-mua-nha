import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

from intent_stubs import StubIntentClassifier

from app.application.use_cases.stream_chat import StreamChatUseCase
from app.domain.entities.chat_orchestration import ChatIntent
from app.domain.entities.chat_request import ChatClaim, ChatCommit, ChatRequest, ChatSnapshot
from app.domain.entities.knowledge_evidence import GroundedContext, KnowledgeEvidence
from app.domain.ports.chat_completion import ChatCompletionPort
from app.domain.ports.chat_turn_repository import ChatTurnRepository
from app.infrastructure.prompts.loader import get_prompt_catalog




class FakeCompletion(ChatCompletionPort):
    def __init__(self) -> None:
        self.calls = 0
        self.received_history = ()

    async def stream_reply(self, text: str, *, history=(), guidance="", knowledge_context="") -> AsyncIterator[str]:
        self.calls += 1
        self.received_history = history
        yield "answer"


class FakeRepository(ChatTurnRepository):
    def __init__(self) -> None:
        self.claim_result = ChatClaim("claimed", ChatSnapshot(0, (), uuid4(), uuid4()))
        self.commits = 0
        self.commit_error = None

    async def claim(self, request: ChatRequest, request_hash: str) -> ChatClaim:
        return self.claim_result

    async def commit(self, request: ChatRequest, *, request_id, lease_token, snapshot_version, answer, state_update=None, estimate=None) -> ChatCommit:
        self.commits += 1
        if self.commit_error:
            return ChatCommit({}, 409, None, None, snapshot_version, error_code=self.commit_error)
        return ChatCommit({"reply": answer}, 200, uuid4(), uuid4(), 1)

    async def fail(self, request: ChatRequest, *, request_id, lease_token, error_code, response_status, retryable) -> bool:
        return True


def test_completed_retry_replays_without_calling_provider_or_committing_again():
    async def run():
        completion = FakeCompletion()
        repository = FakeRepository()
        repository.claim_result = ChatClaim(
            "replay", response_body={"reply": "saved answer", "conversation_version": 1}, response_status=200,
        )
        use_case = StreamChatUseCase(completion, repository, prompts=get_prompt_catalog(), classifier=StubIntentClassifier(ChatIntent.GENERAL))
        request = ChatRequest(uuid4(), uuid4(), "hello", None)

        events = [event async for event in use_case.execute(request)]

        assert [(event.event, event.data) for event in events] == [
            ("replay", {"reply": "saved answer", "conversation_version": 1, "estimate": None}),
        ]
        assert completion.calls == 0
        assert repository.commits == 0

    asyncio.run(run())


def test_replay_bypasses_classifier_and_retrieval():
    class MustNotRun:
        async def classify(self, text, *, history=()):
            raise AssertionError("classification ran on replay")

        async def retrieve(self, text):
            raise AssertionError("retrieval ran on replay")

    repository = FakeRepository()
    repository.claim_result = ChatClaim("replay", response_body={"reply": "old answer"}, response_status=200)
    completion = FakeCompletion()
    use_case = StreamChatUseCase(completion, repository, prompts=get_prompt_catalog(), classifier=MustNotRun(), retrieval=MustNotRun())

    async def run():
        return [event async for event in use_case.execute(ChatRequest(uuid4(), uuid4(), "Hồ sơ?", None))]

    events = asyncio.run(run())
    assert [event.event for event in events] == ["replay"]
    assert events[0].data["estimate"] is None
    assert completion.calls == repository.commits == 0


def test_commit_conflict_never_emits_done():
    repository = FakeRepository()
    repository.commit_error = "VERSION_CONFLICT"

    async def run():
        use_case = StreamChatUseCase(FakeCompletion(), repository, prompts=get_prompt_catalog(), classifier=StubIntentClassifier(ChatIntent.GENERAL))
        return [event async for event in use_case.execute(ChatRequest(uuid4(), uuid4(), "Xin chào", 0))]

    events = asyncio.run(run())
    assert [event.event for event in events] == ["delta", "error"]
    assert events[-1].data["code"] == "VERSION_CONFLICT"
    assert repository.commits == 1


def test_fresh_claim_streams_then_commits_before_done():
    async def run():
        completion = FakeCompletion()
        repository = FakeRepository()
        repository.claim_result = ChatClaim(
            "claimed",
            ChatSnapshot(0, (("user", "previous question"), ("assistant", "previous answer")), uuid4(), uuid4()),
        )
        class Retrieval:
            async def retrieve(self, text):
                item = KnowledgeEvidence(
                    chunk_id=uuid4(), document_id=uuid4(), title="Hồ sơ", source_url=None,
                    body="Cần giấy tờ.", score=0.9,
                )
                return GroundedContext((item,), "Cần giấy tờ.", ())

        classifier = StubIntentClassifier()
        use_case = StreamChatUseCase(
            completion, repository, prompts=get_prompt_catalog(),
            classifier=classifier, retrieval=Retrieval(),
        )
        events = [event async for event in use_case.execute(
            ChatRequest(uuid4(), uuid4(), "Hồ sơ vay cần gì?", 0)
        )]
        assert classifier.calls == [("Hồ sơ vay cần gì?", repository.claim_result.snapshot.history)]
        assert [event.event for event in events] == ["delta", "done"]
        assert completion.calls == 1
        assert completion.received_history == (("user", "previous question"), ("assistant", "previous answer"))
        assert repository.commits == 1

    asyncio.run(run())
