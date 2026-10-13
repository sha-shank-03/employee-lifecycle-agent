# U1 Gateway source candidate — 11 October 2026

The prior source candidate passed 187 regression/pure methods and 18 Java/HTTP methods. Its scripted local-double demo passed 165 independent state/audit assertions with five effects. Independent main review then stopped when `check-public` found four Windows cache databases under a literal unresolved percent-variable directory in the repository. Those passes remain attributable to the prior candidate; U1 has not been accepted.

The corrected candidate passed 24 pure checks in 0.125 seconds, including Windows path defaults, rejected invalid runtime roots and isolation from keys/proxies/Python settings. It supplies only Windows runtime directory variables to its owned transport child: `SystemRoot`, `SystemDrive`, `WINDIR`, `ProgramData`, `LOCALAPPDATA`, `USERPROFILE`, `APPDATA`, `TEMP` and `TMP`. Missing drive/Windows/program-data defaults derive from a valid absolute Windows root. Other platforms receive an empty environment. Keys, proxies, `PATH` and Python configuration are excluded. The four failure files were preserved byte-for-byte in ignored local quarantine. No cache path was added to the public inventory or ignore rules. The original U1 manifest and every changed prior source are archived and checked separately by `u1-source-check`. Corrected native transport/demo checks and fresh-copy execution remain **unexecuted pending main's named lease**. This is not upgrade acceptance, live model evidence or genuine external integration.

U1 uses Python 3.11 standard libraries and the existing Java 17 authority. The only configuration accepted by `agent.u1` selects `local/synthetic-tool-double`, zero inference allocation and zero automatic retries. The transport accepts a literal loopback endpoint, has no credential loader, disables proxies and redirects, and starts one fixed-argv owned Python child per inference decision. Real Gateway/Entra setup remains pending. The worker chat model is not a runtime model.

The double implements nonstreaming OpenAI-compatible Chat Completions function calls. Validated assistant calls and matching tool-result IDs survive approval/resume. Java supplies authoritative observations and derives every mutation from its approved plan. The provider cannot configure budgets, approve a plan, edit clocks or invoke operator tools. Java approval also binds the U1 config identity. A configured U1 run supports one offboarding event; its operator event-import/activation paths are denied.

Bounds: 12 cumulative inference turns, 32 actor tool calls, one call per decision, 2,048 reported/output-cap tokens, 32,768 reported input tokens, 64 KiB responses and 128 KiB request/history. Missing usage/cost stay null. The double's authored usage values are protocol fixtures, not measured model token consumption. Live input/billing-cap semantics remain a later preflight gate.

Java reserves 10 seconds per active session, 25 seconds per turn (provider/transport/cleanup plus a tool), and separately charges retry waits. Actor reservations cannot exceed 300 seconds across resume. Each session also reserves two seconds for Java teardown. A safety batch reserves its entire remaining 60-second cleanup allowance before effects; a crash spends that reservation. Resuming a spent batch can reconcile receipts and expose unresolved work, but cannot replenish cleanup time. Parent monotonic deadlines include transport and owned-child teardown. This relies on the local OS responding to termination; it is not a guarantee against an unresponsive kernel or storage device.

Approval pauses are recorded and excluded from active work. HTTP errors, ambiguous loss, malformed replies, refusal, cancellation and late replies stop inference; none trigger an automatic resend or fallback. An uncertain Java acknowledgement preserves the pending call. An explicit resume reconciles authoritative state/receipts and audits them independently before supplying a `RECONCILED` observation, then chooses a subsequent decision. A transport failure marks history failed and requires operator review.

`gateway-events.jsonl` retains sanitized events across sessions. It contains version/hash IDs, fixed modes, counters, timings, bounded usage/status and null cost, with no raw request, model prose, arguments, employee identifiers, headers or exception bodies. Harness history retains fictional observations locally. `gateway-owned-cleanup.jsonl` retains actual owned PID/start/exit records for lease review. The independent verifier reads committed snapshots/receipts; a model final draft cannot establish completion. Revocation, administrative completion, handoff and physical return remain separate.

After a lease, the authored journey is:

```powershell
py -3.11 dev.py doctor
py -3.11 dev.py build
py -3.11 dev.py test --suite u1-integration
py -3.11 -m agent.u1_demo --out runs/u1-double-20261011
py -3.11 dev.py verify --run-dir runs/u1-double-20261011 --expect fixtures/dev/offboard-success/expected.json
```

The demo uses **SCRIPTED fictional operator approval** after reaching the pause. Inspect `u1-demo.json` for before/after outcomes and independent assertions. `agent.u1 configure --run-dir <run> --config fixtures/providers/gateway-u1-config.json` binds a fresh initialized run. `agent.u1 run` requires the same config and an explicit local-double endpoint. It exits 0 for verified completion, 2 for unfinished work and 1 for unexpected rejection; configure exits 0 when successful.

Pure checks: `py -3.11 dev.py test --suite u1-unit`. Read/hash-only provenance: `py -3.11 dev.py u1-source-check`. Prepared CI runs offline contracts and a fresh public copy; hosted CI remains unexecuted. Java/HTTP/full-suite/fresh-copy commands require the lease in this coordinated upgrade.

The original forty-file v1 freeze, data, historical failures and published commit remain intact. Exact pre-U1 copies of changed frozen source live under `evaluation/upgrade/v1-source`; the additive U1 source manifest binds current files separately. The original `freeze-check` and heldout scorer intentionally reject current changed source rather than silently reusing old results. Legacy scoring belongs to the published v1 source; new evaluation is outside this U1 slice. No quality uplift, measured business impact, external sandbox, credentials, production HRIS/assets, onboarding connector or deployment is claimed.

Protocol references: [Gateway Chat Completions](https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-chat-completions), [function calling](https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-chat-completions/tool-calling), and [REST usage](https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-chat-completions/rest-api), inspected 11 October 2026. Documentation compatibility is not an observed live request.
