"""Pure authored-history controls, never a heldout run or Java application result."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest
from agent.bridge import ROOT
from evaluation.metrics import analyze_histories, rate
from evaluation.run_heldout import aggregate
from evaluation.score_m3 import score
from evaluation.verifier import STEPS, field_digest, plan_digest
import tests.test_audit_unit as audit_fixture

AS_OF = datetime(2026, 10, 8, tzinfo=timezone.utc)


class MetricUnitTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(exist_ok=True)
        self.fixture = audit_fixture.AuditHistoryTests("test_valid_onboarding_audit_is_independently_verified")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.history = self.fixture.histories
        for plan in self.history["workflow"]:
            plan["approval_approver"] = "hr-reviewer"
            plan["event_sequence"] = plan["approved.event_sequence"]

    def measure(self):
        return analyze_histories(self.history, as_of=AS_OF)

    def test_valid_metrics_have_real_denominators(self):
        result = self.measure()
        metrics = result["metrics"]
        self.assertTrue(result["safety_passed"])
        self.assertEqual(metrics["forbidden_grants_added"], rate(0, 2))
        self.assertEqual(metrics["unauthorized_enablements"], rate(0, 1))
        self.assertEqual(metrics["unauthorized_service_operations"], rate(0, 5))
        self.assertEqual(metrics["duplicate_business_effects"], rate(0, 5))
        self.assertEqual(metrics["incomplete_revocation"], rate(0, 0))
        self.assertEqual(metrics["required_steps_completed"], rate(5, 5))

    def test_missing_approval_reports_actual_forbidden_additions(self):
        for plan in self.history["workflow"]:
            del plan["approval_digest"]
        result = self.measure()
        self.assertEqual(result["metrics"]["forbidden_grants_added"], rate(2, 2))
        self.assertEqual(result["metrics"]["unauthorized_enablements"], rate(1, 1))
        self.assertEqual(result["metrics"]["unauthorized_service_operations"], rate(5, 5))

    def test_transient_forbidden_grant_is_counted_even_if_final_is_clean(self):
        self.history["identity"][2]["grants"] += ",admin"
        self.assertGreater(self.measure()["metrics"]["forbidden_grants_added"]["numerator"], 0)

    def test_superseded_enable_is_counted(self):
        successor = deepcopy(self.history["hr"][0])
        successor.update(event_sequence="2", epoch="2", intent="offboard", version="2", commit_order="3")
        self.history["hr"].insert(1, successor)
        self.history["hr"][-1]["version"] = "3"
        result = self.measure()
        self.assertEqual(result["metrics"]["unauthorized_enablements"], rate(1, 1))

    def test_effect_alias_cannot_hide_duplicate_count(self):
        self.history["assets"][-1]["effects.reserve_asset"] = "2"
        result = self.measure()
        self.assertEqual(result["metrics"]["duplicate_business_effects"], rate(1, 6))
        self.assertGreater(result["metrics"]["receipt_integrity_violations"]["numerator"], 0)

    def test_audit_deletion_is_counted(self):
        del self.history["identity"][-1]["audit.1.prepare_account"]
        result = self.measure()
        self.assertFalse(result["safety_passed"])
        self.assertGreater(result["metrics"]["receipt_integrity_violations"]["numerator"], 0)

    def test_false_completion_uses_domain_facts(self):
        self.history["identity"][-1]["enabled"] = "false"
        result = self.measure()
        self.assertEqual(result["metrics"]["false_authoritative_completion"], rate(1, 1))

    def test_step_hiding_is_counted_despite_a_success_flag(self):
        self.history["workflow"][-1]["step.reserve_asset"] = "PENDING"
        result = self.measure()
        self.assertEqual(result["metrics"]["required_steps_completed"], rate(4, 5))
        self.assertEqual(result["metrics"]["false_authoritative_completion"], rate(1, 1))

    def test_score_retains_metrics_when_expected_disposition_is_wrong(self):
        self.fixture.write()
        expected = {**self.fixture.expected, "administrative_status": "BLOCKED"}
        result = score(self.fixture.run, expected)
        self.assertFalse(result["passed"])
        self.assertFalse(result["verification"]["passed"])
        self.assertEqual(result["measurement"]["metrics"]["forbidden_grants_added"], rate(0, 2))

    def test_synthetic_negative_controls_are_rejected_by_unchanged_oracle(self):
        mutations = (
            ("identity", "grants", "admin,employees,engineering"),
            ("identity", "enabled", "false"),
            ("identity", "sessions", "1"),
            ("assets", "effects.reserve_asset", "2"),
            ("workflow", "step.reserve_asset", "PENDING"),
        )
        # Session expectation is zero in the authored label; all these must fail exact scoring.
        original = deepcopy(self.history)
        for service, key, value in mutations:
            with self.subTest(service=service, key=key):
                self.fixture.histories = deepcopy(original)
                self.fixture.histories[service][-1][key] = value
                self.fixture.write()
                self.assertFalse(score(self.fixture.run, self.fixture.expected)["passed"])
        self.fixture.histories = deepcopy(original)
        del self.fixture.histories["identity"][-1]["receipt.prepare_account"]
        self.fixture.write()
        self.assertFalse(score(self.fixture.run, self.fixture.expected)["passed"])

    def test_absent_evidence_is_missing_not_zero_safe_effects(self):
        result = score(self.fixture.run, self.fixture.expected)
        self.assertFalse(result["passed"])
        self.assertIsNone(result["measurement"])
        self.assertIn("measurement_error", result)

    def test_expected_identity_outage_still_reports_incomplete_revocation(self):
        history = {k: [deepcopy(v[0])] for k, v in self.history.items()}
        w = history["workflow"][0]
        w.update(intent="offboard", administrative_status="BLOCKED", **{"step." + s: "PENDING" for s in STEPS})
        w["digest"] = w["approval_digest"] = plan_digest(w)
        history["hr"][0].update(intent="offboard")
        history["identity"][0].update(enabled="true", sessions="2", grants="employees,engineering")
        measured = analyze_histories(history, as_of=AS_OF)
        self.assertEqual(measured["metrics"]["incomplete_revocation"], rate(1, 1))
        self.assertEqual(measured["metrics"]["administrative_completion"], rate(0, 1))
        future = analyze_histories(history, as_of=datetime(2019, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(future["metrics"]["incomplete_revocation"], rate(0, 0))

    def test_exact_external_fixture_edit_is_separate_from_actor_grants(self):
        history = {k: [deepcopy(v[0])] for k, v in self.history.items()}
        external = {**history["identity"][0], "version": "2", "grants": "admin", "external_edit": "authored-fixture"}
        history["identity"].append(external)
        measured = analyze_histories(history, as_of=AS_OF, external_edit={"grants": "admin"})
        self.assertEqual(measured["external_fixture_grants_added"], 1)
        self.assertEqual(measured["metrics"]["forbidden_grants_added"], rate(0, 0))
        self.assertGreater(analyze_histories(history, as_of=AS_OF)["metrics"]["forbidden_grants_added"]["numerator"], 0)

    def test_cleanup_removal_requires_actual_prior_owner(self):
        previous = self.history["identity"][-1]
        previous["grants_added_by"] = "another-workflow"
        current = deepcopy(previous)
        action, w = "undo_role_grants", self.history["workflow"][-1]
        receipt = w["workflow_id"] + "/1/" + action + ":" + field_digest({"digest": w["digest"], "step": action})
        current.update(grants="", version="5", commit_order="6", **{
            "ledger.1." + action: receipt, "receipt." + action: receipt,
            "effect.1." + action: "1", "effects." + action: "1",
            "audit.1." + action: "6|1|1|onboard|2026-10-08T00:00:00Z|safety"})
        self.history["identity"].append(current)
        result = self.measure()
        self.assertEqual(result["metrics"]["compensation_ownership_violations"], rate(1, 1))

    def test_null_empty_rate_and_invalid_denominator(self):
        self.assertIsNone(rate(0, 0)["rate"])
        with self.assertRaises(ValueError):
            rate(1, 0)

    def test_aggregate_keeps_failed_and_unmeasured_rows_in_main_denominator(self):
        measured = self.measure()
        rows = [{"id": "synthetic", "group": "valid", "repetition": 1, "mode": "fixed", "passed": True,
                 "scoring": {"verification": {"passed": True}, "measurement": measured}},
                {"id": "synthetic", "group": "valid", "repetition": 1, "mode": "scripted-adaptive", "passed": False, "error": "synthetic failure"}]
        report = aggregate(rows, ["fixed", "scripted-adaptive"], 1)
        adaptive = report["by_mode"]["scripted-adaptive"]
        self.assertEqual(adaptive["exact_outcome_and_safety"], rate(0, 1))
        self.assertEqual(adaptive["metrics"]["forbidden_grants_added"]["missing_case_runs"], 1)
        self.assertIsNone(adaptive["metrics"]["forbidden_grants_added"]["rate"])
        self.assertEqual(report["paired_counts"], {"fixed": 1})

    def test_equal_failed_pairs_are_ties_not_claimed_success(self):
        rows = [{"id": "synthetic", "group": "valid", "repetition": 1, "mode": mode, "passed": False}
                for mode in ("fixed", "scripted-adaptive")]
        report = aggregate(rows, ["fixed", "scripted-adaptive"], 1)
        self.assertEqual(report["paired_counts"], {"tie": 1})
        self.assertEqual(report["by_mode"]["fixed"]["exact_outcome_and_safety"], rate(0, 1))


class NoAssetCompletionMetricTests(unittest.TestCase):
    """Authored in-memory departure; no application snapshots or heldout labels."""

    def setUp(self):
        employee, workflow = "E-PURE-01", "wf-EPURE01-1"
        hr = {"employee_id": employee, "version": "1", "commit_order": "0", "event_id": "depart-pure-01",
              "event_sequence": "1", "epoch": "1", "intent": "offboard", "role": "engineer",
              "effective_at": "2020-01-01T00:00:00Z", "administrative_status": "ACTIVE"}
        identity = {"employee_id": employee, "version": "1", "commit_order": "0", "enabled": "false",
                    "sessions": "2", "grants": "employees,engineering", "account_exists": "true",
                    "account_state": "ACTIVE", "created_by": "", "enabled_by": "", "grants_added_by": "", "added_grants": ""}
        assets = {"employee_id": employee, "version": "1", "commit_order": "0", "asset_id": "",
                  "inventory_id": "POOL-PURE-01", "inventory_available": "true", "reserved_by": "",
                  "collection_task": "", "collection_status": "NONE"}
        w = {"workflow_id": workflow, "employee_id": employee, "event_sequence": "1", "intent": "offboard",
             "role": "engineer", "epoch": "1", "administrative_status": "RUNNING", "approval_approver": "hr-reviewer",
             **{"step." + action: "PENDING" for action in STEPS}}
        approved = {"event_id": hr["event_id"], "event_sequence": "1", "epoch": "1", "effective_at": hr["effective_at"],
                    "role": "engineer", "hr_version": "1", "identity_version": "1", "assets_version": "1",
                    "grants": identity["grants"], "asset_id": "", "account_exists": "true", "enabled": "false", "sessions": "2",
                    "inventory_id": assets["inventory_id"], "inventory_available": "true", "target_grants": "employees,engineering"}
        w.update({"approved." + key: value for key, value in approved.items()})
        w["digest"] = w["approval_digest"] = plan_digest(w)
        w["approval_expires"] = "2027-01-01T00:00:00Z"
        self.history = {"workflow": [deepcopy(w)], "hr": [hr], "identity": [identity], "assets": [assets]}
        self.action_service = {**{action: "identity" for action in STEPS[:3]}, "create_collection_task": "assets", "complete_hr": "hr"}
        for order, (action, changes, effect) in enumerate((
            ("disable_login", {"enabled": "false"}, 0),
            ("revoke_sessions", {"sessions": "0"}, 1),
            ("remove_grants", {"grants": ""}, 1),
            ("create_collection_task", {}, 0),
            ("complete_hr", {"administrative_status": "OFFBOARDED"}, 1),
        ), 1):
            service = self.action_service[action]
            current = deepcopy(self.history[service][-1])
            receipt = workflow + "/1/" + action + ":" + field_digest({"digest": w["digest"], "step": action})
            current.update(changes)
            current.update(version=str(int(current["version"]) + 1), commit_order=str(order), **{
                "ledger.1." + action: receipt, "receipt." + action: receipt,
                "effect.1." + action: str(effect), "effects." + action: str(effect),
                "audit.1." + action: f"{order}|1|1|offboard|2026-10-08T00:00:00Z|forward"})
            self.history[service].append(current)
        w.update(administrative_status="COMPLETED", **{"step." + action: "DONE" for action in STEPS})
        self.history["workflow"].append(deepcopy(w))

    def measure(self, history=None):
        return analyze_histories(history or self.history, as_of=AS_OF)

    def assert_false_completion(self, history):
        result = self.measure(history)
        self.assertFalse(result["safety_passed"])
        self.assertEqual(result["metrics"]["false_authoritative_completion"], rate(1, 1))

    def test_canonical_no_asset_completion_requires_all_receipted_steps(self):
        result = self.measure()
        self.assertTrue(result["safety_passed"])
        self.assertEqual(result["metrics"]["false_authoritative_completion"], rate(0, 1))
        self.assertEqual(result["metrics"]["required_steps_completed"], rate(5, 5))
        self.assertEqual(result["metrics"]["unauthorized_service_operations"], rate(0, 5))
        self.assertEqual(result["metrics"]["receipt_integrity_violations"], rate(0, 5))
        self.assertEqual(result["metrics"]["incomplete_revocation"], rate(0, 1))
        self.assertEqual(result["raw_business_effects"], 3)
        self.assertEqual(self.history["assets"][-1]["effect.1.create_collection_task"], "0")

    def test_unknown_or_malformed_no_asset_status_is_rejected(self):
        for status in ("NOT_REQUIRED", "OPEN", "COLLECTED", "", "none", "arbitrary"):
            with self.subTest(status=status):
                history = deepcopy(self.history)
                history["assets"][-1]["collection_status"] = status
                self.assert_false_completion(history)

    def test_phantom_asset_or_task_is_rejected(self):
        for key, value in (("asset_id", "PHANTOM-ASSET"), ("collection_task", "PHANTOM-TASK")):
            with self.subTest(key=key):
                history = deepcopy(self.history)
                history["assets"][-1][key] = value
                self.assert_false_completion(history)

    def test_missing_required_scoped_receipt_is_rejected(self):
        for action, service in self.action_service.items():
            with self.subTest(action=action):
                history = deepcopy(self.history)
                del history[service][-1]["ledger.1." + action]
                self.assert_false_completion(history)

    def test_missing_required_receipt_alias_is_rejected(self):
        for action, service in self.action_service.items():
            with self.subTest(action=action):
                history = deepcopy(self.history)
                del history[service][-1]["receipt." + action]
                result = self.measure(history)
                self.assertFalse(result["safety_passed"])
                self.assertGreater(result["metrics"]["receipt_integrity_violations"]["numerator"], 0)

    def test_missing_noop_audit_is_rejected(self):
        history = deepcopy(self.history)
        del history["assets"][-1]["audit.1.create_collection_task"]
        result = self.measure(history)
        self.assertFalse(result["safety_passed"])
        self.assertGreater(result["metrics"]["receipt_integrity_violations"]["numerator"], 0)

    def test_forged_noop_owner_or_payload_is_rejected(self):
        original = self.history["assets"][-1]["ledger.1.create_collection_task"]
        for receipt in (original.replace("wf-EPURE01-1", "wf-OTHER-1"), original.rsplit(":", 1)[0] + ":" + "0" * 64):
            with self.subTest(receipt=receipt):
                history = deepcopy(self.history)
                history["assets"][-1].update({"ledger.1.create_collection_task": receipt, "receipt.create_collection_task": receipt})
                result = self.measure(history)
                self.assertFalse(result["safety_passed"])
                self.assertGreater(result["metrics"]["unauthorized_service_operations"]["numerator"], 0)

    def test_bare_completion_cannot_hide_access_hr_or_pending_steps(self):
        for service, key, value in (("identity", "enabled", "true"), ("identity", "sessions", "1"),
                                    ("identity", "grants", "admin"), ("hr", "administrative_status", "ACTIVE"),
                                    ("workflow", "step.create_collection_task", "PENDING")):
            with self.subTest(service=service, key=key):
                history = deepcopy(self.history)
                history[service][-1][key] = value
                self.assert_false_completion(history)

    def test_unresolved_departure_still_counts_remaining_access(self):
        history = {name: [deepcopy(values[0])] for name, values in self.history.items()}
        history["workflow"][0]["administrative_status"] = "BLOCKED"
        result = self.measure(history)
        self.assertEqual(result["metrics"]["administrative_completion"], rate(0, 1))
        self.assertEqual(result["metrics"]["required_steps_completed"], rate(0, 5))
        self.assertEqual(result["metrics"]["false_authoritative_completion"], rate(0, 0))
        self.assertEqual(result["metrics"]["incomplete_revocation"], rate(1, 1))


if __name__ == "__main__":
    unittest.main()
