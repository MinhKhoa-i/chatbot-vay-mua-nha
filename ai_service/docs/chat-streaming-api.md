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

Chat has four handled paths:

- `general`: ordinary conversation, including greetings, thanks and farewells. The application calls the chat model with `general_guidance.md`, without embeddings or knowledge retrieval.
- `retrieval`: knowledge questions, including uncertain inputs and greetings mixed with questions. The application searches approved knowledge first; only usable evidence permits a model call.
- `estimate`: a loan-payment estimate handled by the dedicated estimate use case. It collects amount, term, repayment method, optional promotional rate/duration and the rate after promotion (or the full-term rate without a promotion), asks the user to confirm the scenario, and only then calls the backend calculator. It does not call knowledge retrieval or ask the chat model to calculate.
- `bank_compare`: a scenario-based bank comparison handled by `CompareBanksUseCase`. It collects amount and whole years, and asks for an assumed post-promotion floating rate when neither that assumption nor a base rate is available. Optional inputs include property value, prepayment month, principal-grace months and repayment method; the default method is `annuity`. Once required inputs are available, it calls backend `POST /api/banks/rank` without a separate confirmation step. It does not retrieve knowledge. The model describes the backend result, subject to the buffered numeric check below; this is not a credit-approval decision or a recommendation.

Intent classification uses the configured model with conversation context; chat no longer uses the old exact-phrase social normalizer. General replies use the model rather than fixed greeting, thank-you or farewell templates.

For conversational searches, the application includes up to two recent non-social user questions (each capped at 1,000 characters, selected from the latest 20 history messages) alongside the current question. Assistant replies are never included as retrieval evidence. This lightweight context helps follow-up questions without introducing an extra model call; it does not guarantee reference resolution across topic changes. The answer model receives up to the latest 20 committed user/assistant messages, the current question and the retrieved context. Neither the conversation ID nor legacy task/profile state is sent to the model.

Generic slot extraction, task queues and the old multi-intent planner are no longer part of chat. The chat snapshot includes history, conversation version, request lease identifiers, typed estimate/bank-comparison sessions and shared conversation memory. Active sessions handle follow-up inputs before ordinary intent classification. When starting a calculation/comparison path, the application can reuse fields from shared memory; bank-comparison extraction also receives the latest assistant message to interpret short answers. The state update carries the typed intent, session changes and updated memory. Replay preserves the previously stored response rather than regenerating it.

### Buffered bank-comparison replies and numeric fallback

`CompareBanksUseCase` always renders a deterministic result into `BankCompareTurn.answer`. When a backend result exists, `StreamChatUseCase` passes JSON containing `scenario` and `result` to the answer model with `bank_compare_guidance.md`. The application buffers all model fragments for this path instead of emitting them immediately. Collection/cancellation replies without a result use the deterministic answer directly.

Before emitting the completed draft, `bank_compare_numbers_match()` extracts numeric values and checks that they are a subset of an allowlist built from scenario amounts/durations/rates, backend costs/payments/rates/assumptions, ranking positions and numbers in the result date, bank/package labels and exclusion text. The parser normalizes supported Vietnamese money units, grouped VND amounts, decimal separators, ISO date separators and invisible formatting characters.

If the check fails, the application logs `BANK_COMPARE_NUMBER_MISMATCH` and replaces the entire draft with `BankCompareTurn.answer`. It emits one `delta` containing the selected answer and commits that same answer before `done`; an invalid model draft is not emitted. This fallback handles numeric mismatch, not provider errors/timeouts, which still fail the turn. Other model-generated paths retain incremental streaming. Bank-comparison results appear in `reply`; there is no separate structured bank-comparison field in `done`, and `estimate` is `null` for these turns.

