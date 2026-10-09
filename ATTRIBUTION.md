# Attribution and provenance

Code, all fictional employee IDs, join/departure events, laptops, role bundles, control schedules, requests and expected development/heldout outcomes are authored for this repository and licensed under MIT. No real employee data, commercial source code or external HR records are included.

Java 17 and Python 3.11 are separately installed prerequisites. No runtime or external library is vendored. Python has the [PSF license and component notices](https://docs.python.org/3.11/license.html). OpenJDK includes [GPL v2](https://raw.githubusercontent.com/openjdk/jdk17u/master/LICENSE) and the [Classpath Exception where designated](https://raw.githubusercontent.com/openjdk/jdk17u/master/ADDITIONAL_LICENSE_INFO); distribution notices remain authoritative.

The following primary sources were read on 8 October 2026. They motivate the project or establish API semantics; the repository's policy is its own fictional design.

* [Databricks People Tech agent engineering posting](https://www.databricks.com/company/careers/engineering---pipeline/staff-fullstack-engineer-agentic-applications-8220840002): onboarding/offboarding, enterprise tool integration, evaluations and human review. No employer endorsement is implied.
* [Microsoft lifecycle workflows](https://learn.microsoft.com/en-us/entra/id-governance/what-are-lifecycle-workflows): established joiner/mover/leaver prior art.
* [Compensating transaction pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction): resumable, application-specific compensation and idempotence.
* [Revocation guidance](https://learn.microsoft.com/en-us/entra/identity/users/users-revoke-access): identity and application-session revocation are distinct. Local sessions represent only the simulator.
* [Java Files](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/file/Files.html), [FileChannel](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/channels/FileChannel.html) and [JAXP security](https://docs.oracle.com/en/java/javase/17/security/java-api-xml-processing-jaxp-security-guide.html): atomic move, flushing/locking and explicit XML parser restrictions.
* [Python subprocess](https://docs.python.org/3.11/library/subprocess.html): bounded trusted child-process management; not a sandbox.

The thirty-six heldout inputs and labels are authored and inspectable, not an external blind benchmark. Their hashes are recorded before evaluation. The two-turn provider replay is handwritten Responses-shaped protocol data under MIT, not a copied or recorded live-model transcript. Heldout scoring has now run locally; see [current local results](EVIDENCE.md#current-local-results-8-october-2026). Live model calls remain unexecuted.

The M3 adapter's protocol design follows [official OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), retrieved on 8 October 2026. It uses Python standard libraries and does not redistribute an SDK or provider model. Compatibility with a real endpoint remains unverified.

Prepared CI pins these MIT-licensed official actions, verified from release commit links and tagged license text on 8 October 2026. They are references for future hosted CI, not locally downloaded dependencies:

| Action | Exact release commit | License |
| --- | --- | --- |
| checkout v5.0.0 | [08c6903cd8c0fde910a37f88322edcfb5dd907a8](https://github.com/actions/checkout/commit/08c6903cd8c0fde910a37f88322edcfb5dd907a8) | [MIT](https://raw.githubusercontent.com/actions/checkout/08c6903cd8c0fde910a37f88322edcfb5dd907a8/LICENSE) |
| setup-python v6.1.0 | [83679a892e2d95755f2dac6acb0bfd1e9ac5d548](https://github.com/actions/setup-python/commit/83679a892e2d95755f2dac6acb0bfd1e9ac5d548) | [MIT](https://raw.githubusercontent.com/actions/setup-python/83679a892e2d95755f2dac6acb0bfd1e9ac5d548/LICENSE) |
| setup-java v5.5.0 | [0f481fcb613427c0f801b606911222b5b6f3083a](https://github.com/actions/setup-java/commit/0f481fcb613427c0f801b606911222b5b6f3083a) | [MIT](https://raw.githubusercontent.com/actions/setup-java/0f481fcb613427c0f801b606911222b5b6f3083a/LICENSE) |

Hosted CI remains unexecuted. The fresh-copy quickstart passed locally; see [current local results](EVIDENCE.md#current-local-results-8-october-2026). Standard public-repository hosted-runner compute is free under [GitHub's billing policy](https://docs.github.com/en/billing/concepts/product-billing/github-actions); private quotas, larger runners and storage have separate terms. The workflow uses no model credentials, paid model, artifact upload or dependency cache. No runtime, binary, vendored library, real employee data or third-party implementation is included.
