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

`client_request_id` must be UUIDv4; `text` is 1–4,000 characters; `expected_version` is optional and non-negative. Unknown fields are rejected. The request includes `conversation_id` only in the path. The client may generate this UUID; if no conversation exists for it yet, the first valid message atomically creates the conversation and its initial profile/checkpoint (version `0`) as part of claiming the turn. Existing conversations continue normally. The standalone `POST /api/v1/conversations` endpoint remains available for clients that prefer explicit creation.

## Idempotency and concurrency

`client_request_id` is a UUIDv4 scoped to the conversation and must be reused with the exact same payload after a timeout or disconnect. The server fingerprints operation, conversation ID, normalized text, and `expected_version` (`null` when omitted). Reusing the key with different content returns an SSE `error` event with `IDEMPOTENCY_CONFLICT`. A completed request replays its stored result without invoking the model or writing messages/version again. Requests in progress return `MESSAGE_PROCESSING`; a different key while another writer owns the conversation returns `CONVERSATION_BUSY`. Both are retryable and include `retry_after: 1`.

`expected_version` is checked before claim when provided; the captured version is always compared again at commit. A version mismatch returns `VERSION_CONFLICT`. Request ownership is fenced by an internal lease token; expired/stale attempts cannot commit. Message history, the encrypted checkpoint/version, and the encrypted replay response are committed atomically before the `done` event is sent.

## Events

Every event has the shape `event: <name>` followed by a JSON `data:` line, then a blank line. Text is streamed as UTF-8 without wrapping the content in Markdown or another envelope. `delta` events are provisional until `done`; clients must discard them if the stream ends with `error`.

A successful `done` event contains the persisted IDs and version, the user-facing `reply`, and `estimate` (an object when an estimate completed, otherwise `null`), for example:

```text
event: done
data: {"conversation_id":"...","client_request_id":"...","conversation_version":1,"user_message_id":"...","assistant_message_id":"...","reply":"Xin chào","estimate":null}
```

A completed retry sends the same durable response in `done`, with no `delta` events and no second provider or calculator call.

Common error codes include `IDEMPOTENCY_CONFLICT`, `MESSAGE_PROCESSING`, `CONVERSATION_BUSY`, `VERSION_CONFLICT`, `REQUEST_LEASE_LOST`, and `MODEL_UNAVAILABLE`. Errors after the stream starts use SSE `error`; the HTTP status is then already 200. Retryable failures instruct the client to reuse the same request ID and payload.

Example of a fresh streamed response (the completion event carries the committed response envelope):

```text
event: delta
data: {"text":"Xin chào"}

event: delta
data: {"text":" bạn"}

event: done
data: {"conversation_id":"<uuid>","client_request_id":"<uuid>","conversation_version":1,"user_message_id":"<uuid>","assistant_message_id":"<uuid>","reply":"Xin chào bạn","estimate":null}
```

