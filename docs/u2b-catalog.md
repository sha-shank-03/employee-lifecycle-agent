# U2B catalog accounting and public evidence

The original 20 records and 40 policy slots are complete. Main reviewed 14 business completions and 26 expected safe stops under the original execution identities. See the [case study](u2b-full40.md) and [projected receipt](../evaluation/receipts/u2b-full40.json) for outcomes, comparisons and limits. This source4 checkpoint changes documentation, static projection checks and packaging lineage only. Actors, scoring, Java, inputs/gold, approvals and budgets are unchanged.

## Original design and identities

The first D01/D07 slice contains four slots under source1: two completed departures and two safe joining compensations. Its original 274-file evidence binding and main review remain unchanged. The source2 catalog predeclared the other 18 records and 36 slots before actor entry. Its 108-event journal now contains the completed STARTED, CAPTURED and CLASSIFIED sequence for those 36 slots. The same 20 correlated author-exposed synthetic records span 12 families; they are not 40 independent problems or an unseen evaluation.

Later source3 packaging fixed a fresh-checkout unit-test dependency on private native files. Main executed the final native slices in explicitly reviewed historical source2 windows and restored source3 afterward. This projection checkpoint preserves source1, source2 and source3 separately; no old intent, event, result or source identity is rewritten.

## Durable entry and stop rules

The production catalog remains at `runs/u2b-catalog-20261012`. Initialization rejects an existing or partial registry. Every slot publishes STARTED before actor entry, then CAPTURED with actor return/failure/timeout, elapsed time, decision digest and raw-file hashes before classification. Independent scoring follows after actor bridges close. A draft or exit zero cannot confer success.

Failed, timed-out, unknown, unexpected or incomplete entries stop before another slot. Started slots cannot replay, including a partially executed pair; no replacement population is created. Reports recheck captured raw bindings and stored verdicts without invoking an actor or filling missing classifications. Pending writes and crash locks remain for review. Publishing uses an exclusive pending file, flush, file fsync and rename. This is process-interruption accounting, not a portable Windows power-loss guarantee.

Exact source, dataset, input, approval, budget, intent, state and cached class bindings remain required. Historical intent under current source is rejected by design. No public projection, synthetic fixture or convenience override substitutes for genuine native evidence. There are no unstarted slots left to schedule.

## Public checks

```powershell
py -3.11 -B dev.py source-check
py -3.11 -B -m evaluation.u2b_receipt
py -3.11 -B dev.py test --suite receipt-unit
py -3.11 -B dev.py test --suite u2b-catalog-unit
py -3.11 -B -m evaluation.u2b_catalog_controls
```

The receipt checker validates projected arithmetic, known input/approval/budget/label identities, counter consistency and source attribution using public files. It explicitly reports that private raw state was not verified and native outcomes were not reexecuted. The original review digests refer to private originals, not the projection's byte identity.

Catalog unit controls and the standalone control demo use explicit synthetic bookkeeping fixtures and no saved native run. Their modeled counts are not historical business evidence. Production `plan`, `preview`, `init`, `report` and `run` still require authentic original files and exact historical source context; a redacted review alone is insufficient. These commands are not a fresh-checkout reproduction of the completed 40 slots.

## Boundaries

Both offline policies complete 7/20 with 20 paired ties and no completion uplift. Safe stops preserve authority and business invariants while leaving work unfinished. Actual policy decisions, kernel turns, direct harness actions, actor tools, safety calls, effects and zero-effect receipts remain distinct. D04's old review field of five is preserved beside four actual decisions and five kernel turns. C09 crashes and C12 superseding events are harness supplied, not autonomous model behavior.

Tokens are unknown for every slot. Offline API charges are recorded as zero; system and live-provider costs remain unknown. Serial timing and sampled resource peaks are descriptive. Actual Entra, live/unseen comparison, final acceptance and the demo gate remain pending. Prior failed source, packaging, preentry, native and audit receipts remain retained under their original identities.
