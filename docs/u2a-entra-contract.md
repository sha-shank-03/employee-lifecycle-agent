# U2-A Entra offboarding contract

This is an additive, injected Python contract using fictional objects. Remote dispatch is unconditionally disabled. No token loader, credential presence check, Graph account, live model, or external sandbox call has run. The existing Java kernel, Python agent loop, approved U1 transport, datasets and baseline remain unchanged. This contract is not exposed as a model tool and cannot acknowledge a Java workflow step.

`fixtures/providers/entra-u2a-profile.json` contains one fictional employee-to-user mapping, a tenant/application identity and two group IDs. It has no credential, endpoint override or live mode. The supported subset is precreated cloud Member users attested as non-admin, with at most two static, cloud, security-only, non-role-assignable groups. Guest, synchronized, agent, dynamic, mail-enabled, role-assignable and incomplete objects are denied. Unknown memberships, including directory roles and administrative units, are denied. A null or missing role-assignable flag is conservatively denied; real compatibility with this selected schema remains unverified.

## API and authority boundaries

The primary-source ledger is `evaluation/upgrade/u2a-sources.json`, retrieved 12 October 2026. Vendor facts and local design choices are separate there.

| Intent | Exact Graph v1.0 request | Observation required after a simulated attempt |
| --- | --- | --- |
| Disable account | `PATCH /users/{allowlisted-id}` with only `{"accountEnabled":false}` | The same existing user has `accountEnabled:false`; unrelated selected facts stay unchanged. |
| Revoke sign-in sessions | `POST /users/{allowlisted-id}/revokeSignInSessions`, no body | The same user's `signInSessionsValidFromDateTime` advances strictly; unrelated selected facts stay unchanged. |
| Remove membership | `DELETE /groups/{allowlisted-group}/members/{allowlisted-user}/$ref`, no body | Complete bounded direct membership enumeration excludes the target; the existing user and both supported groups can still be read. |

