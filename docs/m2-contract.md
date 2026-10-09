# M2 lifecycle contract

M1 and M2 were independently accepted. M2 passes Java build/doctor,
all 96 tests, four demonstrations and 24 paired development runs. All cases are fictional, authored
under MIT, and offline; see EVIDENCE.md for the failed first attempt and correction.

## Authority and role actions

| Journey | Ordered actions | Approved safety actions |
| --- | --- | --- |
| Offboard | disable_login, revoke_sessions, remove_grants, create_collection_task, complete_hr | Remaining first three access reductions; never restore access |
| Onboard | prepare_account, add_role_grants, reserve_asset, enable_login, complete_onboarding_hr | compensate_account, undo_role_grants, release_asset, fail_onboarding_hr |

The finite role bundles are engineer = employees + engineering and
support = employees + support. Existing disabled accounts are eligible only
with zero sessions, no assigned asset and pre-existing grants contained in the
target bundle. Java derives payloads from authoritative HR role and approved
pre-state. Extra grant, role, operation-key or approval fields in an actor call
are rejected.

Approval binds workflow/employee, event ID/sequence/epoch/role/effective time,
initial HR/identity/asset versions, exact grants/account/asset pre-state,
inventory ID/availability, action order, policy version and allowed safety
actions. The digest uses sorted fields and UTF-8 values prefixed by four-byte
lengths. The trusted operator approves that reviewed digest as hr-reviewer.
Forward writes recheck effective time, 24-hour approval expiry, authoritative
event and expected service versions.

Newly prepared accounts carry created_by; added grants have an owner and exact
added set; reservations carry reserved_by. Cleanup disables only its own
enablement, tombstones its own new account, removes only its added grants and
releases only its reservation. It preserves pre-existing disabled accounts and
grants. A changed service version blocks cleanup instead of overwriting an
unrelated edit. Tombstones are an explicit local simulation choice.

HR event import commits the authoritative successor before workflow bookkeeping.
Every forward service write rereads that event. Restart fences an older plan
even if the HR import acknowledgement was lost. An in-progress onboarding is
compensated, then marked SUPERSEDED; cleanup never overwrites the successor HR
record. Completed onboarding resources remain for the successor departure.
Exact same-event replay has no effect; changed replay and older sequences are
denied. A join following departure is an unsupported rehire. At most sixteen
events/workflows are accepted; one workflow is active. Historical workflow
snapshots remain inspectable, but the operator report addresses the current ID.
After the predecessor is SUPERSEDED, the operator can use activate-event with
the old workflow ID to initialize the authoritative successor and its own
bounded counters. Submit a new matching request file for that event. This also
permits a successor after the old actor exhausted its allowance; it grants no
approval or service write by itself.

## Stop, budgets and recovery

Cancellation and malformed/failed/false-final provider output stop new actor
decisions. Java owns bounded cleanup independently of the provider. For an
approved due departure it completes remaining authorized access reductions and
leaves administrative work for review. Before the effective time it performs
no service mutation. An unapproved cancellation has zero service effects.
Awaiting approval and future-time pauses remain resumable.

Budgets persist across process restart: 24 provider turns, 32 actor tool calls,
120,000 milliseconds of active reservations, three attempts per operation,
and a separate twelve-call safety allowance. Each decision reserves seven
seconds (two for the offline provider and five for RPC); retry waits are also
charged. The time bound can stop the actor before the turn bound. Reservations
are conservative allowances, not measured latency. Approval idle time is not
charged. A begin-turn/control RPC is owned by the harness and is absent from
model tool definitions. Raw actor calls also consume the persisted allowance.

The Python loop catches bounded offline provider errors/timeouts and sends the
finite stop control. Actor pipe EOF also triggers Java safety for a metered
provider session. A named process halt skips EOF cleanup, allowing actual
restart/receipt recovery. Each service commit atomically stores state, scoped
receipt, effect count and audit context. Scope includes event sequence and
epoch; a lost reply is reconciled before another write. Retries do not reset
attempts. Receipt lookup outage exposes RECOVERY_BLOCKED with unresolved work.

Immutable snapshots are bounded to 4,096 generations and 16 MiB per store;
each snapshot has at most 512 fields and a 4 MiB ceiling. Three service adapters
share one cooperating local writer. The evidence supports process restart on
the tested local filesystem only. No power-loss, production token/session,
network-share or distributed transaction claim is made. M1 runtime directories
require no reinterpretation: M2 requires fresh run directories rather than an
implicit schema migration.

## Development and corruption contracts

The twelve development scenarios are the four accepted M1 departure cases plus
onboard-success, onboard-support, onboard-compensation,
onboard-preserve-existing, onboard-no-approval, onboard-superseded,
offboard-cancel and onboard-budget-exhaustion.

