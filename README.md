# Employee lifecycle agent

**Evidence checkpoint (13 October 2026):** Main independently reviewed all 40 original offline policy slots across 20 correlated, author-exposed synthetic records and 12 families: **14 business completions and 26 expected safe stops**. Both policies completed 7/20, with 20 paired ties and no observed completion uplift. The first four slots ran under source1 and the next 36 under source2; source3 was the published packaging checkpoint. This source4 documentation/projection checkpoint is pending independent review. See the [case study](docs/u2b-full40.md) and [compact projected receipt](evaluation/receipts/u2b-full40.json). Live models, unseen evaluation, actual Entra integration, final upgrade acceptance and the demo gate remain pending.

A local demonstration of approved employee onboarding and offboarding across fictional HR, identity and asset services. Java controls authorization, durable mutations and safety cleanup. A Python provider chooses typed tools in a bounded loop. Offline decisions and demo approvals are **scripted**, with no model API calls.

The original contribution is the business correctness fixture: a departure must revoke modeled access, expose incomplete asset work, and recover a committed step after its reply is lost. Asset failure never restores access. Creating a collection task does not mean a laptop was physically returned.

**Original v1 evidence (8 October 2026):** The corrected candidate passed all 165 tests, including 38 provider contracts, and nine commands in a clean public-source copy. A fresh comparison produced 216 scored runs: both modes matched the exact expected outcome and safety contract in 108/108 runs, with 108 paired ties and no demonstrated adaptive advantage. Actual administrative completion was 51/108 per mode; 12/63 approved due departures retained access. The original comparison remains a failed partial result: 19 passes, two H05 scoring failures and 195 unscored rows. Its separate read-only regrade passed 21/21 without filling the missing rows. Independent application, raw-history and final documentation checks passed; the local MVP is accepted. See [current local results](EVIDENCE.md#current-local-results-8-october-2026) for commands, denominators and limits.

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

The original v1, U1 source3 and U2A packaging were independently reviewed in local Windows public-source copies. Main checked source3 locally on Windows with 317 full-suite tests, 21 provider-double tests and 12 fresh-copy commands after retaining an initial 180-second aggregate timeout. Those local checks are separate from the historical full catalog and this unpublished source4 candidate. Earlier failed native, packaging and audit attempts remain recorded in [EVIDENCE](EVIDENCE.md).

**Versioned platform evidence:** Source3 at commit `453a6a229aece5611aad568c2faf80bf6725a26d` also passed the hosted Ubuntu 24.04 and Windows Server 2022 workflow: [verified source3 CI run](https://github.com/sha-shank-03/employee-lifecycle-agent/actions/runs/38359201797). macOS validation remains unexecuted. Source4 clean-copy validation, hosted CI and publication remain pending. Unix examples use `python3.11` in place of the Windows `py -3.11` launcher; the prior hosted Ubuntu result is specific to source3.

The preparation statements in sealed [ATTRIBUTION](ATTRIBUTION.md), the workflow's opening comment and preserved tool output are historical text retained for byte provenance. In particular, the local static `check-public` tool's preserved `hosted_ci_executed: false` field does not query hosted CI. Use the versioned evidence above for current platform status; no workflow, attribution or tool bytes were changed to update those earlier statements.

For a public checkout, these commands check packaged bytes, projection arithmetic and pure controls:

```powershell
py -3.11 -B dev.py source-check
py -3.11 -B -m evaluation.u2b_receipt
py -3.11 -B dev.py test --suite receipt-unit
py -3.11 -B -m json.tool evaluation/receipts/u2b-full40.json
```

The receipt is a compact projection of independently reviewed historical observations. Original review hashes refer to retained private originals, not the projection. Public readers can check arithmetic, fixture identities and source lineage; the unshipped native state cannot be reconstructed or independently reverified from this file. Token usage remains unknown for every slot. Recorded zero offline API charges exclude hardware, human and host costs.

The synthetic `evaluation.u2b_catalog_controls` demo is separate from genuine historical evidence. Production catalog `plan`, `preview`, `init`, `report` and `run` still require authentic native evidence and exact historical source identity. Normal current-source catalog checks reject the older intent. No source override or automatic native rerun is provided; all original slots are complete. Existing Java CLI examples are legacy offline references and do not clear the project's demo gate.

These additional commands are available in the current checkout. Builds, integration suites and fresh-copy execution require the appropriate review and resource lease; main owns source4 clean-copy validation.

```powershell
py -3.11 dev.py test --suite all
py -3.11 dev.py test --suite provider-contract
py -3.11 dev.py check-public
py -3.11 dev.py fresh-copy --out .build/public-copy
```

### Historical v1 comparison reference

The archival v1 invocation was `py -3.11 dev.py evaluate --split heldout --modes fixed,scripted-adaptive --repetitions 3 --out runs/local-comparison`. It belongs to the published v1 source and its frozen results. **Do not run it in this source4 checkout:** the original heldout scorer intentionally rejects upgraded source. It is excluded from the current runnable command blocks; no current rerun or missing-result reconstruction is proposed.

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

Default providers are offline scripts. The optional `responses` manual route requires explicit live opt-in, a model ID and existing credentials; it has never made a real call. Synthetic replay is handwritten protocol data, not a recorded model. Demos, evaluation and the offline workflow cannot select either a live model or automatic live approval. Prior source3 hosted Ubuntu/Windows execution is verified in the linked run above; this revised source4 candidate has no hosted result yet. The demo and final acceptance gates remain closed.

The three Java adapters have independent commits but share one local process. XML snapshots are bounded to 4,096 generations and 16 MiB per store, 512 finite fields per snapshot and a 4 MiB snapshot ceiling. These are local demo stores, not a general workflow engine or database. The lock coordinates cooperating local processes. The operator CLI is a fictional authority boundary, not authentication or protection from a same-user arbitrary-code attacker. Fresh run directories are required after the M2 schema extension; no migration of M1 runtime snapshots is provided.

M2 demonstrated sixteen owned-process exits at four phases across identity disable, role grants, collection task creation and owned-grant cleanup, each with exit code 91 and an exact marker. New processes recovered matching domain versions/effects. Power loss, damaged storage, network shares, distributed services, production SSO/token semantics, real accounts and physical collection remain outside the evidence. No production use, live model quality, external adoption or employer endorsement is claimed.

Code and authored fictional fixtures use the [MIT license](LICENSE). Runtime requirements and primary references are recorded in [ATTRIBUTION.md](ATTRIBUTION.md).
