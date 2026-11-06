from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.entities.conversation import Conversation, ConversationMessage
from app.infrastructure.db.models import (
    ConversationMessageModel,
    ConversationModel,
    ConversationProfileModel,
    MessageRequestModel,
)
from app.infrastructure.security.payload_cipher import PayloadCipher, PayloadCipherError


class PostgresConversationRepository:
    def __init__(self, session_factory: async_sessionmaker, cipher: PayloadCipher) -> None:
        self._session_factory = session_factory
        self._cipher = cipher

    async def create(self) -> Conversation:
        conversation_id = uuid4()
        checkpoint = {
            "schema_version": 1,
            "conversation_version": 0,
            "profile_revision": 0,
            "current_stage": "NEW",
            "active_intents": [],
            "pending_tasks": [],
            "pending_question": None,
            "last_calculation_id": None,
            "last_recommendation_id": None,
            "summary": None,
            "summary_version": 0,
            "summary_through_seq": 0,
        }
        profile = {
            "schema_version": 1,
            "profile_revision": 0,
            "slots": {},
            "confirmed_revision": None,
            "confirmed_snapshot_hash": None,
            "confirmed_calculation_input": None,
            "confirmed_at": None,
        }
        checkpoint_blob = self._cipher.encrypt_json(
            checkpoint, table="conversations", column="checkpoint_ciphertext", resource_id=conversation_id
        )
        profile_blob = self._cipher.encrypt_json(
            profile, table="conversation_profiles", column="slots_ciphertext", resource_id=conversation_id
        )
        async with self._session_factory() as session:
            async with session.begin():
                row = ConversationModel(
                    id=conversation_id,
                    checkpoint_ciphertext=checkpoint_blob,
                    expires_at=func.now() + timedelta(days=30),
                )
                session.add(row)
                session.add(ConversationProfileModel(conversation_id=conversation_id, slots_ciphertext=profile_blob))
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
