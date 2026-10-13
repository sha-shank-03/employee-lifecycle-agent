# Current-source packaging correction

## Transport phase correction

The current manifest is `u2a-transport-phase-source-1`. It preserves the exact 170-file packaging manifest at SHA256 `a4f5077b50de1e326bc93a52b1563070168a324979d4b3be026dd60abe13e9db` and the nine changed predecessor files under `evaluation/upgrade/u2a-packaging-source-1/`. The read-only current source gate validates that complete predecessor and every earlier lineage. The remaining sections describe the previous packaging checkpoint and retain their historical execution labels.

Main passed 215 unique methods in seven complete groups on the preserved packaging source. Gateway group3 then recorded four passes and one failure: the 2.3-second total time assertion passed, but its assumed HTTP request count was zero. Cleanup assertions after that failure were not reached; main's independent postflight found no owned process. The original 300-second all-suite timeout is also retained. One four-method crash attempt printed OK in 83.207 seconds before the main disk monitor failed; a later monitored run passed in 79.609 seconds. Those are four unique methods, not eight. These outcomes belong to the preserved source, not this corrected candidate.

`OwnedDoubleExchange` remains byte-identical: a two-second cleanup reserve leaves about 0.3 seconds for worker startup/dispatch when a cold request has a 2.3-second total deadline. That source fact does not establish OS startup as the measured cause of the failure. A zero-request outcome cannot prove stalled HTTP response handling.

The corrected native tests distinguish two scopes. A cold-start fixture deliberately holds the child before the unchanged worker runs and requires zero dispatches, timeout, a reaped owned child, and the unchanged 2.3-second total bound with 0.2-second tolerance. Confirmed-response tests first prepare exactly one real worker/request under a separate five-second preparation deadline. The local server must confirm the matching request; trickle additionally requires a flushed first response byte. Only then does the unchanged exchange adopt the same in-flight child under its 2.3-second response/cleanup timer with 0.2-second tolerance. The adoption seam sends no second request and supplies no fake response. Preparation is explicitly excluded from that response timer and recorded separately. The fixture always owns cleanup, even if an assertion fails, with a 1.5-second reap cap; outer native supervision is still required for process creation and OS scheduling.

Cold cancellation keeps its existing less-than-one-second assertion. An additional confirmed-dispatch cancellation case requires one real request, cancellation in less than one second, and owned cleanup. Existing controller cancellation, controller deadline, stalled/trickled response assertions, authority guards and all other tests are retained. No deadline was increased. Real phase execution remains pending a separately granted native lease; pure fake-process/event checks establish fixture and routing logic only. No production provider, Java/kernel/actor, environment, retry or remote connector behavior changed. The twelve logical copied commands and CI command sequence remain intact.

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
