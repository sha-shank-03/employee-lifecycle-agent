# Employee lifecycle: the original 40-slot catalog

Main independently reviewed 40 historical offline runs: 20 authored synthetic records, two policies and one repetition. The records cover 12 families; eight families are shared across development and capability inputs. They are correlated and label exposed. These results establish local workflow behavior, not unseen or live-model quality.

| Policy | Business completions | Expected safe stops | Median elapsed | p95 elapsed |
|---|---:|---:|---:|---:|
| Observation-driven deterministic v2 | 7/20 | 13/20 | 2,656.5 ms | 6,563 ms |
| Scripted adaptive | 7/20 | 13/20 | 2,554.5 ms | 5,218 ms |

All 20 pairs tie on business completion, expected contract, safety and disposition. No completion uplift was observed. The policies share each pair's input, approval schedule, tools and budget caps; realized consumption can differ. Timings are captured case elapsed times, including harness and cleanup work, from serial batches with the deterministic policy first. The p95 uses nearest rank. These measurements do not establish a causal speed advantage.

The overall result is **14 business completions and 26 expected safe stops**, with no unexecuted, unknown, unexpected failure or timeout slots. Administrative outcomes are 14 COMPLETED, 10 COMPENSATED, six AWAITING_APPROVAL, four BLOCKED, four CANCELLED and two SUPERSEDED. Passing an expected safe-stop contract does not finish the business process. All 40 stored contract and safety checks passed in this authored catalog.

## What the cases show

| Original record | Verified behavior | Business completion |
|---|---|---|
| C06, existing support account | Five committed receipts but four effects. Account preparation is a zero-effect receipt; the existing account is not newly created or owned. | Yes |
| C08, asset outage with existing account | Three effects and six receipts. Cleanup removes only the newly added engineering grant; the original account and `employees` grant survive. | No: safe compensation |
| C09, interrupted departure | The harness injects an owned exit 91 after the login-disable service commit. Receipt-based recovery avoids a duplicate effect, then completes all five steps. | Yes |
| C11, nine-turn budget | The actor stops within the original nine-turn limit. Separate bounded safety cleanup leaves a disabled tombstone, removes owned grants and records failed onboarding. | No: safe compensation |
| C12, superseding event | The harness supplies offboarding event 43 after role grants. The old workflow cleans up owned effects without completing or failing the newer HR event, which remains ACTIVE. | No: superseded |

The approved authority and injected events are synthetic fixture/operator actions. C09's recovery is a kernel/harness integration result, not autonomous model recovery. C12 records four actual policy decisions, eight kernel turns, seven actor calls and three safety calls. Those counters measure different work. D04's original review field `offline_decisions=5` is retained alongside four captured policy decisions and five kernel turns; the original review was not rewritten.

Across the catalog, 140 business effects and 166 committed receipts were checked separately. Zero-effect receipts are not new accounts or business effects. An OPEN collection task does not prove physical equipment return.

## Receipt and source identities

The [compact receipt](../evaluation/receipts/u2b-full40.json) contains the 40 redacted slot rows, input/approval/budget/label digests, policy and family aggregates, counter distinctions and original-review/evidence digests. `metric_counts` stores numerator/denominator pairs in the declared `metric_order`; aggregate rates use summed denominators, with zero denominators remaining null.

| Evidence scope | Historical identity |
|---|---|
| First four slots | `u2b-evaluation-source-1`, manifest beginning `733259be` |
| Remaining 36 slots | `u2b-evaluation-source-2`, manifest beginning `42d998f2` |
| Published packaging checkpoint | `u2b-packaging-source-3`, manifest beginning `ec578a2b`, commit `453a6a2` |
| This projection/documentation checkpoint | `u2c-packaging-source-4`; independent review pending |

The first two execution identities must not be relabeled as source3 or source4 runs. The original intent remains unchanged; its 108-event remainder journal is complete. Current production catalog authority checks remain strict and reject a historical intent under a different source. No completed slot is reopened.

The projection has its own byte hash. Original review hashes bind retained private originals, not this projection. The repository ships no new raw XML, private paths, traces, grants or host details. Public readers can check projection arithmetic, fixture identities and packaging lineage; unshipped native evidence cannot be reconstructed or independently verified here.

## Limits and retained failures

Tokens remain unknown for all 40 slots. Recorded zero offline API charges exclude hardware, human and host costs; real-provider/system cost per successful task is unknown. Resource peaks were sampled, with sampler errors retained, rather than guaranteed lifetime peaks.

Earlier failed native and audit attempts remain recorded. These include the clean-checkout 246-method/26-error failure, the aggregate suite's 180-second exit 124, and the final audit's STAGED assumption corrected to the actual PREPARED state. Metadata corrections did not repeat actors or change outcomes. Audit checks over cumulative evidence are not independent business-task counts.

Live provider quality, a main-held unseen evaluation, actual Entra integration, production impact, final upgrade acceptance and the demo gate remain pending. This is a local evidence checkpoint only.
