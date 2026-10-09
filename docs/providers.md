# Provider decision contract

`next_turn(request, observations)` returns exactly one `ToolCall`,
`Clarification` or `FinalDraft`. The request contains explicit employee ID,
intent and fictional text; observations contain bounded results of actor tools.
Java owns approval, payload derivation, allowed steps, service versions,
durable receipts, cleanup and completion. The provider cannot approve, edit
clocks/events/faults, read files or supply access-mutation parameters.

Default `scripted`/`scripted-adaptive` and `fixed` are authored deterministic
providers. Evaluation permits only those two modes. Demos permit only offline
modes because their trusted fixture driver performs scripted operator approval.
`responses` and `replay` are manual submit/resume routes.

## Optional HTTP source, unexecuted live

`ResponsesProvider` implements a narrow nonstreaming function-calling contract
using an injected transport and Python's standard library. Tool definitions
require exact string arguments, strict schemas and no additional properties.
Requests disable parallel calls and server-side storage. Returned function
calls are validated locally, correlated through `call_id`, and included with
their result on the next request. Opaque reasoning items, including encrypted
content when returned, are preserved. This follows
[official OpenAI function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling).

The parser rejects duplicate argument fields, extra function fields, unknown
tools, multiple calls, call-plus-final output, duplicate/missing IDs, unsupported
output items, incomplete/error responses, malformed usage and oversized data.
Refusal yields a safe clarification. Final text is only a draft. Top-level API
metadata is ignored; executable items use the documented finite allowlist.
Changed requests or tool observations fail correlation before another request.

The production transport requires `--provider responses`, `--allow-live`, an
explicit `--model` and already configured `LIFECYCLE_OPENAI_API_KEY`. It accepts
only `https://api.openai.com/v1/responses`, disables proxies and redirects,
uses one request attempt with a 1.5-second socket timeout and read deadline, limits replies to
64 KiB and input history to 128 KiB. The enclosing actor allows two seconds per
decision; a timeout stops further decisions and Java owns cleanup. HTTP errors
do not retry or reset persisted budgets. The finite timeout is intentionally
short and may reject valid slow live responses. The provider daemon can outlive
the decision timeout during DNS resolution or a socket read; Python threads
cannot hard-cancel remote work. It cannot make further Java tool decisions.
This is an explicit limitation of the unexecuted optional live route.

No model is chosen by default. No API key has been obtained, no account set up,
and no live request has been made. Running this route would require new human
authorization in the portfolio. It is not part of offline quickstart, evaluation
or CI. Real-provider compatibility, latency and decision quality are unverified.

Protocol traces retain prompt version, explicit model, response/call IDs,
request/response hashes, validation status and observed usage counters. They
never store authorization headers, credentials or raw error bodies. Hashes are
audit identifiers, not an independent proof that a remote provider received
the request. Acting traces are separate from authoritative domain outcomes.

## Synthetic replay regression

`ReplayProvider` uses the same response parser, matches each serialized request
SHA-256 and fails on altered context or exhaustion. It never selects by fixture
ID, expected label or success answer. Its files must explicitly declare
`authored-synthetic-not-a-model-recording`.

`fixtures/providers/synthetic-inspect.json` is a handwritten two-turn protocol
fixture: inspect E-REPLAY through a fake bridge, then draft operator review.
Pure units exercise this exact request/result correlation. This is a synthetic
protocol regression, not a transcript from a model and not a complete Java
lifecycle demonstration. A manual replay file must match that invocation's
exact request and observations; the fixture is not a generic successful actor.

## Tests

Pure units validate schema, typed parsing, refusals, correlation, context
separation, failure hashes, explicit opt-in and synthetic replay without sockets
or Java. The separately authored loopback suite starts only a literal IPv4
127.0.0.1 endpoint with no credentials. It checks actual serialized requests,
function results, HTTP 429/500, redirect rejection, content type, size and socket
timeout, then shuts its server down. Its execution requires the M3 integration
lease and remains unexecuted at the source checkpoint. These tests establish
the implemented local contract when run, not real API compatibility.