Sixteen real child-process contracts are authored as this exact matrix:

| Target | before_intent | after_intent/pre-call | after_service_commit/pre-ack | after_result |
| --- | --- | --- | --- | --- |
| disable_login | 1 | 1 | 1 | 1 |
| add_role_grants | 1 | 1 | 1 | 1 |
| create_collection_task | 1 | 1 | 1 | 1 |
| undo_role_grants during compensation | 1 | 1 | 1 | 1 |

Every cell must observe an actual owned-process failure and its named marker,
check service/workflow state at that window, restart in a new process, and
compare domain fields, versions and effect counts with an uninterrupted
reference. Attempts may increase at a pre-call crash, stay bounded and never
reset. Recovery equivalence does not require equal timestamps or attempt counts.

Six additional real-result corruption controls are authored: forbidden grant,
restored departed login, retained session, duplicated collection task, hidden
required step and removed audit receipt. All six rejected the altered actual
Java results. Lightweight
authored-snapshot tests cover these invariants and also check receipt
immutability, payload hashing, expiry, superseded writes and transient grants.

The independent verifier reads committed service state and history. It
recomputes approved plan/payload digests and checks intermediate access
additions against HR authority at commit order. It does not call Java's
completion predicate or grade actor prose. Receipt/effect/audit entries cannot
change between generations. This is independent implementation of finite
policy, not independent data provenance or tamper-proof storage.

## Frozen holdout and paired baseline

Thirty-six heldout inputs and labels live in separate JSONL files. Six cases
each cover valid journeys, authority conflicts, ordering, recovery, persistent
failure and adversarial input. IDs, wording, initial service versions, grants,
roles and failure timing vary. Inputs/driver schedules enter only the
operator-owned harness; labels and verifier never enter provider context.
The actor has no filesystem tool.

The preserved m2-v3 manifest hashes every input/label line and the complete files, verifier,
actor/protocol, driver and Java authority. Freeze before final scoring;
post-freeze repairs require a new manifest version and an explicit evidence
entry. These are authored, inspectable cases, not a blind external benchmark.
No heldout case has been scored.

The fixed provider follows declared evidence and action order. The scripted
adaptive provider chooses from eligible-step observations. Both get identical
seeds, approvals, faults, budgets, durable recovery and Java safety. Neither
uses fixture IDs or labels. A tie is valid. The development evaluator invokes
scoring in a separate Python process after each actor closes and retains every
case result, failure, denominator and paired outcome. No real LLM quality or
stochastic variance claim follows from scripted runs.

## Reproduction commands

Run from a fresh source checkout with Java 17 JDK and Python 3.11:

```powershell
py -3.11 dev.py doctor
py -3.11 dev.py build
py -3.11 dev.py test --suite m2
py -3.11 -m agent.cli demo --scenario onboard-success --provider scripted --run-dir runs/m2-success
py -3.11 -m agent.cli demo --scenario onboard-compensation --provider scripted --run-dir runs/m2-compensation
py -3.11 -m agent.cli demo --scenario onboard-preserve-existing --provider scripted --run-dir runs/m2-preserve
py -3.11 -m agent.cli demo --scenario onboard-superseded --provider scripted --run-dir runs/m2-superseded
py -3.11 dev.py evaluate --split dev --modes fixed,scripted-adaptive --repetitions 1 --out runs/m2-development
```

M2 suite collection is 96 tests: 40 Python units, 14 M1 regressions,
12 development contracts, 16 crash contracts, eight authority cases and six
real-result corruption controls. All 96 pass after the recorded correction.
The paired development command produced 12 x 2 = 24 case-runs, both modes
matching 12/12 expected outcomes. Only four workflows per mode completed all
administrative work; the other eight intentionally paused, blocked, cancelled,
compensated or superseded. Exact-contract success is distinct from completion.
Doctor, build, integration, demos and development evaluation require the
separate granted M2 resource lease in this managed project.

The lightweight `py -3.11 dev.py freeze-check` only reads/hashes source/data;
it never starts Java or scores cases. A live HTTP provider, heldout evaluator,
replay regression adapter, prepared hosted CI and fresh-copy quickstart are
M3 source additions. Pure synthetic provider regression is tested; HTTP/Java
integration, heldout scoring, fresh-copy quickstart and hosted CI remain
unexecuted. See docs/m3-evaluation.md and docs/providers.md.
The real M2 execution correction returns the
workflow ID with an exhausted first-turn denial so a restarted CLI can report
its existing disposition. Budgets and labels were preserved. The finite
operator driver reuses one actor process across consecutive steps, and the
matrix retains exact crash exit codes, markers and pre-recovery snapshots.

