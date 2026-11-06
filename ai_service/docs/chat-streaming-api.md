# Streaming chat API (implementation status)

The stream is exposed as `POST /api/v1/conversations/{conversation_id}/messages` and uses `text/event-stream` (SSE).

## Request

```json
{
  "client_request_id": "174ee389-e68c-4d55-a3c5-95e4f7669b40",
  "text": "Xin chào, tôi muốn tìm hiểu về vay mua nhà",
  "expected_version": 0
}
```

`client_request_id` must be UUIDv4; `text` is 1–4,000 characters; `expected_version` is optional and non-negative. Unknown fields are rejected. The request includes `conversation_id` only in the path.

## Events

Every event has the shape `event: <name>` followed by a JSON `data:` line, then a blank line. Text is streamed as UTF-8 without wrapping the content in Markdown or another envelope.

```text
event: delta
data: {"text":"Xin chào"}

event: delta
data: {"text":" bạn"}

event: done
data: {"status":"completed"}
```

A provider error after the stream starts is reported as an SSE error event (the HTTP response has already started and remains 200):

```text
event: error
data: {"code":"MODEL_UNAVAILABLE","message":"Dịch vụ tư vấn hiện tạm thời không khả dụng."}
```

Malformed requests return HTTP 422 before streaming. Missing provider configuration returns HTTP 503 before streaming. Responses set `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and `X-Accel-Buffering: no`.

## Integration and current limitations

The backend calls an OpenAI-compatible Chat Completions endpoint using `LLM_BASE_URL`, `LLM_API_KEY`, and the required model `cx/gpt-5.6-sol`; tokens are yielded as received. The `conversation_id` is not sent to the provider.

This endpoint is a provider-streaming scaffold, not yet the complete conversation API described in `implement.md`. The current repository does not implement conversation creation/storage, history retrieval, encrypted state, idempotency ledger, version/CAS checks, active-writer locking, slot filling, tool orchestration, verified RAG/citations, or safe persist-then-stream semantics. In particular, `client_request_id` and `expected_version` are validated but not enforced against PostgreSQL state. Do not use this endpoint as a durable financial advice workflow until those components are implemented. Client disconnect or provider failure can interrupt a turn; a streamed turn is not persisted or replayable.
