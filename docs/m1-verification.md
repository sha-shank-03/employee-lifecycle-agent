# M1 verification contract

Four authored fictional fixtures establish integration contracts, not a held-out model benchmark:

| Case | Expected administrative state | Login/sessions/grants | Asset task | Business effects |
| --- | --- | --- | --- | ---: |
| Success | COMPLETED | Disabled / zero / empty | One OPEN collection task | 5 |
| Asset outage | BLOCKED | Disabled / zero / empty | None; unresolved asset operator work | 3 |
| No approval | AWAITING_APPROVAL | Original enabled / two / original grants | None | 0 |
| Restart | COMPLETED | Disabled / zero / empty | One OPEN task; disable receipt recovered | 5 |

The verifier reads the latest committed XML snapshots directly, checks exact HR, access and task state, effect counters and required receipts. It does not invoke Java's completion predicate or trust model prose. Expected fixture files are read by the harness after the actor run; providers receive only the request and allowlisted tool observations. Implementer-authored data is not externally blind evaluation.

Python unit tests reject actor approval calls, supplied mutation payloads, oversized frames, hostile XML as markup, duplicate JSON, mismatched response IDs and nested/DTD responses. Local typed provider doubles prove malformed decisions and a false success draft cannot execute a tool. Verifier mutation tests retain access or sessions, remove receipts or duplicate an effect; every altered output must fail verification.

The lease-required integration suite launches actual Java processes. Besides all four fixture cases it rejects unapproved execution, actor approval, wrong approver, changed digest, out-of-order steps, supplied payloads, unrelated service version changes, DTD/XXE, nested XML and duplicate XML fields. Repeated completed steps must leave the business effect counter and service version unchanged. A corrupt committed schema must fail instead of falling back to earlier state.

The restart fixture arms an out-of-band test hook for the owned Java process only. The process exits after the identity snapshot commits but before the workflow acknowledges it. The harness first confirms disabled identity plus an unacknowledged intent, then starts a new Java process. The independent checker requires a recovered receipt and exactly one effect per required operation. This covers one named crash window. The wider matrix is deferred.

No real model/provider HTTP contract or decision-quality evaluation occurs in M1. Free hosted CI and a baseline/held-out benchmark are planned in later milestones and have not run. Current command results and failures belong in `EVIDENCE.md`; source presence alone cannot pass these checks.
