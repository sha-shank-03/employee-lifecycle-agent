# Current-source packaging correction

This source/pure correction replaces the obsolete inventory gate in the current quickstart, prepared CI and fresh-copy command list. It does not change the Entra adapter, remote-dispatch gate, trusted approval/attestation semantics, Java kernel/outbox, provider transport/environment policy, datasets or baseline. Native tests, builds, complete suites and fresh-copy execution have not been run for this version. Hosted CI remains unverified.

The explicit current gate is:

```powershell
py -3.11 dev.py source-check
```

`evaluation/upgrade/current-manifest.json`, version `u2a-packaging-source-1`, hashes every current public file except itself. The gate checks exact inventory coverage, every current byte hash, the unchanged U2A-source1 manifest and all 159 predecessor hashes through exact archives, then source3/source2/source1 and the original v1 freeze. Anchored predecessor manifest hashes and independent U1 review identities cannot be replaced by editing a current hash. The gate is read-only and invokes no child process/socket/Java. Its result proves source preservation, not runtime outcomes or acceptance.

The necessarily changed U2A-source1 files are archived byte-for-byte under `evaluation/upgrade/u2a-source-1/`. No historical manifest or review is resealed. Original `u1-source-check` and `python -m evaluation.u2a_source` remain historical entry points; they intentionally reject a changed current tree. The new gate verifies their retained snapshots. Earlier documentation that described current packaging as mismatched is historical source1 evidence; this correction authors the replacement but still awaits native execution and main review.

## Prepared offline coverage

`dev.py test --suite all` retains every previous domain/provider pattern and adds the guarded Entra pure, literal-loopback Entra and current packaging tests. CI retains doctor/build/full suite, U1 Java/HTTP integration, public checks and fresh-copy, replacing only the obsolete source gate. Both Windows and Ubuntu jobs remain prepared with the reviewed action pins and no paid calls or credentials.

Dedicated suites are inspectable through `dev.test_patterns` without importing or running their modules:

| CLI suite | Contents | Execution status in this correction |
| --- | --- | --- |
| `packaging-unit` | Existing Windows environment/public tests and new current-source tests | Guarded pure checks executed. |
| `entra-unit` | 31 injected Entra methods with Popen/socket guards | Guarded pure checks executed via the new CLI route. |
| `entra-loopback` | Four owned literal-loopback read-only methods | Authored and unexecuted. |
| `u1-integration` | Retained Java/HTTP provider/authority/recovery suite | Unexecuted on current packaging. |
| `unit` / `all` | Retained domain/provider coverage plus new units; `all` also includes HTTP/Entra loopback | Unexecuted on current packaging. |

Fresh-copy first checks the current source seal and public inventory, copies only public bytes, and uses the unchanged approved Windows/runtime environment with Python `-E -s`. All ten previous copied commands remain in order, with `source-check` replacing `u1-source-check`. U1 integration and Entra loopback are appended: twelve copied commands total. Unit discovery includes Entra pure and packaging checks. Both departure/compensation demos, independent domain verifiers and Gateway local-double demo are retained. No tool is downloaded and no remote mode is enabled.

The same per-child 180-second limit and stop-on-nonzero behavior remain. This correction does not claim a new global fresh-copy deadline, hard kill/cleanup guarantee or measured process-tree peak. Future main execution must supervise the complete batch, retain raw outcomes/timings and verify owned cleanup independently.

## Meaningful pure checks

New guarded tests reject current byte tampering, missing manifest coverage, unlisted files, inventory omissions, altered predecessor snapshots even after updating current hashes, replaced anchored manifests, missing archive mappings, path escape, older lineage/review/v1 tampering, and accidental loss of suite/CI/copied command coverage. They inspect the actual command/suite plans, assert retained predecessor commands and run the current CLI gate. Static public checks use temporary public-byte fixtures without Git metadata, so no Git subprocess starts under the Popen guard. These fixture copies run no quickstart, HTTP or Java.

The 31 Entra tests are repeated for the new CLI route; they are the same exposed contract cases, not 31 new tasks or new external evidence. Native/complete-suite/fresh-copy checks remain separately proposed for main review and a named lease. Authentic prior acceptance stays bound to original manifests; this source correction is not self-accepted.
