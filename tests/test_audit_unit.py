"""Authored audit histories for in-memory verifier tests; never application evidence."""
from copy import deepcopy
import tempfile
import unittest
from pathlib import Path
from agent.bridge import ROOT
from evaluation.verifier import JOIN, STEPS, field_digest, plan_digest, verify_run
from tests.test_unit import write_snapshot


class AuditHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work", prefix="audit-unit-")
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        employee, workflow = "E-900", "wf-E900-1"
        hr = {"employee_id": employee, "version": "1", "commit_order": "0", "event_id": "join-900",
              "event_sequence": "1", "epoch": "1", "intent": "onboard", "role": "engineer",
              "effective_at": "2020-01-01T00:00:00Z", "administrative_status": "ACTIVE"}
        identity = {"employee_id": employee, "version": "1", "commit_order": "0", "enabled": "false",
                    "sessions": "0", "grants": "", "account_exists": "false", "account_state": "MISSING",
                    "created_by": "", "enabled_by": "", "grants_added_by": "", "added_grants": ""}
        assets = {"employee_id": employee, "version": "1", "commit_order": "0", "asset_id": "",
                  "inventory_id": "POOL-900", "inventory_available": "true", "reserved_by": "",
                  "collection_task": "", "collection_status": "NONE"}
        w = {"workflow_id": workflow, "employee_id": employee, "intent": "onboard", "role": "engineer",
             "epoch": "1", "administrative_status": "RUNNING", "actor_calls": "0", "provider_turns": "0",
             "active_reserved_ms": "0", "safety_calls": "0", "turn_limit": "24",
             **{"step." + a: "PENDING" for a in JOIN}, **{"attempts." + a: "1" for a in JOIN}}
        approved = {"event_id": hr["event_id"], "event_sequence": "1", "epoch": "1", "effective_at": hr["effective_at"],
                    "role": "engineer", "hr_version": "1", "identity_version": "1", "assets_version": "1",
                    "grants": "", "asset_id": "", "account_exists": "false", "enabled": "false", "sessions": "0",
                    "inventory_id": "POOL-900", "inventory_available": "true", "target_grants": "employees,engineering"}
        w.update({"approved." + k: v for k, v in approved.items()})
        w["digest"] = w["approval_digest"] = plan_digest(w)
        w["approval_expires"] = "2027-01-01T00:00:00Z"
        self.histories = {"workflow": [deepcopy(w)], "hr": [deepcopy(hr)], "identity": [deepcopy(identity)], "assets": [deepcopy(assets)]}
        order = 0
        for action, service, changes in (
            ("prepare_account", "identity", {"account_exists": "true", "account_state": "PREPARED", "created_by": workflow}),
            ("add_role_grants", "identity", {"grants": "employees,engineering", "grants_added_by": workflow, "added_grants": "employees,engineering"}),
            ("reserve_asset", "assets", {"asset_id": "POOL-900", "inventory_available": "false", "reserved_by": workflow}),
            ("enable_login", "identity", {"enabled": "true", "account_state": "ACTIVE", "enabled_by": workflow}),
            ("complete_onboarding_hr", "hr", {"administrative_status": "ONBOARDED"}),
        ):
            order += 1
            current = deepcopy(self.histories[service][-1])
            current.update(changes)
            current["version"] = str(int(current["version"]) + 1)
            current["commit_order"] = str(order)
            suffix = "1." + action
            receipt = workflow + "/1/" + action + ":" + field_digest({"digest": w["digest"], "step": action})
            current.update({"ledger." + suffix: receipt, "receipt." + action: receipt,
                            "effect." + suffix: "1", "effects." + action: "1",
                            "audit." + suffix: f"{order}|1|1|onboard|2026-10-08T00:00:00Z|forward"})
            self.histories[service].append(current)
        w.update({"step." + a: "DONE" for a in JOIN})
        w["administrative_status"] = "COMPLETED"
        self.histories["workflow"].append(deepcopy(w))
        self.expected = {"employee_id": employee, "administrative_status": "COMPLETED", "enabled": True, "sessions": 0,
                         "grants": ["employees", "engineering"], "hr_status": "ONBOARDED", "collection_status": "NONE",
                         "collection_task": False, "business_effects": 5, "asset_id": "POOL-900"}

    def write(self):
        for name, history in self.histories.items():
            for index, record in enumerate(history, 1):
                write_snapshot(self.run, name, record, generation=index)

    def test_valid_onboarding_audit_is_independently_verified(self):
        self.write()
        self.assertTrue(verify_run(self.run, self.expected)["passed"])

    def test_final_audit_rewrite_is_rejected(self):
        self.histories["identity"][-1]["audit.1.prepare_account"] = "1|2|2|offboard|2026-10-08T00:00:00Z|forward"
        self.write()
        with self.assertRaisesRegex(AssertionError, "immutable receipts"):
            verify_run(self.run, self.expected)

    def test_old_enable_after_new_hr_event_is_rejected(self):
        successor = deepcopy(self.histories["hr"][0])
        successor.update(version="2", event_sequence="2", epoch="2", intent="offboard", commit_order="3")
        self.histories["hr"].insert(1, successor)
        self.histories["hr"][-1]["version"] = "3"
        self.write()
        with self.assertRaisesRegex(AssertionError, "authoritative event"):
            verify_run(self.run, self.expected)

    def test_expired_forward_commit_is_rejected(self):
        for w in self.histories["workflow"]:
            w["approval_expires"] = "2025-01-01T00:00:00Z"
        self.write()
        with self.assertRaisesRegex(AssertionError, "unexpired"):
            verify_run(self.run, self.expected)

    def test_wrong_payload_receipt_is_rejected(self):
        for record in self.histories["identity"][1:]:
            record["ledger.1.prepare_account"] = "wf-E900-1/1/prepare_account:" + "0" * 64
            record["receipt.prepare_account"] = record["ledger.1.prepare_account"]
        self.write()
        with self.assertRaisesRegex(AssertionError, "payload"):
            verify_run(self.run, self.expected)

    def test_transient_forbidden_grant_is_rejected(self):
        self.histories["identity"][2]["grants"] = "admin,employees,engineering"
        self.write()
        with self.assertRaisesRegex(AssertionError, "forbidden grant"):
            verify_run(self.run, self.expected)

    def test_early_enable_before_asset_reservation_is_rejected(self):
        asset = self.histories["assets"][-1]
        asset["commit_order"] = "6"
        asset["audit.1.reserve_asset"] = "6|1|1|onboard|2026-10-08T00:00:00Z|forward"
        self.write()
        with self.assertRaisesRegex(AssertionError, "prior owned asset"):
            verify_run(self.run, self.expected)

