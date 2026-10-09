"""Lease-required M2 domain, recovery and safety checks. Cases execute sequentially."""
import contextlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from agent.bridge import BridgeError, JavaBridge, ROOT
from agent.cli import act, approve_review, create_review, demo, initialize, operator, read_json
from agent.protocol import ToolCall
from evaluation.scenarios import advance_to, raw_step
from evaluation.verifier import read_snapshot, verify_run
from tests.test_unit import write_snapshot

PHASES = ("before_intent", "after_intent", "after_service_commit", "after_result")
JOURNEYS = (("offboard-success", "disable_login"), ("onboard-success", "add_role_grants"),
            ("offboard-success", "create_collection_task"), ("onboard-compensation", "undo_role_grants"))


class M2Base(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "work"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix="m2-")
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "run"

    def prepare(self, scenario, approve=True):
        fixture = ROOT / "fixtures/dev" / scenario
        self.workflow = initialize(fixture, self.run)["workflow_id"]
        self.request = read_json(self.run / "request.json")
        act(self.run, self.request)
        if approve:
            _, path = create_review(self.run, self.workflow)
            approve_review(self.run, self.workflow, path, "hr-reviewer")
        return fixture

    def run_demo(self, scenario, directory=None):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(demo(scenario, directory or self.run), 0)


class DevelopmentContracts(M2Base):
    pass


def dev_test(scenario):
    def test(self):
        self.run_demo(scenario)
        verify_run(self.run, read_json(ROOT / "fixtures/dev" / scenario / "expected.json"))
    return test


for scenario in sorted(p.name for p in (ROOT / "fixtures/dev").iterdir() if p.is_dir()):
    setattr(DevelopmentContracts, "test_" + scenario.replace("-", "_"), dev_test(scenario))


class CrashWindowContracts(M2Base):
    def check_window(self, scenario, phase, target):
        reference = Path(self.temp.name) / "reference"
        self.run_demo(scenario, reference)
        fixture = self.prepare(scenario)
        hook = phase + ":" + target
        with self.assertRaises(BridgeError) as crashed:
            advance_to(self.run, self.workflow, crash_hook=hook)
        self.assertEqual((self.run / "crash-fired.marker").read_text().strip(), hook)
        before = read_snapshot(self.run, "workflow")
        service = "assets" if target == "create_collection_task" else "identity"
        seq = read_json(fixture / "seed.json")["event_sequence"]
        committed = "ledger." + str(seq) + "." + target in read_snapshot(self.run, service)
        evidence = {"hook": hook, "marker": (self.run / "crash-fired.marker").read_text().strip(),
                    "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "scenario": scenario,
                    "owned_child_pid": crashed.exception.owned_child_pid,
                    "child_exit_code": crashed.exception.child_returncode,
                    "workflow_before_recovery": before,
                    "services_before_recovery": {n: read_snapshot(self.run, n) for n in ("hr", "identity", "assets")}}
        evidence_path = ROOT / "work/m2-execution/crash-evidence.jsonl"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        with evidence_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(evidence, sort_keys=True) + "\n")
        self.assertEqual(crashed.exception.child_returncode, 91)
        self.assertEqual(committed, phase in {"after_service_commit", "after_result"})
        self.assertEqual(before["step." + target], "DONE" if phase == "after_result" else "INTENT" if phase != "before_intent" else "PENDING")
        act(self.run, self.request)
        expected = read_json(fixture / "expected.json")
        verify_run(self.run, expected)
        left = {n: read_snapshot(self.run, n) for n in ("workflow", "hr", "identity", "assets")}
        right = {n: read_snapshot(reference, n) for n in left}
        for name, keys in {
            "workflow": ("administrative_status", "reason"),
            "hr": ("administrative_status", "version"),
            "identity": ("enabled", "sessions", "grants", "account_exists", "account_state", "version"),
            "assets": ("asset_id", "collection_task", "collection_status", "inventory_available", "version"),
        }.items():
            self.assertEqual({k: left[name][k] for k in keys}, {k: right[name][k] for k in keys})
            self.assertEqual({k: v for k, v in left[name].items() if k.startswith("effect.")},
                             {k: v for k, v in right[name].items() if k.startswith("effect.")})
        for key, value in left["workflow"].items():
            if key.startswith("attempts."):
                self.assertLessEqual(int(value), 3)
        self.assertGreaterEqual(int(left["workflow"]["attempts." + target]), int(right["workflow"]["attempts." + target]))


def crash_test(scenario, phase, step):
    def test(self):
        self.check_window(scenario, phase, step)
    return test


for scenario, step in JOURNEYS:
    for phase in PHASES:
        setattr(CrashWindowContracts, "test_" + step + "_" + phase, crash_test(scenario, phase, step))