Malformed requests return HTTP 422 before streaming. Requests larger than 20 KiB return HTTP 413 when the content length is available; the validated body is also checked before the stream begins. Responses set `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, and `X-Accel-Buffering: no`.

## Conversation context and orchestration

Chat has three handled paths:

- `general`: a complete greeting, thank-you or farewell message. The application answers locally without calling embeddings, retrieval or the chat model.
- `retrieval`: knowledge questions, including uncertain inputs and greetings mixed with questions. The application searches approved knowledge first; only usable evidence permits a model call.
- `estimate`: a loan-payment estimate handled by the dedicated estimate use case. It collects amount, term and fixed rate, asks the user to confirm the scenario, and only then calls the backend calculator. It does not call knowledge retrieval or ask the chat model to calculate.

The social-intent classifier normalizes case, Vietnamese accents and punctuation, then matches complete social phrases, not substrings. For example, `Xin chào!` is `general`, while `Chào bạn, lãi suất bao nhiêu?` and `Tôi muốn vay 10 tỷ` are knowledge `retrieval` unless an active estimate session handles the request. This is deliberately conservative, not a semantic multilingual classifier: unrecognized social phrasing also takes the retrieval path.

For conversational searches, the application includes up to two recent non-social user questions (each capped at 1,000 characters, selected from the latest 20 history messages) alongside the current question. Assistant replies are never included as retrieval evidence. This lightweight context helps follow-up questions without introducing an extra model call; it does not guarantee reference resolution across topic changes. The answer model receives up to the latest 20 committed user/assistant messages, the current question and the retrieved context. Neither the conversation ID nor legacy task/profile state is sent to the model.

Generic slot extraction, task queues and the old multi-intent planner are no longer part of chat (the loan-estimate flow above keeps its own small amount/years/rate state). The chat snapshot contains only history, conversation version and request lease identifiers. The state update carries a single typed intent, not arbitrary workflow/slot payloads. The atomic commit records that intent, clears legacy pending tasks/questions, and leaves existing profile slots untouched. Legacy slot-update and simulation-confirmation logic is no longer present in chat persistence. Old encrypted checkpoints remain readable; no database migration or frontend request change is required. Replay preserves the previously stored response, including responses created before this refactor.

## Trusted-source grounding

For each new knowledge `retrieval` turn, the application embeds the contextualized query and retrieves up to five knowledge chunks using the existing retrieval service. Search is bounded by a 15-second application timeout. The repository query only includes documents whose review status is `approved`, ingestion status is `published`, `is_active` is true, and effective date range includes the current date. Retrieval context is bounded; the model is instructed to answer from that evidence, place inline citations next to supported claims, and end with a concise model-written disclaimer before any source footer. This disclaimer is a prompt-level requirement, not structurally validated or guaranteed if the model omits it. The model does not generate a source list. The application recognizes exact numeric labels such as `[1]` only when the corresponding label exists in the current turn's retrieved citation list, and appends a footer containing only those cited sources, in retrieval order, after the model's complete answer (including any disclaimer). Unknown labels do not add sources to the footer; the application does not rewrite or remove the model's inline text. The footer's label check does not verify whether cited evidence semantically entails a claim. Because `delta` events are emitted while the model is generating, inline output (including an invalid label) may already have reached the client before the application can filter the footer. When no sufficiently relevant source or usable prompt context is found, the application returns a deterministic no-source reply without calling the chat model. Unconfigured, failed or timed-out retrieval/embedding is a technical error instead: the turn fails without committing a successful no-source reply. Valid-source footers are part of the streamed/persisted reply text.

## Markdown prompt resources

All chat prompts and deterministic reply text live in `app/infrastructure/prompts/*.md`:

| File | Purpose | Required placeholders |
| --- | --- | --- |
| `chat_system.md` | Base instructions for the answer model | None |
| `turn_guidance.md` | Wrapper for per-turn guidance | `{guidance}` |
| `grounding.md` | Source-grounding instructions and retrieved content | `{knowledge_context}` |
| `retrieval_guidance.md` | Instructions for retrieval answers | None |
| `retrieval_query.md` | Contextualized follow-up search query | `{previous_questions}`, `{text}` |
| `greeting.md` | Local greeting reply | None |
| `thanks.md` | Local thank-you reply | None |
| `farewell.md` | Local farewell reply | None |
| `no_evidence.md` | Local reply when usable evidence is unavailable | None |

`PromptCatalog` is a domain port injected into application services. `MarkdownPromptCatalog` implements file loading in infrastructure; the API composition root provides the same catalog to the application and model adapter. Application/domain code does not read files or import the infrastructure loader.

Save resources as UTF-8 (a BOM is accepted). Paths are resolved relative to the loader module, not the working directory. The default catalog checks all required files on first initialization, rejects missing, unreadable, invalid UTF-8 or empty files with `PromptLoadError`, and caches their content for the process. Restart the service after editing a prompt; there is no automatic reload. The existing Docker image copies the entire `app` directory, including these `.md` resources.

Keep the required placeholders in template files. Templates use Python `str.format`; literal braces in these three template files must be doubled (`{{` and `}}`). Template syntax and unknown placeholders are checked at load time; malformed templates raise `PromptLoadError`. Removing a required placeholder without introducing a syntax error is not detected automatically. Inserted user text, guidance and source content are values and are not recursively formatted. Replayed requests return their already-persisted reply, not a newly rendered reply using changed prompts.

## Technical error contract

Technical failures use domain `ChatError` subclasses containing `code`, `stage`, `retryable` and `status_code`. Adapters/repository boundaries raise them where failures occur and preserve the original exception with `raise ... from exc`. The application records a failed claimed request, then re-raises; a failure while recording the failure is logged but never replaces the original exception. Existing `ChatTurnError` lease/conflict decisions are preserved.

Initialization failures before the stream return an HTTP error with `detail: {"code": "...", "retryable": false}`. After streaming starts, HTTP remains 200 and the endpoint sends `event: error` with `{"code": "...", "retryable": ...}`, never `done`. Server logs include the stage and chained traceback; public payloads omit exception text, provider bodies, database details and filesystem paths. Prompt/model configuration is no longer checked in the route itself: the responsible resource/provider raises the error. In particular, social replies and replay do not require configured chat-model credentials.

| Source | Codes | Retryable |
| --- | --- | --- |
| Prompt loader | `PROMPT_UNAVAILABLE` | No |
| Initialization | `CONFIGURATION_INVALID`, `DATABASE_NOT_CONFIGURED`, `ENCRYPTION_NOT_CONFIGURED`, `EMBEDDING_CONFIGURATION_INVALID` | No |
| Retrieval orchestration | `RETRIEVAL_NOT_CONFIGURED`, `RETRIEVAL_UNAVAILABLE`, `RETRIEVAL_TIMEOUT` | No for unconfigured; otherwise yes |
| Query embedding | `EMBEDDING_UNAVAILABLE`, `EMBEDDING_NOT_CONFIGURED`, `EMBEDDING_INVALID_RESPONSE` | No for unconfigured/invalid query vector; otherwise yes |
| Knowledge search | `KNOWLEDGE_SEARCH_UNAVAILABLE` | Yes |
| Model adapter | `MODEL_NOT_CONFIGURED`, `MODEL_AUTHENTICATION_FAILED`, `MODEL_REQUEST_REJECTED`, `MODEL_RATE_LIMITED`, `MODEL_TIMEOUT`, `MODEL_UNAVAILABLE` | No for configuration/authentication/rejection; otherwise yes |
| Conversation storage | `STATE_UNAVAILABLE`, `STATE_CORRUPTED` | Yes for database failure; no for corrupt encrypted state |
| Unexpected programming/runtime failure | `INTERNAL_ERROR` | No |

Business conflicts, lease fencing and stored replay responses retain their existing codes. Retryable failures still use the existing bounded ledger retry policy, which can eventually replay `REQUEST_RETRY_EXHAUSTED`. The original and replayed payloads retain the existing two-field code/retryability shape; internal stages are only logged. No live database/provider failure injection has been performed.

## Integration and remaining limitations

Prompt-loading and rendering tests use local resources and a mocked provider transport; they do not verify a deployed image or a live provider.

The backend calls an OpenAI-compatible Chat Completions endpoint using `LLM_BASE_URL`, `LLM_API_KEY`, and the configured model, and uses the configured embedding endpoint for retrieval. Durable conversation state, idempotency claim/replay, writer gate, lease fencing, version checks, and atomic message/checkpoint/response commit are implemented for this message endpoint. Chat does not run bank comparison/recommendation tools. Loan estimates are the only calculation: `EstimateLoanUseCase` collects amount, years and rate, asks the user to confirm, then calls the backend `POST /api/estimate` (`LOAN_BACKEND_BASE_URL`, default `http://127.0.0.1:8000`), which uses `backend/finance/calculator.py`. The model never computes numbers itself, and the assistant must not represent model output as a verified calculation or bank offer. The shared contract is in `docs/api.md` at the repository root. Grounding quality still depends on the correctness, coverage, approval, and freshness of operator-supplied documents and on retrieval relevance; citations do not guarantee that a document answers every part of a question.

The stream can expose provisional `delta` text before the database commit; if commit subsequently fails, the client receives `error` and must treat those deltas as uncommitted. Model output is not persisted until the successful atomic commit.
