# Conversation API

Base path: `/api/v1`. All response bodies are `application/json`. `POST /conversations` creates a server-generated UUIDv4; for `POST /conversations/{conversation_id}/messages`, the client may instead provide a UUIDv4 in the path and the first valid message atomically creates that conversation if it does not exist. Conversation state, profile payloads, message content, and stored replay responses are encrypted with AES-256-GCM using the key configured by `DATA_ENCRYPTION_KEY_BASE64`.

## Create a conversation

`POST /conversations` with an empty JSON object `{}` returns `201`:

```json
{
  "conversation_id": "2dd4d22a-993d-4a2e-b544-91409ebfb17b",
  "conversation_version": 0,
  "profile_revision": 0,
  "created_at": "2026-11-06T10:00:00Z",
  "expires_at": "2026-12-06T10:00:00Z",
  "status": "active"
}
```

A fresh checkpoint and profile are created atomically. The initial expiration is 30 days from creation. Each successfully committed chat turn persists the user and assistant messages, updates the checkpoint/version and replay response atomically, and renews the expiration to 30 days from that commit. Failed or uncommitted turns do not appear in message history.

## Read a conversation

`GET /conversations/{conversation_id}` returns `200` with version, state, profile summary projection, and expiry. Unknown, deleted, or expired IDs return `404` with `CONVERSATION_NOT_FOUND`. State decryption/integrity failure returns `503 STATE_UNAVAILABLE` and is not silently replaced with empty state.

## List messages

`GET /conversations/{conversation_id}/messages?limit=50&before=<seq>` returns `200`:

```json
{
  "items": [
    {
      "message_id": "a5f9b498-40c5-4b7e-ab9b-39a045bef2cd",
      "role": "assistant",
      "content": "Xin chào! Tôi có thể giúp tìm hiểu về khoản vay mua nhà.",
      "seq": 2,
      "created_at": "2026-11-06T10:01:00Z"
    }
  ],
  "next_cursor": null
}
```

`limit` is 1–100 (default 50); `before` is an optional positive sequence number. Results are returned in chronological order. Use `next_cursor` as the next `before` value. No matching active conversation returns 404.

## Delete a conversation

`DELETE /conversations/{conversation_id}` returns `204` with no body. It tombstones the parent, clears its encrypted checkpoint, and removes messages, profile, and request-ledger rows in one transaction. A repeated delete, unknown ID, or expired ID returns `404`.

## Current implementation boundaries

The Alembic migrations establish conversations, profiles, encrypted messages, and the shared request ledger with database constraints. The conversation API implements create/read/list/delete, while the chat endpoint is integrated with the ledger and persists successfully committed turns as described above. The profile projection is intentionally limited; a general-purpose slot-filling workflow and complete missing-slot derivation are not implemented. The estimate flow keeps its own typed state. There is no authentication boundary beyond possession of the UUID, as scoped in `implement.md`; deploy only behind the intended trusted local API boundary.

`DATA_ENCRYPTION_KEY_BASE64` must decode to exactly 32 random bytes. Keep it outside version control and backups/config logs, and retain protected old key versions until encrypted data retention ends. Generate and provide the key through the operator's secret-management procedure before enabling these endpoints.
