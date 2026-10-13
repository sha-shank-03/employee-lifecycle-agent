# Employee lifecycle agent

**Current source status (12 October 2026):** Main accepted earlier U1 source2/source3 packaging. On the later 170-file U2-A packaging candidate, seven complete groups passed 215 unique root methods; a Gateway deadline test failed because no HTTP request was observed. The earlier full-suite command also exceeded its 300-second cap. This version preserves that source and both failures, and separates cold startup from confirmed stalled/trickled response checks. Production transport, its deadline reserve, and Java/domain behavior are unchanged. This correction is source/pure only; its native phases, complete fresh-copy and hosted CI remain pending. See [phase timing and packaging limits](docs/u2a-packaging.md#transport-phase-correction) and [Entra contract scope](docs/u2a-entra-contract.md). Live models, genuine Entra and final upgrade acceptance are unexecuted. All v1 results below belong to the published pre-upgrade source.

A local demonstration of approved employee onboarding and offboarding across fictional HR, identity and asset services. Java controls authorization, durable mutations and safety cleanup. A Python provider chooses typed tools in a bounded loop. Offline decisions and demo approvals are **scripted**, with no model API calls.

The original contribution is the business correctness fixture: a departure must revoke modeled access, expose incomplete asset work, and recover a committed step after its reply is lost. Asset failure never restores access. Creating a collection task does not mean a laptop was physically returned.

**Current evidence (8 October 2026):** The corrected candidate passed all 165 tests, including 38 provider contracts, and nine commands in a clean public-source copy. A fresh comparison produced 216 scored runs: both modes matched the exact expected outcome and safety contract in 108/108 runs, with 108 paired ties and no demonstrated adaptive advantage. Actual administrative completion was 51/108 per mode; 12/63 approved due departures retained access. The original comparison remains a failed partial result: 19 passes, two H05 scoring failures and 195 unscored rows. Its separate read-only regrade passed 21/21 without filling the missing rows. Independent application, raw-history and final documentation checks passed; the local MVP is accepted. See [current local results](EVIDENCE.md#current-local-results-8-october-2026) for commands, denominators and limits.

## Windows quickstart

Use Java 17 **JDK** (`java` and `javac`, selected by `JAVA_HOME` or PATH) and Python 3.11. No pip, Maven, Docker, browser or account is required. Run from this repository root:

```powershell
py -3.11 dev.py doctor
py -3.11 dev.py build
py -3.11 dev.py test --suite unit
py -3.11 dev.py source-check
py -3.11 -m evaluation.u2b_catalog_controls
py -3.11 -m agent.cli demo --scenario offboard-success --provider scripted --run-dir runs/demo-departure
py -3.11 -m agent.cli demo --scenario onboard-compensation --provider scripted --run-dir runs/demo-compensation
```

The original v1, U1 source3 and preceding U2A local packaging passed independently in fresh public copies on Windows. U2A's root coverage was 104 current plus 167 unchanged historical methods; its nine copy groups included 208 repeated methods. Main subsequently accepted the first four U2B native slots: two completed departures and two safe joining compensations. [The U2B catalog continuation](docs/u2b-catalog.md) retains those original bindings and predeclares the remaining 18 records/36 policy slots, with an observation-driven deterministic baseline and equal offline boundaries. Remaining workflows and live comparisons are unexecuted. Linux/macOS use `python3.11` in place of `py -3.11`; those platforms and hosted CI remain unexecuted.

The local validation commands are below. The original heldout scorer intentionally refuses the current upgrade source; its frozen results belong to the published v1 commit. The first two exposed U2B records were independently reviewed under their original source. Pure controls run with `py -3.11 dev.py test --suite u2b-unit` or `--suite u2b-catalog-unit`. The standalone `evaluation.u2b_catalog_controls` demo models bookkeeping with synthetic fixtures and explicitly verifies no native outcome. It needs no saved runs, cached classes or private coordination. Production catalog `plan`, `preview`, `init`, `report` and `run` require authentic local native evidence; the repository ships only the redacted historical review and bindings. Missing or altered raw files are rejected. Continuation execution requires a separate matching main grant. No full catalog or live quality/uplift conclusion is available.

```powershell
py -3.11 dev.py test --suite all
py -3.11 dev.py test --suite provider-contract
py -3.11 dev.py check-public
py -3.11 dev.py fresh-copy --out .build/public-copy
py -3.11 dev.py evaluate --split heldout --modes fixed,scripted-adaptive --repetitions 3 --out runs/local-comparison
```

The [frozen rubric](evaluation/rubric.json) and [M3 evaluation contract](docs/m3-evaluation.md) were reviewed before first scoring. Their source-only status statements remain historical freeze contents; [current results](EVIDENCE.md#current-local-results-8-october-2026) record the completed execution. Manifest m3-v3 binds the corrected no-asset metric, archives m3-v2 and retains the original exposure. The completed 216-run comparison is validation-informed after that exposure, using authored fictional cases and deterministic scripts. Repetitions do not establish independent statistical evidence or live model quality. Passing an expected BLOCKED, HANDOFF or RECOVERY outcome does not mean the business workflow completed. The original partial comparison still provides no completed rate or tie conclusion.

Each demo creates a fresh run directory. Reusing a populated directory is rejected; use a different name or the manual `resume` command. The doctor uses Java source-file mode to check atomic moves before the application build. It checks the selected runtimes and local filesystem without installing anything.

For a manual review/approval journey:

```powershell
py -3.11 -m agent.cli init --fixture fixtures/dev/offboard-success --run-dir runs/manual
py -3.11 -m agent.cli submit --request fixtures/dev/offboard-success/request.json --provider scripted --run-dir runs/manual
py -3.11 -m agent.cli review --workflow wf-E104-12 --run-dir runs/manual
py -3.11 -m agent.cli approve --workflow wf-E104-12 --review-file runs/manual/review/wf-E104-12.json --approver hr-reviewer --run-dir runs/manual
py -3.11 -m agent.cli resume --workflow wf-E104-12 --provider scripted --run-dir runs/manual
py -3.11 -m agent.cli report --workflow wf-E104-12 --run-dir runs/manual
```

`submit` exits 2 while awaiting approval. Ordinary `submit`/`resume` exit 2 for unfinished business states, 0 for verified completion and 1 for unexpected errors. A demo exits 0 only when its independent expected contract passes, including an explicitly expected blockage. Test and verifier commands fail on assertion errors.

Inspect `runs/<name>/outcome.json`, `traces/`, `review/` and the immutable XML generation files under `hr/`, `identity/`, `assets/` and `workflow/`. Verify a recorded run independently:

```powershell
py -3.11 dev.py verify --run-dir runs/demo-departure --expect fixtures/dev/offboard-success/expected.json
py -3.11 dev.py verify --run-dir runs/demo-compensation --expect fixtures/dev/onboard-compensation/expected.json
```

## Finite lifecycle scope

One employee, at most sixteen serial HR events/workflows and one local writer per run directory. A trusted fixture supplies an employee ID, authoritative role, event sequence and effective instant. Requests explicitly specify `intent=offboard` or `intent=onboard`; this does not claim general free-text HR interpretation. The actor inspects facts and policy, proposes the fixed plan, waits for the operator's exact approval, selects eligible steps and responds to bounded retry observations.

Five ordered steps disable login, invalidate modeled sessions, remove the approved managed grants, create one collection task and complete the HR administrative record. Approval binds exact employee/event, policy, initial versions, grants, asset and ordered actions. A stale version, changed digest, wrong approver or attempt to add mutation parameters is denied by Java. Agent-mode tools cannot approve, initialize, edit clocks, inject faults or run arbitrary code.

The successful outcome has `access_status=REVOKED` and `administrative_status=COMPLETED`. The asset-outage outcome has `access_status=REVOKED`, `administrative_status=BLOCKED`, an outstanding collection-task step and `responsible_role=asset_operator`. Three persisted attempts bound that outage. HR remains administratively active until collection-task creation succeeds; this does not imply the employee retains access.

Onboarding prepares a disabled account, adds the exact `engineer` or `support` bundle, reserves one fictional laptop, enables login late, then completes HR. Compensation tombstones only a newly prepared account, removes only added grants, and releases only its own reservation. A pre-existing disabled account and its original grants survive. A newer departure fences older onboarding; unsupported rehire requires review. Cancellation stops administrative departure work after the preapproved revocation safety pass.

The `fixed` and `scripted-adaptive` providers use identical authority, approvals, budgets and recovery. The former follows the declared action order; the latter follows eligible-step observations. A tie is plausible in this constrained workflow. Development comparison reports describe deterministic integration, not live model quality. Providers receive neither expected labels nor scenario IDs.

## Architecture and limitations

See [docs/architecture.md](docs/architecture.md) for authority and tradeoffs, [docs/m1-verification.md](docs/m1-verification.md) for M1 checks, [docs/m2-contract.md](docs/m2-contract.md) for accepted lifecycle behavior, [docs/providers.md](docs/providers.md) for optional HTTP and synthetic replay, and [docs/m3-evaluation.md](docs/m3-evaluation.md) for the frozen metrics and copy contract. Read [current local results](EVIDENCE.md#current-local-results-8-october-2026) for subsequent execution evidence.

Default providers are offline scripts. The optional `responses` manual route requires explicit live opt-in, a model ID and existing credentials; it has never made a real call. Synthetic replay is handwritten protocol data, not a recorded model. Demos, evaluation and prepared CI cannot select either a live model or automatic live approval. Hosted workflow execution remains unverified.

The three Java adapters have independent commits but share one local process. XML snapshots are bounded to 4,096 generations and 16 MiB per store, 512 finite fields per snapshot and a 4 MiB snapshot ceiling. These are local demo stores, not a general workflow engine or database. The lock coordinates cooperating local processes. The operator CLI is a fictional authority boundary, not authentication or protection from a same-user arbitrary-code attacker. Fresh run directories are required after the M2 schema extension; no migration of M1 runtime snapshots is provided.

M2 demonstrated sixteen owned-process exits at four phases across identity disable, role grants, collection task creation and owned-grant cleanup, each with exit code 91 and an exact marker. New processes recovered matching domain versions/effects. Power loss, damaged storage, network shares, distributed services, production SSO/token semantics, real accounts and physical collection remain outside the evidence. No production use, live model quality, external adoption or employer endorsement is claimed.

Code and authored fictional fixtures use the [MIT license](LICENSE). Runtime requirements and primary references are recorded in [ATTRIBUTION.md](ATTRIBUTION.md).
