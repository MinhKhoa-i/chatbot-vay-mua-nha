from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.chat_request import (
    ChatClaim,
    ChatCommit,
    ChatRequest,
    ChatSnapshot,
    ChatSnapshotUpdate,
    ChatTurnError,
)
from app.domain.entities.conversation import Conversation, ConversationMessage
from app.domain.entities.loan_estimate import LoanEstimateResult
from app.domain.ports.chat_turn_repository import ChatTurnRepository
from app.infrastructure.db.chat_error_boundary import chat_repository_errors
from app.infrastructure.db.estimate_state_codec import decode_estimate_session, encode_estimate_session
from app.infrastructure.db.models import (
    ConversationMessageModel,
    ConversationModel,
    ConversationProfileModel,
    MessageRequestModel,
)
from app.infrastructure.security.payload_cipher import PayloadCipher, PayloadCipherError


class PostgresConversationRepository(ChatTurnRepository):
    def __init__(self, session_factory: async_sessionmaker, cipher: PayloadCipher) -> None:
        self._session_factory = session_factory
        self._cipher = cipher

    @staticmethod
    def _initial_state() -> tuple[dict, dict]:
        checkpoint = {
            "schema_version": 1,
            "conversation_version": 0,
            "profile_revision": 0,
            "current_stage": "NEW",
            "active_intents": [],
            "pending_tasks": [],
            "pending_question": None,
        }
        profile = {
            "schema_version": 1,
            "profile_revision": 0,
            "slots": {},
        }
        return checkpoint, profile

    def _new_conversation_records(
        self, conversation_id: UUID
    ) -> tuple[ConversationModel, ConversationProfileModel, dict]:
        checkpoint, profile = self._initial_state()
        checkpoint_blob = self._cipher.encrypt_json(
            checkpoint, table="conversations", column="checkpoint_ciphertext", resource_id=conversation_id
        )
        profile_blob = self._cipher.encrypt_json(
            profile, table="conversation_profiles", column="slots_ciphertext", resource_id=conversation_id
        )
        return (
            ConversationModel(
                id=conversation_id,
                checkpoint_ciphertext=checkpoint_blob,
                expires_at=func.now() + timedelta(days=30),
            ),
            ConversationProfileModel(conversation_id=conversation_id, slots_ciphertext=profile_blob),
            checkpoint,
        )

    async def create(self) -> Conversation:
        conversation_id = uuid4()
        row, profile_row, checkpoint = self._new_conversation_records(conversation_id)
        async with self._session_factory() as session:
            async with session.begin():
                session.add(row)
                session.add(profile_row)
                await session.flush()
                await session.refresh(row)
                return Conversation(
                    id=row.id,
                    status=row.status,
                    version=row.version,
                    profile_revision=0,
                    checkpoint=checkpoint,
                    profile_summary={"confirmed": False},
                    created_at=row.created_at,
                    expires_at=row.expires_at,
                )

    async def get(self, conversation_id: UUID) -> Conversation | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ConversationModel, ConversationProfileModel)
                .join(ConversationProfileModel, ConversationProfileModel.conversation_id == ConversationModel.id)
                .where(
                    ConversationModel.id == conversation_id,
                    ConversationModel.status.in_(("active", "closed")),
                    ConversationModel.expires_at > func.now(),
                )
            )
            pair = result.one_or_none()
            if pair is None:
                return None
            row, profile_row = pair
            if row.checkpoint_ciphertext is None:
                raise PayloadCipherError("conversation checkpoint missing")
            checkpoint = self._cipher.decrypt_json(
                row.checkpoint_ciphertext,
                table="conversations",
                column="checkpoint_ciphertext",
                resource_id=conversation_id,
            )
            profile = self._cipher.decrypt_json(
                profile_row.slots_ciphertext,
                table="conversation_profiles",
                column="slots_ciphertext",
                resource_id=conversation_id,
            )
            if (
                checkpoint.get("conversation_version") != row.version
                or checkpoint.get("profile_revision") != profile_row.revision
                or profile.get("profile_revision") != profile_row.revision
            ):
                raise PayloadCipherError("conversation state version mismatch")
            return Conversation(
                id=row.id,
                status=row.status,
                version=row.version,
                profile_revision=profile_row.revision,
                checkpoint=checkpoint,
                profile_summary=self._profile_projection(profile),
                created_at=row.created_at,
                expires_at=row.expires_at,
            )

    @staticmethod
    def _profile_projection(profile: dict) -> dict:
        slots = profile.get("slots", {})
        if not isinstance(slots, dict):
            raise PayloadCipherError("profile slots are invalid")
        # Expose only typed slot values/status; never expose provenance or encrypted internals.
        projection: dict = {}
        for name, slot in slots.items():
            if not isinstance(name, str) or not isinstance(slot, dict):
                raise PayloadCipherError("profile slot is invalid")
            projection[name] = {"value": slot.get("value"), "status": slot.get("status", "unknown")}
        projection["confirmed"] = profile.get("confirmed_revision") == profile.get("profile_revision") and profile.get("confirmed_snapshot_hash") is not None
        return projection

    async def list_messages(
        self, conversation_id: UUID, *, before: int | None, limit: int
    ) -> tuple[list[ConversationMessage], int | None] | None:
        async with self._session_factory() as session:
            conversation_exists = await session.scalar(
                select(ConversationModel.id).where(
                    ConversationModel.id == conversation_id,
                    ConversationModel.status.in_(("active", "closed")),
                    ConversationModel.expires_at > func.now(),
                )
            )
            if conversation_exists is None:
                return None
            stmt = select(ConversationMessageModel).where(
                ConversationMessageModel.conversation_id == conversation_id
            )
            if before is not None:
                stmt = stmt.where(ConversationMessageModel.seq < before)
            rows = list(
                (
                    await session.scalars(
                        stmt.order_by(ConversationMessageModel.seq.desc()).limit(limit + 1)
                    )
                ).all()
            )
            has_more = len(rows) > limit
            page = list(reversed(rows[:limit]))
            messages: list[ConversationMessage] = []
            for row in page:
                payload = self._cipher.decrypt_json(
                    row.content_ciphertext,
                    table="messages",
                    column="content_ciphertext",
                    resource_id=row.id,
                )
                content = payload.get("content")
                if not isinstance(content, str) or row.role not in {"user", "assistant"}:
                    raise PayloadCipherError("message payload is invalid")
                messages.append(ConversationMessage(row.id, row.role, content, row.seq, row.created_at))
            next_cursor = page[0].seq if has_more and page else None
            return messages, next_cursor

    @staticmethod
    def _response_envelope(status_code: int, body: dict, error_code: str | None = None) -> dict:
        return {"schema_version": 1, "status": status_code, "body": body, "error_code": error_code}

    def _encrypt_request_response(self, request_id: UUID, status_code: int, body: dict, error_code: str | None = None) -> bytes:
        return self._cipher.encrypt_json(
            self._response_envelope(status_code, body, error_code),
            table="message_requests", column="response_ciphertext", resource_id=request_id,
        )

    def _decrypt_request_response(self, row: MessageRequestModel) -> dict:
        if row.response_ciphertext is None or row.response_status is None:
            raise PayloadCipherError("cached request response is missing")
        return self._cipher.decrypt_json(
            row.response_ciphertext,
            table="message_requests", column="response_ciphertext", resource_id=row.id,
        )

    async def _insert_conversation_if_absent(self, session: AsyncSession, conversation_id: UUID) -> bool:
        conversation_row, profile_row, _ = self._new_conversation_records(conversation_id)
        inserted_id = await session.scalar(
            insert(ConversationModel)
            .values(
                id=conversation_row.id,
                checkpoint_ciphertext=conversation_row.checkpoint_ciphertext,
                expires_at=conversation_row.expires_at,
            )
            .on_conflict_do_nothing(index_elements=[ConversationModel.id])
            .returning(ConversationModel.id)
        )
        if inserted_id is None:
            return False
        session.add(profile_row)
        await session.flush()
        return True

    @chat_repository_errors("claim")
    async def claim(self, request: ChatRequest, request_hash: str) -> ChatClaim:
        async with self._session_factory() as session:
            async with session.begin():
                conversation_query = select(ConversationModel).where(
                    ConversationModel.id == request.conversation_id
                ).with_for_update()
                conversation = await session.scalar(conversation_query)
                if conversation is None:
                    await self._insert_conversation_if_absent(session, request.conversation_id)
                    conversation = await session.scalar(conversation_query)
                if conversation is None or conversation.status == "deleted":
                    return ChatClaim("error", error_code="CONVERSATION_NOT_FOUND")
                db_now = await session.scalar(select(func.now()))
                if conversation.expires_at <= db_now:
                    return ChatClaim("error", error_code="CONVERSATION_NOT_FOUND")

                ledger = await session.scalar(
                    select(MessageRequestModel).where(
                        MessageRequestModel.conversation_id == request.conversation_id,
                        MessageRequestModel.client_request_id == request.client_request_id,
                    ).with_for_update()
                )
                if ledger is not None:
                    if ledger.operation != "send_message" or ledger.request_hash != request_hash:
                        return ChatClaim("error", error_code="IDEMPOTENCY_CONFLICT")
                    if ledger.status == "completed" or (ledger.status == "failed" and not ledger.retryable):
                        envelope = self._decrypt_request_response(ledger)
                        return ChatClaim(
                            "replay", response_body=envelope["body"], response_status=envelope["status"],
                            error_code=envelope.get("error_code"),
                        )
                    if ledger.status == "processing":
                        if ledger.lease_expires_at is not None and ledger.lease_expires_at > db_now:
                            return ChatClaim("processing", error_code="MESSAGE_PROCESSING", retry_after=1)
                        await self._fence_expired_locked(session, conversation, ledger)
                        ledger = await session.scalar(
                            select(MessageRequestModel).where(
                                MessageRequestModel.conversation_id == request.conversation_id,
                                MessageRequestModel.client_request_id == request.client_request_id,
                            ).with_for_update()
                        )
                    if ledger is not None and ledger.status == "failed" and ledger.retryable:
                        db_now = await session.scalar(select(func.now()))
                        if ledger.next_retry_at is not None and ledger.next_retry_at > db_now:
                            return ChatClaim("retry", error_code=ledger.error_code, retry_after=max(1, int((ledger.next_retry_at - db_now).total_seconds())))
                        if ledger.attempts >= ledger.max_attempts:
                            return ChatClaim("error", error_code="REQUEST_RETRY_EXHAUSTED")
                        if conversation.version != ledger.snapshot_version:
                            self._set_terminal_error(ledger, "VERSION_CONFLICT", 409)
                            return ChatClaim("error", error_code="VERSION_CONFLICT")
                else:
                    ledger = None

                if conversation.status != "active":
                    return ChatClaim("error", error_code="CONVERSATION_CLOSED")
                if conversation.active_request_id is not None:
                    active = await session.scalar(
                        select(MessageRequestModel).where(MessageRequestModel.id == conversation.active_request_id).with_for_update()
                    )
                    if active is not None and active.status == "processing":
                        db_now = await session.scalar(select(func.now()))
                        if active.lease_expires_at is not None and active.lease_expires_at > db_now:
                            return ChatClaim("busy", error_code="CONVERSATION_BUSY", retry_after=1)
                        await self._fence_expired_locked(session, conversation, active)
                    elif active is None:
                        conversation.active_request_id = None

                if ledger is None:
                    if request.expected_version is not None and request.expected_version != conversation.version:
                        return ChatClaim("error", error_code="VERSION_CONFLICT")
                    row_id = uuid4()
                    token = uuid4()
                    ledger = MessageRequestModel(
                        id=row_id, conversation_id=request.conversation_id,
                        client_request_id=request.client_request_id, operation="send_message",
                        request_hash=request_hash, status="processing", snapshot_version=conversation.version,
                        lease_token=token, lease_expires_at=db_now + timedelta(seconds=90),
                        attempts=1, max_attempts=3,
                    )
                    session.add(ledger)
                    conversation.active_request_id = row_id
                else:
                    if request.expected_version is not None and request.expected_version != ledger.snapshot_version:
                        self._set_terminal_error(ledger, "VERSION_CONFLICT", 409)
                        return ChatClaim("error", error_code="VERSION_CONFLICT")
                    token = uuid4()
                    ledger.status = "processing"
                    ledger.lease_token = token
                    ledger.lease_expires_at = db_now + timedelta(seconds=90)
                    ledger.attempts += 1
                    ledger.retryable = False
                    ledger.next_retry_at = None
                    ledger.response_ciphertext = None
                    ledger.response_status = None
                    ledger.error_code = None
                    ledger.updated_at = func.now()
                    conversation.active_request_id = ledger.id

                profile_row = await session.scalar(
                    select(ConversationProfileModel).where(
                        ConversationProfileModel.conversation_id == request.conversation_id
                    ).with_for_update()
                )
                if conversation.checkpoint_ciphertext is None or profile_row is None:
                    raise PayloadCipherError("conversation state is unavailable")
                checkpoint = self._cipher.decrypt_json(
                    conversation.checkpoint_ciphertext, table="conversations",
                    column="checkpoint_ciphertext", resource_id=request.conversation_id,
                )
                profile = self._cipher.decrypt_json(
                    profile_row.slots_ciphertext, table="conversation_profiles",
                    column="slots_ciphertext", resource_id=request.conversation_id,
                )
                if (
                    checkpoint.get("conversation_version") != conversation.version
                    or checkpoint.get("profile_revision") != profile_row.revision
                    or profile.get("profile_revision") != profile_row.revision
                ):
                    raise PayloadCipherError("conversation state version mismatch")
                history_rows = list((await session.scalars(
                    select(ConversationMessageModel).where(
                        ConversationMessageModel.conversation_id == request.conversation_id
                    ).order_by(ConversationMessageModel.seq)
                )).all())
                history: list[tuple[str, str]] = []
                for item in history_rows:
                    payload = self._cipher.decrypt_json(
                        item.content_ciphertext, table="messages", column="content_ciphertext", resource_id=item.id,
                    )
                    history.append((item.role, payload["content"]))
                return ChatClaim(
                    "claimed",
                    ChatSnapshot(
                        conversation.version,
                        tuple(history),
                        token,
                        ledger.id,
                        estimate_session=decode_estimate_session(profile),
                    ),
                )

    async def _fence_expired_locked(self, session, conversation: ConversationModel, ledger: MessageRequestModel) -> None:
        if ledger.status != "processing" or ledger.lease_token is None:
            return
        db_now = await session.scalar(select(func.now()))
        if ledger.lease_expires_at is None or ledger.lease_expires_at > db_now:
            return
        retryable = ledger.attempts < ledger.max_attempts
        code = "REQUEST_INTERRUPTED" if retryable else "REQUEST_RETRY_EXHAUSTED"
        status_code = 503
        ledger.status = "failed"
        ledger.lease_token = None
        ledger.lease_expires_at = None
        ledger.retryable = retryable
        ledger.next_retry_at = func.now() + timedelta(seconds=1 if ledger.attempts == 1 else 2) if retryable else None
        ledger.error_code = code
        ledger.response_status = status_code
        ledger.response_ciphertext = self._encrypt_request_response(ledger.id, status_code, {"code": code, "retryable": retryable}, code)
        ledger.updated_at = func.now()
        if conversation.active_request_id == ledger.id:
            conversation.active_request_id = None

    def _set_terminal_error(self, ledger: MessageRequestModel, error_code: str, status_code: int) -> None:
        ledger.status = "failed"
        ledger.lease_token = None
        ledger.lease_expires_at = None
        ledger.retryable = False
        ledger.next_retry_at = None
        ledger.error_code = error_code
        ledger.response_status = status_code
        ledger.response_ciphertext = self._encrypt_request_response(
            ledger.id, status_code, {"code": error_code, "retryable": False}, error_code,
        )
        ledger.updated_at = func.now()

    @chat_repository_errors("commit")
    async def commit(
        self, request: ChatRequest, *, request_id: UUID, lease_token: UUID,
        snapshot_version: int, answer: str, state_update: ChatSnapshotUpdate | None = None,
        estimate: LoanEstimateResult | None = None,
    ) -> ChatCommit:
        async with self._session_factory() as session:
            async with session.begin():
                conversation = await session.scalar(
                    select(ConversationModel).where(ConversationModel.id == request.conversation_id).with_for_update()
                )
                if conversation is None or conversation.status != "active":
                    raise ChatTurnError("CONVERSATION_NOT_FOUND")
                db_now = await session.scalar(select(func.now()))
                if conversation.expires_at <= db_now:
                    raise ChatTurnError("CONVERSATION_NOT_FOUND")
                ledger = await session.scalar(
                    select(MessageRequestModel).where(MessageRequestModel.id == request_id).with_for_update()
                )
                if ledger is None or ledger.status != "processing" or ledger.lease_token != lease_token or conversation.active_request_id != request_id:
                    raise ChatTurnError("REQUEST_LEASE_LOST", retryable=True)
                db_now = await session.scalar(select(func.now()))
                if ledger.lease_expires_at is None or ledger.lease_expires_at <= db_now:
                    await self._fence_expired_locked(session, conversation, ledger)
                    await session.flush()
                    return ChatCommit(
                        {"code": "REQUEST_LEASE_LOST", "retryable": True},
                        409,
                        None,
                        None,
                        conversation.version,
                        "REQUEST_LEASE_LOST",
                        True,
                    )
                if conversation.version != snapshot_version or ledger.snapshot_version != snapshot_version:
                    body = {"code": "VERSION_CONFLICT", "retryable": False}
                    self._set_terminal_error(ledger, "VERSION_CONFLICT", 409)
                    conversation.active_request_id = None
                    await session.flush()
                    return ChatCommit(body, 409, None, None, conversation.version, "VERSION_CONFLICT", False)

                user_id, assistant_id = uuid4(), uuid4()
                max_seq = await session.scalar(select(func.coalesce(func.max(ConversationMessageModel.seq), 0)).where(
                    ConversationMessageModel.conversation_id == request.conversation_id
                ))
                next_version = conversation.version + 1
                now = func.now()
                for message_id, role, content, seq in (
                    (user_id, "user", request.text, max_seq + 1),
                    (assistant_id, "assistant", answer, max_seq + 2),
                ):
                    session.add(ConversationMessageModel(
                        id=message_id, conversation_id=request.conversation_id, role=role,
                        content_ciphertext=self._cipher.encrypt_json(
                            {"content": content}, table="messages", column="content_ciphertext", resource_id=message_id,
                        ), seq=seq,
                    ))
                checkpoint = self._cipher.decrypt_json(
                    conversation.checkpoint_ciphertext, table="conversations",
                    column="checkpoint_ciphertext", resource_id=request.conversation_id,
                )
                profile_row = await session.scalar(
                    select(ConversationProfileModel)
                    .where(ConversationProfileModel.conversation_id == request.conversation_id)
                    .with_for_update()
                )
                if profile_row is None:
                    raise PayloadCipherError("conversation profile is unavailable")
                profile_payload = self._cipher.decrypt_json(
                    profile_row.slots_ciphertext, table="conversation_profiles",
                    column="slots_ciphertext", resource_id=request.conversation_id,
                )
                if (
                    checkpoint.get("conversation_version") != snapshot_version
                    or checkpoint.get("profile_revision") != profile_row.revision
                    or profile_payload.get("profile_revision") != profile_row.revision
                ):
                    raise PayloadCipherError("conversation state version mismatch")
                checkpoint["conversation_version"] = next_version
                if state_update is not None:
                    if state_update.estimate_session is not None:
                        profile_payload["estimate_session"] = encode_estimate_session(state_update.estimate_session)
                        profile_row.revision += 1
                        profile_payload["profile_revision"] = profile_row.revision
                        profile_row.slots_ciphertext = self._cipher.encrypt_json(
                            profile_payload, table="conversation_profiles", column="slots_ciphertext",
                            resource_id=request.conversation_id,
                        )
                    # New estimate state is stored only in the encrypted profile.
                    checkpoint.update(
                        current_stage="ANSWERING",
                        active_intents=[state_update.intent.value],
                        pending_tasks=[],
                        pending_question=None,
                    )
                    checkpoint["profile_revision"] = profile_row.revision
                conversation.version = next_version
                conversation.checkpoint_ciphertext = self._cipher.encrypt_json(
                    checkpoint, table="conversations", column="checkpoint_ciphertext", resource_id=request.conversation_id,
                )
                conversation.active_request_id = None
                conversation.last_active_at = now
                conversation.expires_at = now + timedelta(days=30)
                conversation.updated_at = now
                body = {
                    "conversation_id": str(request.conversation_id), "client_request_id": str(request.client_request_id),
                    "conversation_version": next_version, "user_message_id": str(user_id),
                    "assistant_message_id": str(assistant_id), "reply": answer,
                    "estimate": self._serialize_estimate(estimate),
                }
                ledger.status = "completed"
                ledger.lease_token = None
                ledger.lease_expires_at = None
                ledger.retryable = False
                ledger.next_retry_at = None
                ledger.error_code = None
                ledger.response_status = 200
                ledger.response_ciphertext = self._encrypt_request_response(request_id, 200, body)
                ledger.updated_at = now
                return ChatCommit(body, 200, user_id, assistant_id, next_version)

    @staticmethod
    def _serialize_estimate(estimate: LoanEstimateResult | None) -> dict | None:
        if estimate is None:
            return None
        return {
            "input": {
                "amount": estimate.request.amount,
                "years": estimate.request.years,
                "rate": str(estimate.request.rate),
            },
            "monthly_payment": estimate.monthly_payment,
            "total_interest": estimate.total_interest,
            "updated_at": estimate.updated_at,
        }

    @chat_repository_errors("fail")
    async def fail(
        self, request: ChatRequest, *, request_id: UUID, lease_token: UUID,
        error_code: str, response_status: int, retryable: bool,
    ) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                conversation = await session.scalar(
                    select(ConversationModel).where(ConversationModel.id == request.conversation_id).with_for_update()
                )
                if conversation is None or conversation.status != "active":
                    return False
                db_now = await session.scalar(select(func.now()))
                if conversation.expires_at <= db_now:
                    return False
                ledger = await session.scalar(select(MessageRequestModel).where(
                    MessageRequestModel.id == request_id
                ).with_for_update())
                if ledger is None or ledger.status != "processing" or ledger.lease_token != lease_token or conversation.active_request_id != request_id:
                    return False
                db_now = await session.scalar(select(func.now()))
                if ledger.lease_expires_at is None or ledger.lease_expires_at <= db_now:
                    await self._fence_expired_locked(session, conversation, ledger)
                    return False
                final_retryable = retryable and ledger.attempts < ledger.max_attempts
                code = error_code if final_retryable or not retryable else "REQUEST_RETRY_EXHAUSTED"
                status_code = response_status
                body = {"code": code, "retryable": final_retryable}
                ledger.status = "failed"
                ledger.lease_token = None
                ledger.lease_expires_at = None
                ledger.retryable = final_retryable
                ledger.next_retry_at = func.now() + timedelta(seconds=1 if ledger.attempts == 1 else 2) if final_retryable else None
                ledger.error_code = code
                ledger.response_status = status_code
                ledger.response_ciphertext = self._encrypt_request_response(request_id, status_code, body, code)
                ledger.updated_at = func.now()
                conversation.active_request_id = None
                return True

    async def delete(self, conversation_id: UUID) -> bool:
        async with self._session_factory() as session:
            async with session.begin():
                row = await session.scalar(
                    select(ConversationModel)
                    .where(
                        ConversationModel.id == conversation_id,
                        ConversationModel.status.in_(("active", "closed")),
                        ConversationModel.expires_at > func.now(),
                    )
                    .with_for_update()
                )
                if row is None:
                    return False
                # Fencing by deleting request rows prevents later code from treating a stale lease as active.
                await session.execute(
                    delete(MessageRequestModel).where(MessageRequestModel.conversation_id == conversation_id)
                )
                await session.execute(
                    delete(ConversationMessageModel).where(ConversationMessageModel.conversation_id == conversation_id)
                )
                await session.execute(
                    delete(ConversationProfileModel).where(ConversationProfileModel.conversation_id == conversation_id)
                )
                row.status = "deleted"
                row.checkpoint_ciphertext = None
                row.active_request_id = None
                row.deleted_at = func.now()
                row.updated_at = func.now()
                return True