The `/$ref` suffix is mandatory. Omitting it can delete the user when permissions allow it. This adapter denies that route. [Microsoft membership removal documentation](https://learn.microsoft.com/en-us/graph/api/group-delete-members?view=graph-rest-1.0)

The selected application permissions are `User.Read.All`, `User.EnableDisableAccount.All`, `User.RevokeSessions.All`, `GroupMember.ReadWrite.All` and `Directory.Read.All`. The last permission supports plain app-only `memberOf` and organization/group reads. These vendor permissions are tenant-wide; the local allowlist is an additional restriction, not vendor-enforced per-object IAM. No permission, consent, account, isolation or non-admin status has been validated against a real tenant. Earlier proposed lifecycle-information permission is outside this slice: no lifecycle attributes or HRIS writes are read or changed.

`TrustedAttestation` is an explicit input from future trusted main preflight, bound to profile hash, tenant/application, non-admin users, permission set and expiry. Creating this dataclass is not proof of its claims. Fixture attestation is fictional. `/organization?$select=id` verifies the returned tenant fact in a double; it does not prove application identity or consent. Access tokens remain opaque. `TokenLoader.load(tenant_id, app_id, authority, scope)` is a future main-owned interface retained without invocation; the intended authority is fixed to the configured tenant and scope is Graph `.default`. There is no Authorization header or remote transport implementation. [Microsoft token guidance](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)

`TrustedApproval` binds workflow, profile, exact selected facts, request and expiry, and requires a trusted injected verifier. A digest or model proposal alone is insufficient. Fixture proof is labeled `fictional-java-proof`. Real Java approval verification and a Java-owned remote outbox/acknowledgement protocol are pending. This slice does not change the Java operator API or give the Python agent approval authority.

## Reads, persistence and recovery

Reads are limited to the fixed global Graph host, organization ID, the selected user fields, both groups' selected metadata, and direct `memberOf?$select=id&$top=20`. No beta, cast, indexed filter, transitive expansion, redirects, arbitrary host/port or credential-bearing URL is allowed. Pagination accepts only validated opaque next links for the same user/path, at most three pages of twenty rows, with duplicate/cycle checks. Every group must be allowlisted and explicitly typed. Overflow or incomplete pagination prevents any absence claim. Plain direct membership avoids an advanced-query index assumption; it is not transitive access analysis or a transactional snapshot.

The trusted, single-writer `IntentJournal` persists call reservations and approved pre-state using file fsync and atomic replacement. It binds profile and workflow across restart and permits four intents. It is a local contract prototype, not a Java-owned outbox, distributed lock, cryptographic audit store or power-loss guarantee. Its necessary pre-state contains fictional object IDs; telemetry excludes raw IDs, URLs, bodies, headers, token/error prose and approval proof. Logs expose version, injected mode, fixed diagnostics, HTTP status, hashes and call counts.

`prepare` re-reads the complete bound snapshot before storing `PREPARED` with attempts zero. `reserve_contract_attempt` rechecks approval and the snapshot, then persists attempts one and `UNCERTAIN`. It simulates a crash boundary without sending anything. Duplicate/restarted intent or reservation never resends POST. `dispatch` always raises `REMOTE_DISPATCH_DISABLED`, before transport or token loading. Simulated HTTP 2xx is recorded without acknowledging success. A 404, denial, failed read, unchanged cutoff, partial enumeration or unrelated drift leaves reconciliation inconclusive.

Successful double readback means only `postcondition_observed:true`, with `mutation_attribution:"unknown"` and `all_sessions_stopped:false`. A concurrent actor could produce that state. Session revocation resets a refresh/session cutoff, can take minutes to apply, and does not establish that all existing application access tokens have stopped. These observations are not complete offboarding, physical asset recovery or exactly-once effects. [Microsoft revocation documentation](https://learn.microsoft.com/en-us/graph/api/user-revokesigninsessions?view=graph-rest-1.0)

## Bounds and verification status

There is one serialized injected read, forty persisted calls per journal, 64 KiB per response/journal, sixteen bounded response headers, five seconds per cooperative read and a thirty-second adapter session. The reader receives an absolute deadline; late output is rejected. A synchronous injected callback must honor that deadline: this code cannot kill an uncooperative callback. Restart retains the call cap but does not prove a global elapsed-time cap. The forty-call cap can reject a sequence of all four separately revalidated actions; this slice does not demonstrate a full multi-action remote workflow. Atomic approval/Graph compare-and-set is unavailable here; no ETag precondition is invented.

Reads and mutations have zero automatic retries. HTTP 401/403/429/5xx stop with fixed diagnostics. No Retry-After delay or retry schedule is executed; any future safe read retry must respect that advice, reserve calls and honor a main-owned total deadline. Ambiguous mutations require readback and review, never blind POST replay.

The following source/pure commands were executed locally for this version:

```powershell
py -3.11 -m unittest -v tests.test_entra_u2a_unit
py -3.11 -m evaluation.u2a_source
py -3.11 dev.py check-public
git diff --check
```

The pure suite has 31 methods and guards `subprocess.Popen` and `socket.socket` in every method. It covers trust/approval drift, mandatory reference deletion, schema/type errors, pagination, HTTP denials/throttling/server errors, virtual deadlines, persisted call caps, duplicate/restart handling, simulated lost responses, readback and redaction. Test methods are contract cases, not fresh evaluation tasks, unseen acceptance or observed real-account effects. Native timing/cleanup, peak RAM and external integration remain unmeasured.

Four additional literal-loopback methods are authored in `tests/test_entra_u2a_loopback.py`. They are unexecuted and require a separately named local integration lease:

```powershell
py -3.11 -m unittest -v tests.test_entra_u2a_loopback
```

They use only an owned read-only `127.0.0.1` HTTP server and propose intake/gate, cross-host rejection, simulated lost-response reconciliation and slow-read/cleanup checks. They invoke neither Java nor the token loader and send no Graph mutations. Authored assertions are not observed timings or cleanup evidence.

## Preserved acceptance and current seal

The accepted U1 source3 manifest remains byte-identical at `evaluation/upgrade/u1-manifest.json`; its original 148-file public inventory and independent packaging review are archived under `evaluation/upgrade/`. That main review passed 6 outer/10 copied commands, 130 copied methods and an independent raw-state review. Its acceptance belongs to that historical source, not these new files. Source2 acceptance, source1 failures and all original v1 evidence remain attributable.

`evaluation/upgrade/u2a-manifest.json` seals the new public source independently, excluding only itself. `python -m evaluation.u2a_source` checks this inventory plus original 40 frozen files, exact v1 archives and all source3/source2/source1 hashes. The sole existing source3 file changed by U2-A is `PUBLIC_FILES.json`; its original bytes are archived. The old `dev.py u1-source-check` and old fresh-copy pipeline remain bound to source3 and reject the new inventory. Their updated current-source integration/CI packaging gate is explicitly pending a later assigned slice; do not reseal historical U1 to hide that distinction.

U2-A is source-ready and awaiting independent review. Real attestation/token loading, Java remote outbox integration, native checks, genuine Entra use, fresh datasets/baselines (U2-B), live models, hosted CI and publication remain unexecuted. No production or final upgrade acceptance is claimed.
