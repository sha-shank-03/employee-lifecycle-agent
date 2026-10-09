# M3 evaluation and reproduction contract

M1 and M2 were independently accepted on the local Windows machine. M3 is
source-ready: pure units pass, while Java/HTTP integration, heldout scoring,
fresh-copy quickstart and hosted CI are unexecuted. Review
[the frozen rubric](../evaluation/rubric.json) before first scoring. Results
must remain absent until execution; the planned 216 runs are not evidence.

## Frozen comparison

Hashes cover exact source/data bytes. `.gitattributes` sets `* -text` to keep
Git from changing line endings on commit or checkout, as documented by
[Git attributes](https://git-scm.com/docs/gitattributes). This preserves hash
semantics across the prepared OS matrix. A source copy preserves bytes directly;
an actual Git clone and hosted matrix remain unexecuted. The first M3 manifest
is archived before the additive byte-preservation correction in m3-v2.

The thirty-six original inputs and labels remain byte-identical. Archives
preserve m2-v1, m2-v2 and m2-v3. The M3 manifest adds the provider, metric,
scorer, runner, rubric, reproduction source and regression fixtures. Java,
the bounded loop and the independent verifier remain unchanged from accepted
M2. Provider/CLI additions and retained multi-crash packets are the narrow
changes to earlier frozen Python source; the manifest records every change.
Any later correction must preserve the old manifest and explain a new version.

Each of six groups has six cases: valid, authority, ordering, recovery, failure
and adversarial. Two offline policies and three deterministic repetitions
produce 216 planned case-runs, 108 per mode and 108 paired comparisons.
Fixed follows declared action ordering; scripted-adaptive follows eligible
step observations. Both use the same approvals, faults, time/version rules,
budgets, recovery and Java safety. A tie is valid. Cases testing malformed
requests, raw authority entry points or injected adversarial providers test
the shared boundary; they do not establish an adaptive policy advantage.

The provider has no file tool and receives neither labels nor case IDs.
The harness invokes `run_case(seed, request, control, ...)`; the label is not
an argument. After all owned Java contexts close, a separate Python scorer
reads expected data and immutable service histories. It executes the unchanged
M2 verifier and the added independent counters. It never trusts actor prose
or calls Java's completion predicate.

Rows, errors, expected blocks and partial evidence remain in the main
denominator. Measurement errors yield null/unmeasured counters, with separate
measured/missing counts. Rates with no opportunities are N/A, represented as
JSON null. The report preserves row files, progressive `rows.jsonl`, paired
outcomes, group counts, dispositions, elapsed time and frozen-manifest hash.
An interrupted run has an execution plan and partial rows, not a completed
216-run report. Existing output directories are never silently reset.

## Outcomes versus remaining safety work

The rubric distinguishes exact expected state, actual administrative completion,
forward steps, expected unresolved states, incomplete revocation, unauthorized
grant/enable/service effects, duplicate effects, receipt integrity, compensation
ownership and false completion. These come from raw state/history even when
the exact expected state is wrong.

The frozen identity-outage case expects enabled login, sessions and grants to
remain with `BLOCKED` and zero service effects. Passing that expected contract
must still report incomplete revocation. The cleanup-outage case expects owned
grants to remain with `BLOCKED_COMPENSATION`; it is not a completed onboarding.
Declared external fixture edits are matched exactly and counted separately from
actor additions. A final empty grant set cannot hide an unauthorized intermediate
addition. Creating a collection task cannot prove physical return.

Crash rows retain actual child exit code 91, PID, exact hook marker and all
pre-recovery snapshots, including both windows in the two-restart case. M3
checks the frozen expected recovered state and absence of unsafe effects. M2's
separate sixteen-window matrix establishes equivalence with uninterrupted
references; do not describe M3's expected-state rate as that stronger comparison.

## Exact planned commands

Run sequentially from the repository root with Python 3.11 and Java 17 JDK.
During the managed local project, every Java/HTTP/fresh-copy/evaluation command
requires a newly granted M3 resource lease. No live provider appears here.

```powershell
py -3.11 dev.py doctor
py -3.11 dev.py build
py -3.11 dev.py test --suite all
py -3.11 dev.py test --suite provider-contract
py -3.11 dev.py freeze-check
py -3.11 dev.py check-public
py -3.11 dev.py fresh-copy --out .build/m3-fresh-copy
py -3.11 dev.py evaluate --split heldout --modes fixed,scripted-adaptive --repetitions 3 --out runs/m3-heldout
```

The pure `unit` suite starts no Java or HTTP server. `provider-contract` includes
actual credential-free loopback HTTP. `all` includes the accepted Java tests,
provider tests and all pure units. Expected source collection: unit 93,
provider-contract 38 and all 156. Collection is not execution.

The fresh-copy command copies only `PUBLIC_FILES.json` inventory entries to an
empty directory under this repository's `.build` or `work`. It excludes Git,
prior builds/runs, local instructions, caches and private working files. Child
commands ignore Python startup environment and user packages, and inherit only
runtime/OS resolution. It runs public/freeze checks, doctor/build, pure units,
successful departure and failed-onboarding compensation demos, then direct
verifiers. It needs no sibling repository or mandatory third-party dependency.
Runtime installations are prerequisites rather than vendored artifacts. The
copy, exact hashes and child logs are retained; it does not rerun heldout scoring.

`check-public` checks inventory completeness, symlinks/path escapes, file bounds,
credential-shaped literals, personal paths, Python syntax/imports and reviewed
full CI action pins. It also compares Git public entries when Git metadata exists.
It is a bounded source check, not comprehensive secret detection or a security
certification. Source-only copies run without Git.

## CI and resource tradeoffs

Prepared GitHub Actions use standard Ubuntu 24.04 and Windows 2022 runners,
read-only contents permission, full action commit pins and maximum parallelism
one. They install selected runtime prerequisites on hosted runners, use no API
credentials, call no model, cache no dependencies and run the offline commands.
No workflow has been pushed, dispatched or executed remotely.

The proposed job timeout is thirty minutes. This revises the plan's ten-minute
estimate: accepted M2's 24 development runs alone took 82.683 seconds; scaling
to 216 plus the full suite, slower failure cases and copied quickstart needs
more headroom. This is a bounded estimate for review, not a measured M3 duration.
The local request estimates twenty to thirty active minutes, JVM Xmx256m,
512 MiB aggregate memory and 256 MiB generated data, one Java and at most two
Python processes while scoring, with zero downloads/model calls. Main may
grant a narrower staged lease; stop before its limit rather than exceeding it.

Standard GitHub-hosted runner compute is free for public repositories under
[GitHub's documented policy](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Private quotas, larger runners and artifact/cache storage have different terms.
The prepared workflow performs no artifact uploads or dependency caching.

The comparison is authored and inspectable, uses finite simulation policy and
deterministic providers, and shares policy/parser helpers in the added metrics.
It is independent from Java execution, not independent data provenance.
Three repeats cannot establish live model quality, uncertainty or production
reliability. Real HTTP compatibility, production SSO/session semantics, real
account permissions, physical returns, damaged storage and power-loss behavior
remain outside the evidence.
