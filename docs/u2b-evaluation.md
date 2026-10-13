# U2B authored offline evaluation source

This version adds source and pure controls for a bounded offline comparison. No U2B workflow, live model, external connector or unseen acceptance evaluation has run. Main owns native execution and acceptance. Existing Java state, authorization, approvals, provider loop, retry timing, connector and runtime budgets are unchanged.

## Data and exposure

`fixtures/u2b/manifest.json` binds 8 development and 12 capability records, their separate input/label JSONL files, MIT license and source hashes. All are synthetic and author-exposed. Twelve semantic families derive from the existing public `fixtures/dev` cases: departure success, no approval, asset outage, cancellation and restart; joining success, support role, compensation, preservation of an existing account, no approval, budget exhaustion and supersession. Fictional employee/asset/event identifiers and event sequences are remapped. Expected states are author-derived hypotheses, not observed U2B outcomes.

Development and capability share eight families. Twenty unique record identities would yield forty paired policy slots; neither count establishes twenty independent scenario families or unseen generalization. Regression evidence remains in the original suites and historical freezes. No main-held unseen data was accessed or created.

## Comparison boundary

`deterministic-v2` uses current observed Java eligibility, retry state and authoritative status, and requests verification of observed completion. It does not dispatch on task IDs, families, labels or a remembered completed-step index. `scripted-adaptive` is the existing authored script. Both use the same `EvaluationPolicy` input boundary, typed tools, existing `agent.cli.act`/`agent.loop.run_loop`, Java authority, seed, operator schedule and persistent reservations. Actor requests contain only fictional employee ID, explicit lifecycle intent and one fixed neutral sentence. Nested evaluation metadata, changed request text and oversized contexts fail closed.

The unchanged generic loop supports a provider protocol and an optional Responses provider. These two offline modes demonstrate a baseline and comparison harness; they provide no live model quality evidence. The separate U1 Gateway controller has different offboarding-only reservations and is not represented as an equivalent participant in this slice. A future live comparison needs main-reviewed adaptation and a separate live grant. No positive uplift is required or claimed.

Both policies keep the existing 120-second actor-loop limit, 2-second decision limit, 24-turn ceiling, 32 actor-tool/12 safety-tool ceilings and 2000-ms retry-wait cap. The existing budget-exhaustion family seeds a 9-turn limit identically for both policies. Additional observation/verification calls consume the same budget. Fixture approvals and recovery/operator actions are synthetic controls, not human activity or actor authority.

## Scoring and complete accounting

Before execution, the runner persists the selected unique task roster and every paired slot with input, approval-schedule and budget hashes. A missing, duplicate, reordered or changed slot is rejected. PLANNED, RUNNING, SCORED, FAILED, TIMEOUT and UNKNOWN remain visible. A killed process leaves its RUNNING slot and future PLANNED slots in the ledger; `summary` counts their outcomes as unknown and never retries them. Main must supervise the whole process tree and retain the exit/timeout evidence.

After the acting bridges close, the unchanged independent XML verifier and HR/identity/assets history metrics evaluate committed state and receipts. Actor drafts and runner success strings confer no completion. Exact expected-state match, safe stop, actual completion, duplicate effects and unsafe service changes are separate. Wrong expectations retain independent measurements. Actual completion requires raw administrative completion, five required steps and no independent safety violations. Due-approved departure revocation uses observed approval/HR history, rather than all tasks. Joining is 0/0 with a null revocation rate.

Aggregates include every intended slot and also label observed-only rates explicitly. Paired completion reports deterministic wins, scripted wins, both-complete ties, both-incomplete ties and unknown pairs. These are descriptive counts for authored cases, without statistical or causal claims. Metrics expose fixed enums, integer counts, finite numbers and digests; raw XML, drafts, exception messages and identities are excluded. Saved local run folders still contain fictional source evidence for independent review.

Usage remains null when unreported. Known cost subtotals do not become complete cost totals when any slot is unknown. Cost per completion is null for unknown total cost or zero completions. The offline runner records zero actual monetary cost for executed slots because neither implementation invokes a chargeable provider; it does not invent token usage. Unstarted slots retain null cost. Source/data versions, evidence hashes, policy/decision counts, tool/reservation counters, synthetic approval counts, crash-window observations, latency and error types are retained separately.

## Pure checks and proposed first native batch

```powershell
py -3.11 dev.py test --suite u2b-unit
py -3.11 dev.py source-check
py -3.11 -m evaluation.u2b plan --split development
```

Pure tests guard subprocess and socket creation and use authored XML histories and mocked runner calls. They test contaminated inputs, missing/duplicated slots, forged completion, stale approval and forged effect receipts, duplicate effects, independent scoring after expectation failures and null cost/usage. They do not execute application workflows.

The only proposed initial native batch selects development `U2B-D01` (departure success) and `U2B-D07` (joining compensation), once with each offline policy, at a fresh path. It is unexecuted. `evaluation.u2b run` requires a JSON grant from main matching lease `employee-u2b-first-pair-20261012`, active/main ownership, repository slug, exact current source/data hashes, selected IDs/split, 14 existing class hashes and the exact resource mapping in `evaluation.u2b.RESOURCES`. The UTC expiry must leave at least 240 seconds for command/teardown. This is a local procedural resource gate, not a cryptographic authorization service.

```powershell
py -3.11 -m evaluation.u2b run --split development --ids U2B-D01,U2B-D07 --out runs/u2b-main-first-20261012 --main-grant <main-supplied-grant.json>
py -3.11 -m evaluation.u2b summary --out runs/u2b-main-first-20261012
```

Main's supervisor must enforce 180 seconds for the command and 300 seconds for the active lease, including two 10-second source gates and up to 60 seconds of teardown. The proposal caps RAM at 768 MiB, disk at 128 MiB, Java at one process, and Python at two including the launcher; HTTP servers, downloads, external calls and spend are zero. Sequential execution can still be interrupted inside an unchanged actor call. It does not promise four completed runs within the cap. No build or retry occurs automatically, and the worker has no current native lease.

`ledger.json` stores the full initial intent and evolving status; `metrics.json` stores redacted aggregation; `score-NN.json` stores each independent redacted verdict. Missing evidence stays unknown. Successful exact safe compensation counts as an expected safe stop with zero actual completion. Native receipts, monitored cleanup/peaks, any full authored-slice evaluation, live model quality and genuine sandbox integration remain pending.

## Preservation

The additive `u2b-evaluation-source-1` current source seal retains the exact preceding `u2a-transport-phase-source-1` manifest and six changed predecessor files. It also retains the sanitized authentic U2A main review. That review covered 104 current plus 167 unchanged historical root methods (271 inventory coverage), and nine copy groups/fifteen cells/208 repeated methods. Those counts are historical local evidence, not fresh U2B runs. Earlier timeout and phase/monitor failures remain attributable to their original artifacts. No historical freeze, result or approval is regenerated.
