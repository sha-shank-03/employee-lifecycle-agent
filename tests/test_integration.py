"""Lease-required M1 checks: actual Java processes and committed domain records."""
import contextlib
import io
import struct
import tempfile
import unittest
from pathlib import Path
from agent.bridge import BridgeError, JavaBridge, ROOT
from agent.cli import act, approve_review, create_review, demo, initialize, read_json
from agent.protocol import ToolCall, decode_response
from evaluation.verifier import read_snapshot, verify_run
from tests.test_unit import write_snapshot


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / ".build/classes/lifecycle/Main.class").exists():
            raise AssertionError("Build Java first; M1 integration cannot be skipped")

    def setUp(self):
        scratch = ROOT / "work"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix="integration-")
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / "run"
        self.fixture = ROOT / "fixtures/dev/offboard-success"

    def prepare(self, approve=True):
        initial = initialize(self.fixture, self.run)
        self.workflow = initial["workflow_id"]
        self.request = read_json(self.run / "request.json")
        act(self.run, self.request)
        if approve:
            _, path = create_review(self.run, self.workflow)
            approve_review(self.run, self.workflow, path, "hr-reviewer")

    def scenario(self, name):
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(demo(name, self.run), 0)
        return verify_run(self.run, read_json(ROOT / "fixtures/dev" / name / "expected.json"))

    def test_approved_success(self):
        self.assertEqual(self.scenario("offboard-success")["business_effects"], 5)

    def test_asset_outage_preserves_revocation(self):
        self.assertEqual(self.scenario("offboard-asset-outage")["business_effects"], 3)

    def test_no_approval_zero_domain_mutations(self):
        self.assertEqual(self.scenario("offboard-no-approval")["business_effects"], 0)

    def test_real_process_restart_after_commit_before_ack(self):
        self.assertEqual(self.scenario("offboard-restart")["business_effects"], 5)
        checkpoint = read_json(self.run / "recovery-checkpoint.json")
        self.assertTrue(checkpoint["service_committed"])
        self.assertFalse(checkpoint["workflow_acknowledged"])

    def test_actor_approval_tool_denied(self):
        self.prepare(approve=False)
        with JavaBridge(self.run) as bridge:
            result = bridge.request({"tool": "approve", "workflow_id": self.workflow, "digest": "invented", "approver": "hr-reviewer"})
        self.assertEqual(result["code"], "TOOL_NOT_ALLOWED")
        self.assertEqual(read_snapshot(self.run, "identity")["version"], "1")

    def test_execution_requires_approval(self):
        self.prepare(approve=False)
        with JavaBridge(self.run) as bridge:
            result = bridge.call(ToolCall("execute_step", {"workflow_id": self.workflow, "step_id": "disable_login"}))
        self.assertEqual(result["code"], "APPROVAL_REQUIRED")
        self.assertEqual(read_snapshot(self.run, "identity")["enabled"], "true")

    def test_wrong_approver_and_changed_digest_denied(self):
        self.prepare(approve=False)
        packet, path = create_review(self.run, self.workflow)
        with self.assertRaisesRegex(RuntimeError, "APPROVER_DENIED"):
            approve_review(self.run, self.workflow, path, "asset_operator")
        with JavaBridge(self.run, mode="operator") as bridge:
            result = bridge.request({"tool": "approve", "workflow_id": self.workflow, "digest": "0" * 64, "approver": "hr-reviewer"})
        self.assertEqual(result["code"], "APPROVAL_DIGEST_MISMATCH")
        self.assertEqual(read_snapshot(self.run, "identity")["version"], "1")

    def test_step_order_and_unknown_payload_denied(self):
        self.prepare()
        with JavaBridge(self.run) as bridge:
            result = bridge.call(ToolCall("execute_step", {"workflow_id": self.workflow, "step_id": "complete_hr"}))
            injected = bridge.request({"tool": "execute_step", "workflow_id": self.workflow, "step_id": "disable_login", "enabled": "true"})
        self.assertEqual(result["code"], "STEP_PREREQUISITE_DENIED")
        self.assertEqual(injected["code"], "INVALID_ARGUMENTS")

    def test_duplicate_step_does_not_duplicate_effect(self):
        self.prepare()
        with JavaBridge(self.run) as bridge:
            call = ToolCall("execute_step", {"workflow_id": self.workflow, "step_id": "disable_login"})
            self.assertEqual(bridge.call(call)["code"], "OK")
            self.assertEqual(bridge.call(call)["code"], "OK")
        state = read_snapshot(self.run, "identity")
        self.assertEqual(state["version"], "2")
        self.assertEqual(state["effects.disable_login"], "1")

    def test_stale_version_rejects_mutation(self):
        self.prepare()
        state = read_snapshot(self.run, "identity")
        state["version"] = "2"
        state["grants"] = "admin,employees,engineering"
        write_snapshot(self.run, "identity", state, generation=2)  # trusted test's unrelated service edit
        with JavaBridge(self.run) as bridge:
            result = bridge.call(ToolCall("execute_step", {"workflow_id": self.workflow, "step_id": "disable_login"}))
        self.assertEqual(result["code"], "STALE_APPROVAL")
        self.assertEqual(read_snapshot(self.run, "identity")["enabled"], "true")

    def raw_request(self, payload):
        with JavaBridge(self.run) as bridge:
            bridge.process.stdin.write(struct.pack(">I", len(payload)) + payload)
            bridge.process.stdin.flush()
            response = bridge.responses.get(timeout=5)
            if isinstance(response, Exception): raise response
            return decode_response(response, "0")

    def test_java_rejects_dtd_external_entity(self):
        self.prepare(approve=False)
        payload = b'<!DOCTYPE request [<!ENTITY secret SYSTEM "file:///must-not-read">]><request protocol="1" id="1"><field name="tool">&secret;</field></request>'
        self.assertEqual(self.raw_request(payload)["code"], "INVALID_ARGUMENTS")
        self.assertEqual(read_snapshot(self.run, "identity")["version"], "1")

    def test_java_rejects_nested_depth(self):
        self.prepare(approve=False)
        payload = b'<request protocol="1" id="1"><field name="tool"><nested><deep>approve</deep></nested></field></request>'
        self.assertEqual(self.raw_request(payload)["code"], "INVALID_ARGUMENTS")

    def test_java_rejects_duplicate_fields(self):
        self.prepare(approve=False)
        payload = b'<request protocol="1" id="1"><field name="tool">approve</field><field name="tool">report</field></request>'
        self.assertEqual(self.raw_request(payload)["code"], "INVALID_ARGUMENTS")

    def test_corrupt_committed_snapshot_fails_closed(self):
        self.prepare(approve=False)
        (self.run / "identity" / "00000000000000000002.xml").write_text('<snapshot schema="2"/>', encoding="utf-8")
        with JavaBridge(self.run) as bridge:
            with self.assertRaises(BridgeError): bridge.call(ToolCall("inspect_employee", {"employee_id": "E-104"}))


if __name__ == "__main__": unittest.main()
