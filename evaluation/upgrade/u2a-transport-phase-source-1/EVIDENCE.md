# Execution evidence

## Transport phase source correction — 12 October 2026

The preserved 170-file packaging source is bound to current-manifest SHA256 `a4f5077b50de1e326bc93a52b1563070168a324979d4b3be026dd60abe13e9db`. Main passed 215 unique root methods in seven complete capped groups. Gateway group3 recorded four passes and one failure at the assumed one-request assertion (actual zero); the preceding 2.3-second time bound passed. Subsequent cleanup assertions were not reached, while main independently found no owned processes remaining. Forty-two root methods and all 199 copied repeated methods were still unexecuted at that checkpoint. The original 300-second monolithic timeout remains a failed incomplete result.

A crash group printed OK for four methods in 83.207 seconds before main's disk monitor failed without a supervised exit receipt; the same four-method group later passed with complete receipts in 79.609 seconds. It contributes four unique methods. Neither failed attempt is replaced by the later pass.

This correction preserves those source bytes and records separately bounded startup and confirmed-response test phases. The production transport and Java/domain semantics are unchanged. Its native tests, cleanup, quickstart and complete copy have not run. Guarded pure checks of the fixture and source lineage are reported separately in the source handoff; no native success or exact OS startup attribution is claimed. See [phase timing scope](docs/u2a-packaging.md#transport-phase-correction). Earlier sections below remain historical evidence.

Date: 8 October 2026. M1 and M2 were independently accepted. The corrected M3 candidate has now passed all 165 tests, a separate 21-row read-only regrade, a fresh 216-run comparison and nine clean public-copy commands. Independent application and raw-history checks passed; final documentation review remains pending. Original failures and unscored rows remain unchanged. Decisions: authored/scripted; application model calls: zero. All employee/service fixtures are fictional. See [current local results](#current-local-results-8-october-2026) for the completed results and their limits.

Sections from Source checkpoint through the EL-M3-01 source correction record their checkpoint-time state. Their pending, proposed and unexecuted statements are historical. The frozen M3 document and rubric retain their original wording; the dated section below supplies current execution status.

## Source checkpoint

Implemented source for Java 17 finite offboarding/approval, immutable independent service snapshots and operation receipts, a standard-library XML bridge, Python typed provider loop, four fixtures and independent final-state checks. Source existence is not build or application execution evidence.

At the earlier source checkpoint, only lightweight Python checks had run. The subsequent explicitly granted M1 lease authorized the Java build and finite acceptance commands recorded below. No dependencies were downloaded.

## Actual lightweight checks

Executed from the repository root on Windows with Python 3.11.9:

| Command | Exit | Observed result |
| --- | ---: | --- |
| `py -3.11 dev.py test --suite unit` | 0 | 20 tests, zero failures/errors/skips; 0.230 seconds reported by unittest; no Java process or network launched |
| `py -3.11 --version` | 0 | Python 3.11.9 |
| `git status --short` | 0 | New M1 source/docs/fixtures present as untracked files; generated unit scratch and caches ignored |

The 20 tests comprise ten protocol/input checks, four decision-boundary checks and six independent-verifier checks. The verifier checks include five rejected altered outcomes: enabled login, retained session, retained grant, missing receipt and duplicate business effect. The passing verifier case contains authored synthetic snapshots, not application-generated state.

A source scan for local personal paths/model/API-key identifiers returned no matches in public source/docs. This is a bounded text check, not comprehensive secret detection. There were no failed execution attempts in this checkpoint. No Java version or compilation result has been inferred from Python checks.

## Actual Java and domain checks

Executed sequentially from the repository root under the worker-owned `employee-lifecycle-agent-integration` M1 lease. Raw lease expiry was `2026-10-08T11:12:12.706574+00:00`; JSON string parsing and offset-aware UTC comparison confirmed validity immediately before demo/verification batches. Environment: Windows, Python 3.11.9, OpenJDK/java and javac 17.0.18. Commands completed between approximately 09:44 and 09:46 UTC (15:14–15:16 Asia/Calcutta).

| Exact command | Exit | Observed result |
| --- | ---: | --- |
| `py -3.11 dev.py doctor` | 0 | Selected Java 17/Python 3.11; actual Java source-mode atomic move probe passed; zero downloads |
| `py -3.11 dev.py build` | 0 | `javac --release 17`; six Java sources compiled |
| `py -3.11 dev.py test --suite m1` | 0 | 34 tests in 20.521 seconds; 20 Python unit + 14 actual Java integration tests; zero failures/errors/skips |
| `py -3.11 -m agent.cli demo --scenario offboard-success --provider scripted --run-dir runs/m1-success` | 0 | COMPLETED / REVOKED, 20 independent assertions, five business effects |
| `py -3.11 -m agent.cli demo --scenario offboard-asset-outage --provider scripted --run-dir runs/m1-outage` | 0 | BLOCKED / REVOKED, 16 assertions, three access-reduction effects, three failed asset attempts |
| `py -3.11 -m agent.cli demo --scenario offboard-no-approval --provider scripted --run-dir runs/m1-no-approval` | 0 | AWAITING_APPROVAL / ACTIVE, 11 assertions, zero business effects or domain-service commits |
| `py -3.11 -m agent.cli demo --scenario offboard-restart --provider scripted --run-dir runs/m1-restart` | 0 | COMPLETED / REVOKED, 21 assertions, committed disable receipt recovered after actual owned-process halt, five effects |
| `py -3.11 dev.py verify --run-dir runs/m1-success --expect fixtures/dev/offboard-success/expected.json` | 0 | Direct committed-state verification: 20 assertions |
| `py -3.11 dev.py verify --run-dir runs/m1-outage --expect fixtures/dev/offboard-asset-outage/expected.json` | 0 | Direct committed-state verification: 16 assertions |
| `py -3.11 dev.py verify --run-dir runs/m1-no-approval --expect fixtures/dev/offboard-no-approval/expected.json` | 0 | Additional explicit direct verification: 11 assertions |
| `py -3.11 dev.py verify --run-dir runs/m1-restart --expect fixtures/dev/offboard-restart/expected.json` | 0 | Additional explicit direct verification: 21 assertions |

Success and restart records have login disabled, zero modeled sessions, an empty managed-grant set and exactly one OPEN collection task. Its ID is `collect-E-104-LAP-104`; physical return is explicitly unverified. Outage retains those identity reductions while HR completion remains pending and the collection step is exposed for `asset_operator`. No-approval service snapshots remain at version 1 with their original access state.

The restart run's `recovery-checkpoint.json` independently records the observed post-service-commit/pre-workflow-ack window. The final workflow has `recovered_receipt=disable_login`. Each of five required service actions has one receipt and at most one business effect; repeated-step integration tests also leave version and effect count unchanged.

The real Java integration suite passed DTD/external-entity, nested-depth and duplicate XML rejection; wrong approver/digest, actor approval, absent approval, step order/payload and stale versions were denied. A corrupt committed schema failed closed. The protocol unit checks covered the 64 KiB frame bound and wrong response IDs. No parser restriction was weakened.

## First failed attempt and corrections

The initial PowerShell lease-check command exited 1 with `Lease expired` before any heavy work. The raw expiry was still in the future. The check was corrected to compare explicit UTC epoch values and then to parse the raw JSON timestamp string with Python `datetime.fromisoformat`, preserving its offset; this avoids implicit PowerShell JSON date/culture conversion. The validated checker returned success before execution. This was a coordination preflight failure, not an application test failure.

All M1 application/build/test commands passed on their first execution. No application source correction or acceptance relaxation was needed during this lease.

## Resource and process closeout

Observed command-runtime sum was approximately 38.2 seconds; conservatively report 60 seconds of cumulative active lease use, below ten minutes. Java was launched with `-Xmx256m`, one Java/Python pair at a time. Peak aggregate RSS was not sampled, so memory remains an estimate rather than a measured benchmark.

At 09:46:50 UTC, generated files measured `.build/` 53,592 bytes, `runs/` 193,242 bytes, and ignored coordination checker `work/` 1,256 bytes. Total was under 0.25 MiB at that point. All CLI commands exited; the bridge waits for or terminates its own child. A read-only process inventory found zero Java processes whose command line referenced this repository. No owned background process remains. The worker is release-ready; shared lease release belongs to main.

## Unexecuted checks

* Main independently accepted M1 at 09:58:51 UTC after 18 commands, 34 passing tests, four fresh demos/direct verifiers and 29 additional committed-state checks, including the separate manual approval journey. This acceptance concerns the recorded M1 source, not the later M2 changes.
* Hosted CI, real provider/model API and decision-quality evaluation — unexecuted.
* M2 source checks and subsequent granted Java/domain execution are recorded below; worker execution passed, main M2 acceptance remains pending.

## Limits

Python doubles alone do not establish Java behavior or model quality. The executed four M1 fixtures establish their finite authored integration contracts and one real process-restart window. They are not a held-out model benchmark. One local process with separate service commits is not a network-distributed system. Physical return, production identity/token revocation and power-loss durability are not established.

## M2 source checkpoint — actual lightweight execution

Authorized scope was M2 source and lightweight in-memory Python unit work only.
No Java compilation, doctor/source-mode probe, subprocess/crash suite, full demo
or development/heldout evaluation was run. The released M1 lease was not reused.

Source now includes two finite onboarding bundles; exact approval/payload checks;
owned compensation; authoritative HR replay/supersession fences; cancellation
and persisted budgets; twelve development fixtures; sixteen crash cells;
six real-result corruption controls; and fixed/scripted-adaptive providers with
identical authority and recovery. HTTP/live providers and CI are still M3 work.

Executed sequentially on Windows with Python 3.11.9 from the repository root:

| Exact command / invocation | Exit | Observed result |
| --- | ---: | --- |
| `py -3.11 dev.py test --suite unit` — first M2 run | 0 | 45 reported tests in 0.258 s; loader duplication found afterward |
| `py -3.11 dev.py test --suite unit` — audit-history addition | 1 | 39 tests in 0.404 s; one authored corruption history had a non-incrementing HR version, causing rejection at the version invariant before its intended fence assertion |
| `py -3.11 dev.py test --suite unit` — corrected synthetic history | 0 | 39 unique tests in 0.229 s; no failures/errors/skips |
| `py -3.11 dev.py test --suite unit` — early-enable audit control | 0 | 40 tests in 0.333 s; no failures/errors/skips |
| `py -3.11 dev.py test --suite unit` — final source state | 0 | 40 tests in 0.270 s; no failures/errors/skips |
| `py -3.11 work/freeze_heldout.py` | 0 | Python syntax parsed; 36 inputs/labels and 17 files hashed; first freeze m2-v1; zero scored case-runs |
| `py -3.11 dev.py freeze-check` — m2-v1 | 0 | 36 cases, six groups of six, 17 source/data hashes matched at that point; zero case-runs scored |
| `py -3.11 work/reseal_heldout.py` | 0 | m2-v2 sealed with unchanged inputs/labels; all Python source parsed; 96 tests collected without execution, including exact 12/16/8/6 integration contract counts; zero Java starts |
| `py -3.11 dev.py freeze-check` — m2-v2 | 0 | Final 36 cases and 17 file hashes matched; zero scored case-runs |

The final forty unique unit tests are the twenty M1 Python tests, eleven M2
decision/data-topology checks, two added outcome corruption checks and seven
independent audit-history tests. They use only memory doubles and authored
local snapshots. They do not launch Java or test real provider behavior.

The failed unit check was corrected by making the authored successor fixture's
following HR version increment properly. The intended fence still rejects the
corrupted history. No acceptance invariant was weakened. Duplicate test loading
was removed so denominators describe distinct tests. Two source-write tool
attempts failed before modification (duplicate patch target, then Windows
command-length limit); a staged source file and exact native move completed the
write within the assigned repository.

## M2 frozen inputs and source review revisions

Freeze m2-v1 had manifest SHA-256
`dc1b3f3596d99a5a4a7876d5d8959db61400404fc0f169c7c91a8a1ef07b470b`
and verifier SHA-256
`2d530d9c6d1514939e5fb9f2953dcacc8c06484f6388dd231df1729f5909eab4`.
Afterward, static review found that compensation after enabling an existing
disabled account should also restore its INACTIVE state. The source was fixed
and an unexecuted real Java authority test was authored. Audit checks were
strengthened for owned cleanup and enablement after asset reservation; a
lightweight early-enable corruption test passed. Terminal verification now
preserves a superseded disposition, and trusted successor activation can start
its new budget after an old workflow exhausted its allowance.

The source-checkpoint freeze was m2-v2; m2-v1 is archived under the manifest
history directory. Input and label bytes did not change. Both freezes preceded
any heldout scoring; scored heldout case-runs remain zero. The final manifest
contains exact source hashes and the revision explanation. Authorship and
inspectability limit the holdout; this is not a blind external benchmark.
Source-checkpoint manifest SHA-256 was
`1b90d23295d698e36ac379b2cf0f0a1f63fcd9662320ec3783f23f5ee1841573`;
source-checkpoint verifier SHA-256 was
`72319935459f04e5e0f5f0eb607135107c97790f6875693e7c50ada3d4fd1301`.

## M2 remaining acceptance and resource request at source checkpoint

The authored M2 suite collects 96 tests: 40 lightweight units, 14 M1 integration
regressions, twelve development contracts, sixteen crash cells, eight additional
authority cases and six actual-result corruption controls. Collection is source
inspection, not execution. The planned paired development comparison has
12 cases x 2 modes x 1 repetition = 24 case-runs; it has not run. Every heldout
evaluation, real HTTP provider call and hosted CI run remains unexecuted.

Request a new M2 integration lease for doctor, javac, the M2 suite, four fresh
onboarding demonstrations and paired development comparison, sequentially.
Estimate: one Java/Python pair, JVM Xmx256m, aggregate under 512 MiB, scratch
under 256 MiB, at most ten minutes, zero downloads. These are estimates rather
than measured M2 application resource use. No Java or owned background process
was started in this source phase. Main acceptance of M2 remains pending.

## M2 granted integration — actual execution

Main reviewed the source/rubric and independently ran forty units, freeze check
and all 86 source-checkpoint hashes before dispatching the exact worker-owned
employee-lifecycle-agent-m2-integration lease. Every supervised invocation
rechecked raw JSON owner/slug/milestone/status, offset-aware grant/expiry and
cumulative heavy seconds. Raw expiry was 2026-10-08T12:50:04.799947+00:00.
No released M1 or main-owned lease was consumed.

Environment: Windows, Python 3.11.9, Java/javac 17.0.18. Application commands
ran between 11:22:06 and 11:38:24 UTC on 8 October. There were thirteen actual
invocations of the eleven requested commands, including a repeated build and
full suite after correction. All completed sequentially in the assigned repo.

| Exact command | Exit | Observed result | Wall seconds |
| --- | ---: | --- | ---: |
| `py -3.11 dev.py doctor` | 0 | Selected runtimes and Java atomic-move probe passed; zero downloads | 1.214 |
| `py -3.11 dev.py build` — first attempt | 0 | Six Java sources compiled with release 17 | 1.823 |
| `py -3.11 dev.py test --suite m2` — first attempt | 1 | 96 tests; 95 passed, one restart-budget reporting error; no failures/skips | 228.238 |
| `py -3.11 dev.py build` — correction | 0 | Six Java sources compiled | 1.703 |
| `py -3.11 dev.py test --suite m2` — correction | 0 | All 96 passed; zero failures/errors/skips; unittest reported 212.588 seconds | 212.880 |
| `py -3.11 -m agent.cli demo --scenario onboard-success --provider scripted --run-dir runs/m2-success` | 0 | COMPLETED/ACTIVE, exact role/device, five effects, 174 predicate checks | 3.250 |
| `py -3.11 -m agent.cli demo --scenario onboard-compensation --provider scripted --run-dir runs/m2-compensation` | 0 | COMPENSATED/REVOKED, own new account tombstoned, grants removed, five effects, 193 checks | 6.556 |
| `py -3.11 -m agent.cli demo --scenario onboard-preserve-existing --provider scripted --run-dir runs/m2-preserve` | 0 | COMPENSATED/DISABLED, original account and employee grant preserved, three effects, 195 checks | 6.530 |
| `py -3.11 -m agent.cli demo --scenario onboard-superseded --provider scripted --run-dir runs/m2-superseded` | 0 | SUPERSEDED/REVOKED, successor HR preserved, both old access-addition requests denied, four effects, 153 checks | 3.738 |
| `py -3.11 dev.py evaluate --split dev --modes fixed,scripted-adaptive --repetitions 1 --out runs/m2-development` | 0 | 24/24 exact contracts; fixed 12/12, scripted-adaptive 12/12; tie, no excluded case | 82.683 |
| `py -3.11 dev.py verify --run-dir runs/m2-compensation --expect fixtures/dev/onboard-compensation/expected.json` | 0 | Direct committed-state verification, 193 checks | 0.406 |
| `py -3.11 dev.py verify --run-dir runs/m2-preserve --expect fixtures/dev/onboard-preserve-existing/expected.json` | 0 | Direct committed-state verification, 195 checks | 0.359 |
| `py -3.11 dev.py freeze-check` | 0 | Final m2-v3: 36 cases, six groups of six, 17 file hashes; zero heldout scored | 0.296 |

Predicate counts include checks repeated over immutable generations; they are
not counts of unique unit tests. The ninety-six suite cases comprise forty
Python units, fourteen M1 integration regressions, twelve development contracts,
sixteen actual crash windows, eight additional authority cases and six checks
rejecting corrupted application-generated results. All denominators passed.

## M2 first failed integration and bounded correction

The first suite errored in test_budget_exhaustion_is_persisted_across_restart.
On a fresh actor process with an already exhausted persisted budget, Java
returned ACTOR_BUDGET_EXHAUSTED without the workflow ID. The CLI therefore
raised "No valid workflow obtained" while the durable workflow was already
COMPENSATED. This was a reporting bug, not a reset of the budget or an unsafe
service mutation. Java now returns its authoritative status with that denial,
so the restarted CLI reports the existing disposition. The test still asserts
the unchanged nine-turn budget and unchanged cleanup count.

The finite scenario driver also reuses its one owned actor across consecutive
steps, closing it before operator clock changes. It keeps the same calls,
approval/version/retry rules and outcome comparisons. Crash tests now retain
the actual PID/exit code, exact marker and four pre-recovery snapshots before
temporary directories are cleaned; all sixteen assert exit 91. No fixture label,
approval, budget, retry bound or acceptance assertion was relaxed. The failed
first output and corrected full-suite output are preserved separately.

The changed frozen kernel/driver were sealed as m2-v3 before the corrected
full-suite run. Prior m2-v2 is preserved in manifest history, alongside m2-v1.
Heldout input and label bytes are unchanged from both earlier freezes; no
heldout case was scored. Final manifest SHA-256:
`267a0712e0c7c6e9a9adb47badd939bcf6f626d3eacca83a73b4eb9fe9301bb2`.
Verifier hash remains
`72319935459f04e5e0f5f0eb607135107c97790f6875693e7c50ada3d4fd1301`.
One later documentation patch failed on a wrapped text anchor before editing;
reading the exact current lines resolved it without a runtime/source change.

## M2 crash and paired outcome evidence

Sixteen retained packets contain unique exact markers and exit code 91:

| Action | before_intent | after_intent | after_service_commit | after_result |
| --- | --- | --- | --- | --- |
| disable_login | 91 / matched | 91 / matched | 91 / matched | 91 / matched |
| add_role_grants | 91 / matched | 91 / matched | 91 / matched | 91 / matched |
| create_collection_task | 91 / matched | 91 / matched | 91 / matched | 91 / matched |
| undo_role_grants | 91 / matched | 91 / matched | 91 / matched | 91 / matched |

Each marker is the literal phase:action. Pre-recovery snapshots confirm PENDING
before intent, INTENT before acknowledgement, DONE after result, and a scoped
service receipt only in the two post-commit windows. Fresh processes recover
the same HR/identity/asset domain fields, versions and effect totals as an
uninterrupted reference. A pre-call crash can consume an additional attempt;
attempts remain at most three, and actor/safety budgets never reset. The six
real-result corruption checks reject forbidden grant, restored login, retained
session, duplicated task, hidden required step and missing audit receipt.

The paired comparison scores each case after its actor closes using a separate
Python verifier process. Both providers have the same seeds, operator approvals,
faults, budget and durable safety/recovery. Results per mode:

| Metric | Fixed | Scripted-adaptive |
| --- | ---: | ---: |
| Exact expected outcome | 12/12 | 12/12 |
| Administratively COMPLETED workflows | 4/12 | 4/12 |
| Required forward steps done | 34/60 | 34/60 |
| Incomplete revocation among approved due departures | 0/4 | 0/4 |
| Correct expected unresolved disposition | 8/8 | 8/8 |
| Forbidden committed access effects detected | 0 | 0 |
| Duplicate business effects detected | 0 | 0 |
| False authoritative COMPLETED | 0 | 0 |

Each mode has four COMPLETED, three COMPENSATED, two AWAITING_APPROVAL,
one BLOCKED, one CANCELLED and one SUPERSEDED. These intentional outcomes
explain why exact-contract success is not administrative completion. All twelve
paired outcome results tie. This is one authored deterministic development
repetition, not live-model quality, stochastic variance or a blind benchmark.

## M2 resource closeout and remaining work

Measured cumulative command wall time, including the failed suite and repeated
build, is 549.676 seconds (9 minutes 9.676 seconds), below the ten-minute grant.
This conservatively includes retry waits. Source review/editing and read-only
coordination checks are separate lightweight work. JVM heap cap was Xmx256m;
commands owned one Java process at a time and at most two Python processes when
scoring. A native point sample at 11:25:44 UTC observed one Java plus its Python
parent at 86,945,792 working-set bytes (about 82.9 MiB). This is not peak RSS or
a continuous proof of the 512 MiB estimate.

At 11:39:57 UTC, generated files measured .build 73,725 bytes, runs 5,823,494
bytes and work 191,837 bytes, under 6 MiB combined at that point and below the
256 MiB ceiling. Run totals include prior M1 artifacts. Metadata/report closeout
adds only small files. All supervised commands exited; the 11:39:58 UTC native
inventory found zero repository-owned Java processes. There is no owned
background service. The worker is release-ready; only main releases the shared
lease and supplies independent M2 acceptance.

Heldout scoring (36 cases), real/HTTP/replay provider work, hosted CI,
fresh-copy quickstart and every M3 gate remain unexecuted. There were zero
downloads, live application model calls, external account writes or publication.
Process-restart evidence remains local and synthetic; physical collection,
production token/session revocation and power-loss durability are not established.

## Independent M2 acceptance

Main independently accepted M2 at 2026-10-08 12:00:12 UTC: eleven commands,
96 tests, 830 additional raw-state/history checks, sixteen actual owned-child
exit-91 packets with exact markers, four fresh demonstrations and 24 paired
development case-runs. Both offline policies matched 12/12 expected outcomes.
Main reviewed the retained restart-budget failure and narrow reporting fix,
confirmed all 36 heldout inputs/labels and verifier bytes unchanged, and released
both M2 leases. Earlier pending-acceptance statements above are historical.
Main's initial extra checker assumed every receipt had a nonzero effect; its
corrected checker independently verifies authorized zero-effect no-op commits.
That initial checker failure was retained and did not change application source.

## M3 source-only work and lightweight evidence

M3 source readiness does not constitute M3 acceptance. The assignment permits
source and pure units only before a new M3 lease. No Java process, HTTP server,
heldout scorer, real model, downloaded dependency, hosted CI, copied quickstart,
external account action or publication was started for this source slice.

Added source includes the opt-in Responses adapter, exact-context synthetic
replay, independent raw-state/history metrics, separate M3 scorer, 36-case
paired runner, versioned rubric, public inventory checks, self-contained copied
quickstart and fully pinned prepared CI. Demos/evaluation remain offline.
Java authority, the bounded actor loop and original verifier remain unchanged.
The provider fixture is authored synthetic data; it is not a model recording.

Lightweight commands were run sequentially on Windows, Python 3.11.9, on
8 October 2026. The ignored evidence ledger records exact arguments, offset-aware
UTC times, wall durations, exit codes and complete output under
`work/m3-source-evidence/`. Private authoring helpers are not public runtime
dependencies. They create/reseal source rather than score application cases.

| Command / source check | Exit | Result |
| --- | ---: | --- |
| `py -3.11 work/m3_generate.py` | 0 | Authored two synthetic protocol turns; inventory initially 103 files; zero HTTP requests |
| `py -3.11 dev.py test --suite unit` first attempt | 1 | 77 collected executions, one import error from a closing bracket typo in the new report builder |
| `py -3.11 dev.py test --suite unit` second attempt | 1 | 93 executions, thirteen errors because the authored metric history omitted the ordinary workflow event-sequence field |
| `py -3.11 dev.py test --suite unit` corrected attempt | 0 | 93/93, zero failures/errors/skips; 0.511 seconds reported by unittest |
| `py -3.11 work/m3_syntax.py` initial source collection | 0 | 32 Python AST files; all-suite collection 156 and provider-contract collection 38; no tests executed |
| `py -3.11 work/m3_freeze.py` | 0 | Preserved exact m2-v3 bytes; additive m3-v1 source manifest with 39 files; gold/oracle unchanged |
| `py -3.11 work/m3_generate.py` final inventory | 0 | 108 public files; synthetic fixture reproduced byte-identically |
| `py -3.11 dev.py freeze-check` | 0 | 36 cases, six groups of six, all 39 current hashes and three archived manifests checked; zero scoring |
| `py -3.11 dev.py check-public` | 0 | 108 public files passed bounded inventory/path/credential-shape/Python import-syntax/CI-pin checks |
| `py -3.11 work/m3_syntax.py` final source/rubric collection | 0 | AST and collection counts retained; 36 input/label memberships plus frozen rubric validated without calling an actor or scorer |

The two failed pure-unit attempts and every full output are retained as logs
02 and 03. The first correction fixes report-builder syntax. The second adds
the existing approved event sequence to the authored test's workflow record.
No assertion, real runtime field requirement, frozen label or verifier rule
was relaxed. Three failed documentation patch attempts made no changes because
their exact paragraph anchors did not match; subsequent bounded patches used
the actual lines.

The final 93 units comprise forty accepted M2 pure tests, thirty-one provider
and synthetic replay tests, seventeen metric/oracle controls and five public
inventory/copy controls. Source-only collection includes those 93, the fourteen
M1 Java regressions, forty-two M2 Java contracts and seven loopback HTTP tests:
156 total. The provider-contract suite has 31 pure plus 7 HTTP tests. Collection
does not establish execution of the HTTP or Java additions.

The added controls prove raw counters can expose absent approval, transient
forbidden grants despite a clean final state, superseded enablement, duplicate
aliases, deleted audit, hidden steps, false completion and wrong cleanup owner
in authored histories. They retain metrics when the expected disposition is
wrong, preserve failed/unmeasured main denominators, distinguish exact external
fixture edits and count incomplete revocation in the authored identity outage.
The unchanged verifier also rejects six synthetic final-state corruptions;
six accepted actual-result M2 corruption controls remain in the all suite.

## M3 frozen rubric and unexecuted work

Current manifest: m3-v2,
SHA-256 `55fe73f0ad4de46e824224b2a1a8766f42efd7b6b5f2875c0df46d7ab645eec7`.
The initial M3 manifest m3-v1 is retained byte-for-byte in history with
SHA-256 `22adf24a7def4543df05c3924160ff4b6bafa9ded0e1396af65cd45829f7765a`.
The exact m2-v3 manifest is retained in `evaluation/heldout/history/m2-v3.json`
with SHA-256 `267a0712e0c7c6e9a9adb47badd939bcf6f626d3eacca83a73b4eb9fe9301bb2`;
m2-v1 and m2-v2 remain unchanged. Original input/label lines and complete-file
hashes are unchanged. The verifier remains
`72319935459f04e5e0f5f0eb607135107c97790f6875693e7c50ada3d4fd1301`.

Only three earlier frozen files change: the provider interface adds Clarification
to its type contract; CLI adds manual opt-in/replay routes and protocol hashes;
the finite driver requires actual exit 91 and retains all scheduled crash packets.
The manifest lists additive source/rubric/provider/reproduction/test files.
It does not score, modify gold outcomes or replace the accepted Java guardrails.

Before final checkpoint, source review identified Git EOL conversion as a risk
to exact-byte freeze hashes on different operating systems. `.gitattributes`
now uses `* -text`, following official Git semantics. This is an additive
source portability correction, with no actor/domain/oracle/data changes.
m3-v2 preserves m3-v1 and adds the rule, the bounded public checker for it and
its documented rationale. Private `m3_reseal_eol.py` exited 0; inventory
regeneration exited 0 with 110 files; final freeze-check exited 0 with forty
current hashes and four archives; final check-public exited 0 with 110 files.
All outputs are retained as ledger entries 12–15. A focused five-test pure
public/copy rerun after that source change exited 0 (entry 16). Git's read-only
`git check-attr text -- agent/responses.py evaluation/heldout/inputs.jsonl`
reported text unset for both. Actual cloned Git checkout remains unexecuted.

Main must review `evaluation/rubric.json`, the comparison/scorer/metrics source
and this freeze before first heldout scoring. The planned command is
`py -3.11 dev.py evaluate --split heldout --modes fixed,scripted-adaptive --repetitions 3 --out runs/m3-heldout`:
36 x 2 x 3 = 216 planned runs, 108 per mode and 108 paired outcomes. **Zero have
been executed.** A tie is valid; authored deterministic repeats are not live
model quality or independent statistical samples. Expected blocked identity
or receipt outages must still expose remaining departure access. Expected
cleanup blockage is not a completed onboarding.

Unexecuted commands include new Java doctor/build, `test --suite all`,
`test --suite provider-contract`, the entire heldout comparison and
`fresh-copy --out .build/m3-fresh-copy`. The prepared GitHub Actions workflow
has never run or been published. Its reviewed full pins and runtime versions
are listed in ATTRIBUTION.md. The proposed thirty-minute job bound revises the
original ten-minute estimate using measured M2 time; it remains an estimate
for review. The new local lease request estimates 20–30 active minutes,
512 MiB RAM, 256 MiB generated data, one Java/up to two Python processes and
zero downloads/model calls. No heavy lease is currently consumed.

Public checks are bounded patterns/syntax/import/inventory checks, not a complete
secret scan. Fresh-copy source procedure is prepared, not validated execution.
Optional HTTP source uses a short socket/decision timeout and cannot hard-cancel
a remote request or Python thread. Real API compatibility and model quality,
production permissions/token semantics, distributed transactions, power loss
and physical return remain outside the evidence.

## M3 bounded execution and stopped first comparison

Main accepted the 110-file source and frozen rubric before execution. All public
bytes remained identical to that accepted checkpoint throughout the eight
reviewed commands; only README.md and this evidence document were updated after
the stopped execution. The actor, Java services, original verifier, labels,
provider source, metric source, safety gates, rubric and m3-v2 manifest remain
unchanged. Frozen documents preserve their earlier source-only checkpoint text.

The worker-owned M3 lease granted 30 cumulative active minutes, 512 MiB RAM,
256 MiB new generated data, zero downloads/model calls, at most one Java and two
Python processes. Each command had a retained raw offset-aware lease preflight
and 110-file hash comparison. Execution ran on Windows, Python 3.11.9 and Java
17.0.18 between 14:30:11 and 14:37:13 UTC on 8 October 2026.

| Exact command | Exit | Observed result |
| --- | ---: | --- |
| `py -3.11 dev.py doctor` | 0 | Actual Java source-mode atomic-move probe passed; selected Java/Javac 17.0.18 |
| `py -3.11 dev.py build` | 0 | Six Java sources compiled with release 17 |
| `py -3.11 dev.py test --suite all` | 0 | 156 tests; zero failures/errors/skips; 218.181 seconds reported by unittest |
| `py -3.11 dev.py test --suite provider-contract` | 0 | 38 tests: 31 pure and seven actual credential-free loopback HTTP contracts; zero failures/errors/skips |
| `py -3.11 dev.py freeze-check` | 0 | Forty current file hashes, four preserved archives and all 36 cases checked; no actor or scoring |
| `py -3.11 dev.py check-public` | 0 | All 110 inventory files passed the bounded checks |
| `py -3.11 dev.py fresh-copy --out .build/m3-fresh-copy` | 0 | Exactly 110 public files copied byte-identically; all nine child quickstart commands passed |
| `py -3.11 dev.py evaluate --split heldout --modes fixed,scripted-adaptive --repetitions 3 --out runs/m3-heldout` | -1 | Primary Python deliberately stopped after unexpected H05 failures; partial evidence retained; no automatic rerun |

Complete logs, UTC receipts and preflights are in `work/m3-execution/`. These
ignored evidence files are produced locally, not runtime dependencies or public
source. The timeout HTTP double emitted a server connection-abort traceback
when its client closed the socket; both suites retained that trace and passed
with zero test errors. No real API was contacted. Synthetic replay remains
handwritten protocol evidence, not a model recording or full Java journey.

The copied quickstart used sanitized Python startup environment and only the
public inventory. It passed public/freeze/doctor/build checks, all 93 pure units,
offboarding-success and onboarding-compensation demos, and direct independent
verification of both runs. All nine exact child commands and source hashes are
retained in `work/fresh-copy-evidence/m3-fresh-copy.json`. The copied source
predates these final documentation updates. This is an actual source copy; an
actual Git clone, Linux/macOS run and hosted CI remain unexecuted.

The first comparison is **incomplete**. Its original execution plan remains
36 cases x two modes x three repetitions = 216 planned rows, 108 per mode.
`runs/m3-heldout/rows.jsonl` retains 21 scored rows: 19 pass and two fail. Fixed
has 11 observed rows (ten pass, one fail); scripted-adaptive has ten (nine pass,
one fail). The full planned denominators remain 108 each; the other 195 rows
are unexecuted or unscored, not zero-safe observations. One next directory,
`rep-1/scripted-adaptive/H11-stale-service`, has interrupted committed evidence
and no score. No final comparison report exists. Fast later cases advanced
before the stop took effect; all their rows are retained. No complete rate,
paired winner, tie, repeatability or superiority conclusion is claimed.

Both H05-no-device-disabled modes failed the new `false_authoritative_completion`
gate at 1/1, while the unchanged independent verifier passed all 164 assertions
in each. Raw latest asset state has empty `asset_id`, empty `collection_task`,
`collection_status=NONE` and a scoped zero-effect collection receipt. The frozen
label expects NONE. The unchanged Java asset service returns a verified no-op
when no asset exists. Read-only diagnosis points to `evaluation/metrics.py`
line 183 expecting NOT_REQUIRED for that branch. This is an inferred metric
contract mismatch awaiting main review; the original failed scores remain
unchanged. No source, label, assertion, rubric or gate was tuned after exposure.

Observed administrative completions are six per mode. Required steps completed
are fixed 30/55 and scripted-adaptive 30/50. The retained metric reports incomplete
revocation at 2/5 for fixed and 1/4 for scripted-adaptive; those remaining-access
observations are not hidden by expected dispositions. Observed duplicate effects
are 0/22 per mode, unauthorized service operations 0/30 per mode, receipt-integrity
violations 0/31 fixed and 0/30 adaptive. The completion gate remains 1/6 per mode.
These counts describe only the retained rows. The planned H26 identity outage,
H28 receipt block, H29 cleanup block and scheduled recovery group were not
reached. Their safety or crash results are unmeasured. Zero-opportunity counters
retain 0/0 and JSON null rates.

The eight top-level commands consumed 296.595 seconds cumulatively, including
the stopped comparison. At evidence collection, new generated file bytes were
5,873,286 relative to the pre-lease baseline; no prior runs were deleted. Two
native resource point samples observed at most 215,994,368 bytes aggregate
working set including the supervisor/launcher, one Java and two Python processes.
This is not continuous peak RAM evidence, and heldout RAM was not sampled. The
14:37:38 UTC native inventory found zero remaining workload processes from the
exact retained owned PID set after stopping the primary Python; its child exited.
No background service remains. Final metadata adds small ignored files.

M3 acceptance remains pending. Worker status is correction_needed and
resource_release_ready, with no current resource consumption. Only main releases
the shared lease. Main must inspect the failed scores/raw no-op evidence and
separately authorize any correction or revised scoring; it must also perform its
own copied-source and raw-state acceptance. Hosted CI, live compatibility/model
quality, real accounts, production tokens, power loss and physical returns remain
outside the evidence. No downloads, publication or external writes occurred.

## EL-M3-01 validation-informed scorer correction — source only

Main independently read both H05 raw histories and reproduced the old metric
failure at 14:51:12 UTC on 8 October 2026. Main confirmed empty asset/task,
canonical NONE status, a scoped zero-effect collection receipt, all five DONE
steps, revoked identity access and HR OFFBOARDED. The original verifier passed
164 assertions per mode. Java and the frozen label agreed; metrics.py alone
required the nonexistent NOT_REQUIRED status. Main released the old lease and
authorized this source correction, with no producer scoring or heavy execution.

Before edits, the exact accepted 110-file source, post-execution 110-file source,
old metric, original execution receipts and complete stopped-run directory were
copied and hash-checked under `work/el-m3-01-preservation/`. That preservation
includes all 21 scored rows (19 passes and two failures), the 216-row plan, every
raw snapshot and the next unscored partial directory. Original rows SHA-256 is
`edc751ba3334067e15fcf45b638db8f591c92fa31c7a10228289163a5dfd4582`.
No original result, flag or incomplete-revocation observation was overwritten.

The executable metric change is exactly one literal: the generic empty-asset
branch recognizes NONE. It still requires an empty collection task, revoked
identity, HR OFFBOARDED, five DONE steps and all required scoped receipts.
Unchanged authorization and receipt-integrity gates reject forged receipt
ownership/payload, absent aliases/audit and unreceipted commits. No actor, Java,
provider, label, original verifier, rubric, threshold or other gate changed.
The incomplete-revocation computation is byte-identical.

Nine new pure in-memory methods cover canonical receipted no-device completion;
unknown/malformed status, including NOT_REQUIRED; phantom asset/task; missing
each required scoped receipt or alias; missing no-op audit; forged no-op receipt
owner/payload; remaining access, wrong HR status or hidden pending steps; and
unresolved due departures that retain access. The positive case includes two
authorized zero-effect no-ops and three actual effects. These are authored
synthetic states, not regraded H05 snapshots or new application runs.

| Source / pure command | Exit | Observed result |
| --- | ---: | --- |
| `py -3.11 work/el_m3_01_preserve.py` | 0 | Accepted/current source and stopped evidence copied byte-identically before edits |
| `py -3.11 -m unittest tests.test_metrics_unit.NoAssetCompletionMetricTests -v` first attempt | 1 | Nine methods; two subtest assertions selected the wrong diagnostic counter for later deletion of older receipt aliases |
| Same focused command, corrected authored assertion | 0 | Nine methods pass; 0.011 seconds reported by unittest |
| `py -3.11 dev.py test --suite unit` | 0 | 102 pure methods, zero failures/errors/skips; 0.743 seconds reported by unittest |
| `py -3.11 work/el_m3_01_version.py` | 0 | Archived exact m3-v2; new m3-v3 binding, forty source hashes, five preserved archives, 111 public files |
| `py -3.11 dev.py freeze-check` | 0 | Forty current hashes, all 36 case memberships and five archived manifests validated; no scoring |
| `py -3.11 dev.py check-public` | 0 | 111 public files passed bounded inventory/path/syntax/import/pin checks |
| `py -3.11 work/el_m3_01_syntax.py` | 0 | 32 public Python AST files plus prepared private regrade syntax; collections 102/165/38 without execution |

The failed focused log and its complete test source are retained in
`work/el-m3-01-source-evidence/01-focused.log` and `01-focused-test-source.py`.
Both subcases already failed the overall safety check. The assertion correction
requires a positive receipt-integrity counter: deletion of an older alias after
an authorized commit is an integrity violation, while that historical operation
was authorized. No application change or acceptance relaxation followed the
failed test. Original seventeen metric tests remain unchanged; final collection
is unit 102, all 165 and provider-contract 38. The latter two counts are source
collection only for the corrected candidate, not new Java/HTTP execution.

Manifest m3-v3 SHA-256:
`d16786aeaa27119ad086b2c9ff4943d63bb0ba7a6a2b74d00be14d594fd69431`.
The prior m3-v2 bytes are now also preserved publicly at
`evaluation/heldout/history/m3-v2.json`, still hashing to
`55fe73f0ad4de46e824224b2a1a8766f42efd7b6b5f2875c0df46d7ab645eec7`.
Its only changed frozen file bindings are metrics.py and test_metrics_unit.py.
All data/gold/original-verifier hashes, 36 case memberships, rubric and safety
gates remain exact. Manifest metadata identifies the validation-informed
correction and prior 21-row exposure. Frozen rubric/document source-only wording
remains historical. The corrected source has zero producer runs or original
application-result regrades. This is not a fresh unseen benchmark.

A new named lease is requested only after main's source re-review. It proposes
the corrected full suite, a separately named regrade of exactly the original
21 scored rows, a new 216-row producer regression in
`runs/m3-heldout-regression-v3`, and a corrected public-source quickstart copy.
Prepared private regrade code writes solely to `runs/m3-regrade-original21-v3`,
checks original evidence hashes before/after, retains old flags, requires the
exact new worker-owned offset-aware lease and stops on an unexpected result.
Its source is prepared and syntax-checked only. Regrade results cannot complete
the missing 195 original rows or substitute for the new 216-row comparison.

Proposed limits remain thirty active minutes, 512 MiB RAM, 256 MiB additional
generated data, one Java/up to two Python processes, zero downloads/live calls.
No heavy resource is currently consumed. Old original reports/checkpoints are
preserved; the correction has its own source checkpoint and review notes. Main
owns source acceptance, any new grant and final raw-state/copy acceptance.
Hosted CI, real API compatibility/model quality and production behavior remain
unexecuted. Worker stops for source re-review without launching those proposed
commands.

## Current local results (8 October 2026)

The following results use Windows, Python 3.11.9 and OpenJDK `java`/`javac` 17.0.18. The corrected application, scorer, tests, authored data, labels, rubric and safety gates were unchanged throughout this completed execution. The only subsequent public edits are README and this evidence update; all forty frozen files and manifest m3-v3 remain unchanged. M1 and M2 remain independently accepted. Independent M3 application and saved-history checks passed; final documentation/package acceptance is pending.

### Completed commands and copy checks

| Worker invocation | Exit | Recorded wall seconds | Result |
| --- | ---: | ---: | --- |
| `py -3.11 dev.py doctor` | 0 | 3.111 | Selected runtimes and atomic filesystem probe passed |
| `py -3.11 dev.py build` | 0 | 4.537 | Java source compiled without downloaded dependencies |
| `py -3.11 dev.py test --suite all` | 0 | 224.626 | 165 tests; zero failures, errors or skips; unittest reported 222.441 seconds |
| `py -3.11 dev.py freeze-check` | 0 | 3.288 | 36 cases, forty current hashes and five preserved manifest archives validated |
| Separate read-only audit of the original 21 scored runs | 0 | 6.254 | 21/21 regraded passes, zero new producer runs; separate output `runs/m3-regrade-original21-v3` |
| `py -3.11 dev.py evaluate --split heldout --modes fixed,scripted-adaptive --repetitions 3 --out runs/m3-heldout-regression-v3` | 0 | 755.060 | 216 observed/scored passes, zero failed or unscored rows |
| `py -3.11 dev.py fresh-copy --out .build/m3-scorer-regression-copy` | 0 | 21.795 | 111 public files copied byte-identically; nine copied commands passed |

The 165-test suite includes the 38 provider contracts: 31 pure contracts and seven tests using credential-free local HTTP doubles. These are included counts, not 38 additional tests or a separately repeated corrected provider suite. No real model endpoint was called. The nine copy commands were `check-public`, `freeze-check`, `doctor`, `build`, `test --suite unit` (102 tests), the `offboard-success` and `onboard-compensation` demos, and the corresponding two direct verifiers. Every command exited 0. The copy used no prior run directories, build caches or private helper scripts.

A separate independent reviewer relocated the 111-file public source and ran fourteen commands: all 165 tests, four demos and 210 raw-state assertions passed. The reviewer also independently parsed all 216 saved histories against the frozen authored labels, immutable effects/receipts and due-departure denominators without importing repository code. That saved-history audit is a read-only check of the existing 216 producer runs, not another producer comparison. Repeated suite checks are separate executions of the same 165 tests, not 330 distinct tests.

### Original partial result and separate regrade

The original comparison remains exactly 21 scored rows out of 216 planned: 19 passes and two H05 failures under the original scorer, with 195 rows unscored. The next partial directory and all 948 original raw files remain preserved. Original rows SHA-256 is `edc751ba3334067e15fcf45b638db8f591c92fa31c7a10228289163a5dfd4582`. The original H05 flags were not overwritten.

After the documented no-asset NONE correction, the separate read-only regrade of those same 21 saved runs passed 21/21. It produced no new application runs and does not fill the missing 195 original rows. The fresh 216-run producer comparison is a later, validation-informed regression after prior exposure, not a blind or previously unseen benchmark. The earlier corrected full-suite attempt interrupted by an instrumentation clock fault remains retained: 67 observed OK lines, 98 unfinished tests, no final summary and unknown RAM. The completed execution above does not erase that interrupted attempt or the earlier authored-test failures.

### Fresh comparison denominators

The fresh comparison contains 36 authored cases, two scripted modes and three repetitions: 216 runs, 108 per mode and 108 matched pairs. Every pair tied; there is zero demonstrated advantage for `scripted-adaptive`. Each of the six groups has 18/18 expected-outcome-and-safety passes per mode. Deterministic repetitions do not supply independent statistical evidence.

| Metric | `fixed` | `scripted-adaptive` | Meaning |
| --- | ---: | ---: | --- |
| Exact expected outcome and safety | 108/108 | 108/108 | Includes expected unresolved outcomes |
| Actual administrative completion | 51/108 (47.22%) | 51/108 (47.22%) | Business record actually completed |
| Required steps completed | 312/540 (57.78%) | 312/540 (57.78%) | Completed required steps across all runs |
| Incomplete access revocation | 12/63 (19.05%) | 12/63 (19.05%) | Approved due departures with modeled access remaining |
| Expected unresolved disposition | 57/57 | 57/57 | Expected blockages/handoffs, not administrative completions |
| Observed injected crash windows | 21/21 | 21/21 | Actual owned-child exit 91 with matching markers |
| Expected restart outcome | 18/18 | 18/18 | Recovery outcomes matched the authored contract |

All metrics have 108 measured and zero missing case runs per mode. Zero applicable opportunities use a null rate, not an invented success rate. The safety violation counts and opportunity denominators are identical in both modes: forbidden grants 0/33; unauthorized enablements 0/12; unauthorized service operations 0/351; duplicate effects 0/312; receipt integrity 0/357; compensation ownership 0/36; false authoritative completion 0/51; unsafe departure restoration 0/162. Positive incomplete revocation is reported separately and is not hidden by a passing expected-blockage contract.

Disposition counts per mode are COMPLETED 51, RECEIVED 12, BLOCKED 12, AWAITING_APPROVAL 9, COMPENSATED 6, STALE_APPROVAL 6, SUPERSEDED 3, HANDOFF 3, RECOVERY_BLOCKED 3 and BLOCKED_COMPENSATION 3. An expected BLOCKED, HANDOFF or RECOVERY disposition passing its contract does not mean that employee journey completed.

H26 identity outage and H28 receipt unavailability are approved due offboarding cases. Each has positive incomplete revocation 1/1 in every mode/repetition, even though the expected BLOCKED or RECOVERY_BLOCKED outcome passes. H29 cleanup outage is onboarding with BLOCKED_COMPENSATION, a disabled account and two of five required steps complete. Its departure-only incomplete-revocation metric is 0/0 with a null rate (not applicable); it must not be relabeled offboarding or counted as a successful revocation. The due-departure denominator requires offboarding intent, an approved plan and an effective instant at or before the authoritative as-of instant.

### Runtime, resources and limits

The seven worker command durations sum to 1,018.671 seconds. These recorded wall durations include supervision, launch, execution and cleanup; nested timing is not added a second time. An inclusive accounting upper bound was 1,020.532 seconds. There were 193 memory point samples, approximately five seconds apart. Maximum sampled aggregate memory was 466,808,832 bytes (445.18 MiB), including execution overhead. These samples do not establish continuous peak RSS; commands too short to receive a sample retain unknown memory. Maximum sampled concurrency was two Python and one Java process. The final owned-process cleanup check was clear.

Additional generated files measured 44,586,569 bytes before metadata closeout, below the 256 MiB bound. A conservative closeout accounting including new worker metadata measured 47,342,024 bytes. These are measured generated-byte totals for the recorded slice, not a claim about arbitrary future runs. No downloads, paid calls, real model calls, new credentials or external accounts were used.

All service data and expected labels were authored fictional fixtures, inspectable by the implementer. The original contribution is the bounded lifecycle correctness fixture with independently committed service state, scoped receipts, approval/version fences, owned compensation and reply-loss recovery. It uses standard-library Java and Python; it does not claim a new general workflow engine. Local HTTP doubles and handwritten synthetic replay demonstrate protocol handling, not real-provider compatibility or model quality. Production SSO/token behavior, real accounts, physical laptop return, power loss, damaged storage and distributed services remain unverified. Linux/macOS execution, an actual Git clone, hosted CI, publication and deployment remain unexecuted.

The standalone public quickstart requires only the selected Java 17 JDK and Python 3.11 runtimes. Frozen [M3 evaluation wording](docs/m3-evaluation.md) remains historical; these dated results are the current evidence.

## Public source release — 9 October 2026

All three local MVP milestones passed independent acceptance on 8 October 2026, including final documentation review. The review was executed separately from the implementation worker and included documented quickstarts, meaningful success/failure tests and direct domain-state checks. The results and limitations above remain unchanged.

This source release includes application code, authored fixtures, evaluator/tests, quickstart, architecture, license/attribution and the prepared CI workflow. Private orchestration records, machine-specific paths, runtime caches and generated local runs are excluded. Offline scripted/rule/replay outcomes and local provider doubles do not establish live model quality, employer adoption or production impact. Hosted CI results are available in this repository's Actions tab after publication; historical local reports retain their original execution dates.

## U1 source authoring — 11 October 2026

A bounded offboarding Gateway function-call path is authored with an explicit synthetic local double, exact Java approval, persistent actor/cleanup reservations, owned transport cancellation, independent state verification and sanitized cumulative events. The first pure batch passed 20 tests in 0.177 seconds; the revised final batch passed 22 in 0.099 seconds. Socket/transport-process creation was blocked or mocked. No Java build, socket/process transport contract, full regression, end-to-end demo, fresh-copy execution, live model or external sandbox was run in this source slice. Compilation/integration correctness and measured cleanup remain pending the named lease and independent main review; no upgrade milestone is self-accepted.

The original freeze and all original results above are retained. Changed frozen v1 sources are archived byte-for-byte and referenced by the additive U1 source manifest. Current candidate hashes do not replace v1 evaluation hashes. See [U1 source scope](docs/u1-source.md) for limits and proposed execution commands.

### U1 Windows transport environment correction — 11 October 2026

Under a separate named local lease, the prior U1 candidate passed eight commands: 187 regression/pure methods, 18 Java/HTTP methods and a scripted local-double offboarding demo with 165 independently verified assertions and five effects. No live model or external service was used. Main's independent batch passed `u1-source-check`, then `check-public` exited 1 because four untracked Windows cache databases had appeared below a literal unresolved percent-variable directory during the worker's native run. Main stopped there; the earlier public check preceded that run and did not establish a clean resulting tree.

The child previously received only `SystemRoot`, omitting `SystemDrive`. The corrected child receives a finite Windows runtime directory allowlist, with keys/proxies/Python settings excluded, and retains the same loopback, request, timeout and cleanup limits. Its pure suite passed 24 methods in 0.125 seconds, with zero failures/errors/skips; real child/socket creation was blocked or mocked. One targeted native cache regression is authored but unexecuted. The failure databases were moved to ignored in-repository quarantine with identical hashes, without deletion or a new ignore rule. Manifest `u1-source-2` preserves the exact prior manifest and prior source bytes. Corrected native execution, fresh-copy packaging and main acceptance remain pending. The original 205 passing test methods are historical evidence for the preceding source, not rerun counts or acceptance of this correction.

### Independent local-double U1 acceptance — 12 October 2026

Main accepted source2 at manifest SHA-256 `a77f12e5d28efa97be9850252886417a194bde328fb762ec5e4c168ef5788295`. Twelve independently executed commands all exited 0: source/public checks, doctor/build, 189 regression/pure methods, 19 Java/HTTP methods, two legacy scripted demos, the Gateway local-double demo, its verifier and final public/source checks. There were zero failed/error/skipped tests. A separate direct XML/ledger review passed 260 assertions and five negative controls across nine saved scenarios. The local-double demo retained SCRIPTED fictional approval; modeled revocation, administrative completion and OPEN collection differ from physical laptop return. The original source1 inventory failure and all earlier results remain preserved.

This is U1 local-double acceptance, not live model, external Entra, packaging or final upgrade acceptance. Whole-process-tree memory/process peaks were not measured; owned-child cleanup and total-deadline assertions were exercised. A sanitized copy of the authentic main review, with its original hash, is retained under `evaluation/upgrade/history/u1-source-2-main-review.json`.

### Copied-runtime environment source correction — 12 October 2026

Source3 corrects the separate fresh-copy Python startup environment using the accepted transport's finite Windows runtime policy, plus explicit PATH/JAVA_HOME and Windows COMSPEC/PATHEXT. Keys, proxies and Python startup variables are excluded. Python `-E -s`, copying restrictions, ten copied commands, subprocess deadlines and failure handling are unchanged. The packaging pure suite passed nine methods in 0.033 seconds, including four new environment mapping methods; the existing U1 pure suite passed 24 in 0.117 seconds. Both had zero failures/errors/skips, with child/socket creation blocked or mocked. These 33 pure methods are checks, not 33 business journeys or new native evidence.

The exact source2 manifest and seven changed source2 files are archived separately, and source3 checks both prior revisions and the original v1 freeze. Source2's 208-method acceptance remains bound to its original hashes. No native subprocess contract, build, demo or fresh-copy was run during this source correction. Copied-runtime execution and final packaging remain pending a new main-owned lease and independent review.

### Independent source3 packaging acceptance and later U2-A source — 12 October 2026

Main subsequently accepted source3 packaging at the unchanged original manifest: six outer and ten copied commands, 130 copied methods, 148 copied hashes, 153 direct raw-state assertions and nine negative controls passed. The authentic public review copy and original review identity remain under `evaluation/upgrade/history/`. This acceptance belongs to source3's old inventory. No live model or genuine Entra call was made.

The subsequent additive U2A-source1 injected contract passed 31 guarded pure methods (2.700 seconds suite, 3.2575166 seconds command wall), new source/inventory/diff checks and a 160-file inventory. Four loopback methods were authored and unexecuted. That immutable manifest remains `evaluation/upgrade/u2a-manifest.json`; Java remote outbox/real identity validation and external execution were not implemented or claimed. The worker disclosed that the old CI/fresh-copy gate rejected the enlarged inventory, and main requested this bounded packaging correction.

### Current-source packaging correction — 12 October 2026

`dev.py source-check` now verifies a separate `u2a-packaging-source-1` current manifest, complete public coverage and retained U2A/source3/source2/source1/v1 hashes. Six necessarily changed predecessor files are archived exactly. No historical manifest, main receipt, failed run or evaluation result is overwritten. The approved runtime/environment propagation is unchanged; fresh-copy retains the ten previous commands with the current gate substituted and appends U1 integration/Entra loopback. CI's retained full suite includes Entra pure/loopback and packaging cases.

Guarded `py -3.11 dev.py test --suite packaging-unit` and `py -3.11 dev.py test --suite entra-unit` passed with zero failures/errors/skips, as did `py -3.11 dev.py source-check`. Each pure method guards Popen and socket creation. New cases exercise byte/coverage/inventory/lineage tampering and actual retained command/suite plans. Static public checks on public-byte fixtures run without Git metadata or a child. Counts and source scope are detailed in [the current packaging record](docs/u2a-packaging.md); repetitions of the 31 Entra cases are not new tasks or external effects.

No current Java build, loopback, full suite, runtime quickstart or fresh-copy was executed in this correction. Owned native cleanup, current process-tree peaks, current external integration, hosted CI and final upgrade acceptance remain unverified. The source gate establishes preservation, not runtime correctness or self-acceptance.