class M2AuthorityContracts(M2Base):
    def test_successor_activation_has_its_own_budget_after_old_exhaustion(self):
        self.run_demo("onboard-budget-exhaustion")
        previous = read_snapshot(self.run, "workflow")
        operator(self.run, "import_event", employee_id=previous["employee_id"], event_id="new-departure",
                 event_sequence="13", effective_at="2020-01-01T00:00:00Z", intent="offboard", role="engineer")
        new = operator(self.run, "activate_event", workflow_id=previous["workflow_id"])
        self.assertNotEqual(new["workflow_id"], previous["workflow_id"])
        self.assertEqual(new["provider_turns"], "0")
        request = read_json(self.run / "request.json")
        request["intent"] = "offboard"
        self.assertEqual(act(self.run, request)["administrative_status"], "AWAITING_APPROVAL")
        self.assertEqual(read_snapshot(self.run, "hr")["administrative_status"], "ACTIVE")

    def test_existing_account_restored_after_enable_then_hr_failure(self):
        from evaluation.scenarios import initialize_case
        fixture = ROOT / "fixtures/dev/onboard-preserve-existing"
        seed = read_json(fixture / "seed.json")
        seed.update(asset_outage=False, failure_step="complete_onboarding_hr")
        self.request = read_json(fixture / "request.json")
        self.workflow = initialize_case(seed, self.request, self.run)
        act(self.run, self.request)
        _, path = create_review(self.run, self.workflow)
        approve_review(self.run, self.workflow, path, "hr-reviewer")
        advance_to(self.run, self.workflow)
        identity = read_snapshot(self.run, "identity")
        self.assertEqual((identity["enabled"], identity["grants"], identity["account_state"]), ("false", "employees", "INACTIVE"))
        self.assertEqual(read_snapshot(self.run, "assets")["asset_id"], "")

    def test_cancel_without_approval_has_zero_effects(self):
        self.prepare("onboard-success", approve=False)
        state = operator(self.run, "cancel", workflow_id=self.workflow)
        self.assertEqual(state["administrative_status"], "CANCELLED")
        self.assertEqual([read_snapshot(self.run, n)["version"] for n in ("hr", "identity", "assets")], ["1"] * 3)

    def test_expiry_before_offboard_blocks_mutation(self):
        self.prepare("offboard-success")
        operator(self.run, "advance_clock", workflow_id=self.workflow, seconds="86401")
        self.assertEqual(raw_step(self.run, self.workflow, "disable_login")["code"], "APPROVAL_EXPIRED")
        self.assertEqual(read_snapshot(self.run, "identity")["version"], "1")

    def test_expiry_after_owned_grants_compensates(self):
        self.prepare("onboard-success")
        advance_to(self.run, self.workflow, target="add_role_grants")
        operator(self.run, "advance_clock", workflow_id=self.workflow, seconds="86401")
        self.assertEqual(raw_step(self.run, self.workflow, "reserve_asset")["code"], "APPROVAL_EXPIRED")
        identity = read_snapshot(self.run, "identity")
        self.assertEqual((identity["enabled"], identity["grants"], identity["account_state"]), ("false", "", "TOMBSTONE"))
        self.assertEqual(read_snapshot(self.run, "workflow")["administrative_status"], "COMPENSATED")

    def test_future_departure_does_not_revoke_on_actor_stop(self):
        fixture = ROOT / "fixtures/dev/offboard-success"
        seed = read_json(fixture / "seed.json")
        seed["effective_at"] = "2099-01-01T00:00:00Z"
        from evaluation.scenarios import initialize_case
        self.request = read_json(fixture / "request.json")
        self.workflow = initialize_case(seed, self.request, self.run)
        act(self.run, self.request)
        _, path = create_review(self.run, self.workflow)
        approve_review(self.run, self.workflow, path, "hr-reviewer")
        self.assertEqual(act(self.run, self.request)["administrative_status"], "WAITING_EFFECTIVE_TIME")
        self.assertEqual(read_snapshot(self.run, "identity")["enabled"], "true")

    def test_new_hr_authority_recovers_without_workflow_acknowledgement(self):
        self.prepare("onboard-success")
        advance_to(self.run, self.workflow, target="add_role_grants")
        hr = read_snapshot(self.run, "hr")
        hr.update(event_id="new-departure", event_sequence="13", epoch="2", intent="offboard", version="2", commit_order="3")
        write_snapshot(self.run, "hr", hr, generation=2)
        state = operator(self.run, "report", workflow_id=self.workflow)
        self.assertEqual(state["administrative_status"], "SUPERSEDED")
        self.assertEqual(read_snapshot(self.run, "identity")["grants"], "")
        self.assertEqual(raw_step(self.run, self.workflow, "enable_login")["code"], "STALE_APPROVAL")

    def test_budget_exhaustion_is_persisted_across_restart(self):
        self.run_demo("onboard-budget-exhaustion")
        before = read_snapshot(self.run, "workflow")
        request = read_json(self.run / "request.json")
        act(self.run, request)
        after = read_snapshot(self.run, "workflow")
        self.assertEqual((before["provider_turns"], after["provider_turns"]), ("9", "9"))
        self.assertEqual(before["safety_calls"], after["safety_calls"])
        self.assertEqual(after["administrative_status"], "COMPENSATED")


class RealVerifierCorruptionContracts(M2Base):
    def corrupt(self, service, changes, remove=None):
        self.run_demo("offboard-success")
        state = read_snapshot(self.run, service)
        state.update(changes)
        if remove:
            state.pop(remove)
        files = sorted((self.run / service).glob("[0-9]*.xml"))
        write_snapshot(self.run, service, state, generation=int(files[-1].stem) + 1)
        with self.assertRaises(AssertionError):
            verify_run(self.run, read_json(ROOT / "fixtures/dev/offboard-success/expected.json"))

    def test_forbidden_grant(self): self.corrupt("identity", {"grants": "admin"})
    def test_restored_login(self): self.corrupt("identity", {"enabled": "true"})
    def test_retained_session(self): self.corrupt("identity", {"sessions": "1"})
    def test_duplicate_collection_task(self): self.corrupt("assets", {"collection_task": "collect-E-104-LAP-104,collect-E-104-LAP-104"})
    def test_hidden_required_step(self): self.corrupt("workflow", {"step.complete_hr": "PENDING"})
    def test_missing_audit_receipt(self): self.corrupt("identity", {}, remove="audit.12.disable_login")

