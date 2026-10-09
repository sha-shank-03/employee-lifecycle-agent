# Authored fictional fixtures

All employees, devices, role bundles, HR events, prose, expected states and
fault schedules are authored under the repository MIT license.

Twelve development directories each separate seed.json, request.json,
driver.json and expected.json. The provider receives only the request and
observations from Java. The operator harness owns approvals, clock/fault
controls and process crash schedules; it reads the expected label only after
the actor ends.

The thirty-six heldout cases are separate inputs/labels under evaluation/heldout
with six cases per documented group. They are inspectable authored data, not
private or externally sourced employee information and not a blind benchmark.
Their hashes and scoring source are frozen before evaluation. No heldout
case has been executed at the M2 source checkpoint.