**Limit:** this is numeric-value membership checking, not semantic validation. For example, with a 20-year term and a 10% assumed rate, a draft saying “lãi giả định 20%/năm” can pass because `20` is present in the scenario. The guard does not verify bank/field/unit associations, ranking correctness, required facts or nonnumeric claims. Prompt instructions are not a runtime guarantee; a hard guarantee requires backend-rendered facts or validated field references, which are not implemented here. Regression examples and buffer/fallback assertions are in `tests/test_bank_compare_chat.py::test_comparison_validates_buffered_draft_before_emitting`.

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
| `general_guidance.md` | Instructions for general conversation replies | None |
| `no_evidence.md` | Local reply when usable evidence is unavailable | None |

`PromptCatalog` is a domain port injected into application services. `MarkdownPromptCatalog` implements file loading in infrastructure; the API composition root provides the same catalog to the application and model adapter. Application/domain code does not read files or import the infrastructure loader.

Save resources as UTF-8 (a BOM is accepted). Paths are resolved relative to the loader module, not the working directory. The default catalog checks all required files on first initialization, rejects missing, unreadable, invalid UTF-8 or empty files with `PromptLoadError`, and caches their content for the process. Restart the service after editing a prompt; there is no automatic reload. The existing Docker image copies the entire `app` directory, including these `.md` resources.

Keep the required placeholders in template files. Templates use Python `str.format`; literal braces in these three template files must be doubled (`{{` and `}}`). Template syntax and unknown placeholders are checked at load time; malformed templates raise `PromptLoadError`. Removing a required placeholder without introducing a syntax error is not detected automatically. Inserted user text, guidance and source content are values and are not recursively formatted. Replayed requests return their already-persisted reply, not a newly rendered reply using changed prompts.

## Technical error contract

Technical failures use domain `ChatError` subclasses containing `code`, `stage`, `retryable` and `status_code`. Adapters/repository boundaries raise them where failures occur and preserve the original exception with `raise ... from exc`. The application records a failed claimed request, then re-raises; a failure while recording the failure is logged but never replaces the original exception. Existing `ChatTurnError` lease/conflict decisions are preserved.

Initialization failures before the stream return an HTTP error with `detail: {"code": "...", "retryable": false}`. After streaming starts, HTTP remains 200 and the endpoint sends `event: error` with `{"code": "...", "retryable": ...}`, never `done`. Server logs include the stage and chained traceback; public payloads omit exception text, provider bodies, database details and filesystem paths. Prompt/model configuration is no longer checked in the route itself: the responsible resource/provider raises the error. Replay does not call the chat model; newly generated general replies require configured chat-model credentials.

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

The backend calls an OpenAI-compatible Chat Completions endpoint using `LLM_BASE_URL`, `LLM_API_KEY`, and the configured model, and uses the configured embedding endpoint for retrieval. Durable conversation state, idempotency claim/replay, writer gate, lease fencing, version checks, and atomic message/checkpoint/response commit are implemented for this message endpoint. Chat supports backend bank ranking via `POST /api/banks/rank`, with LLM-written, buffered replies and the limited numeric fallback described above; the ranking is not a recommendation or approval decision. Loan-payment estimates use a separate path: `EstimateLoanUseCase` collects amount, years, repayment method (`annuity` or `reducing_balance`), an optional promotional rate with its duration in months, and the rate (the post-promotion rate when a promotion applies), asks the user to confirm, then calls the backend `POST /api/estimate` (`LOAN_BACKEND_BASE_URL`, default `http://127.0.0.1:8000`), which uses `backend/finance/calculator.py`. Calculations run in the backend, and the model is instructed not to calculate or change values; the bank-comparison numeric check does not guarantee correct use of those values. The assistant must not represent model output as a verified calculation or bank offer. The shared contract is in `docs/api.md` at the repository root. Grounding quality still depends on the correctness, coverage, approval, and freshness of operator-supplied documents and on retrieval relevance; citations do not guarantee that a document answers every part of a question.

The stream can expose provisional `delta` text before the database commit; if commit subsequently fails, the client receives `error` and must treat those deltas as uncommitted. Model output is not persisted until the successful atomic commit.
