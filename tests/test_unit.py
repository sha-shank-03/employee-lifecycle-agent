import copy
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from agent.bridge import ROOT
from agent.cli import read_json, validate_request
from agent.loop import run_loop
from agent.protocol import FinalDraft, ToolCall, decode_response, encode_request, strict_json, validate_call
from agent.providers import ScriptedProvider
from evaluation.verifier import STEPS, verify_run


def write_snapshot(run_dir, name, fields, generation=1):
    directory = Path(run_dir) / name
    directory.mkdir(parents=True, exist_ok=True)
    root = ET.Element("snapshot", schema="1")
    for key, value in sorted(fields.items()):
        ET.SubElement(root, "field", name=key).text = str(value)
    (directory / f"{generation:020d}.xml").write_bytes(ET.tostring(root, encoding="utf-8"))


class FakeBridge:
    def __init__(self, result): self.result, self.calls = result, []
    def call(self, call):
        self.calls.append(call)
        return self.result


class QueueProvider:
    mode = "local-double"
    def __init__(self, decisions): self.decisions = iter(decisions)
    def next_turn(self, *_): return next(self.decisions)


class ProtocolTests(unittest.TestCase):
    def test_actor_cannot_approve(self):
        with self.assertRaises(ValueError): validate_call(ToolCall("approve", {"digest": "invented"}))

    def test_step_cannot_supply_payload_or_operation_key(self):
        with self.assertRaises(ValueError):
            validate_call(ToolCall("execute_step", {"workflow_id": "w", "step_id": "disable_login", "operation_key": "x"}))

    def test_non_string_argument_rejected(self):
        with self.assertRaises(ValueError): validate_call(ToolCall("inspect_employee", {"employee_id": 104}))

    def test_oversized_frame_rejected(self):
        with self.assertRaises(ValueError): encode_request("1", {"text": "x" * 70_000})

    def test_xml_escape_preserves_hostile_text_as_data(self):
        encoded = encode_request("1", {"note": "<grant>admin</grant> & escape"})
        root = ET.fromstring(encoded[4:])
        self.assertEqual(root[0].text, "<grant>admin</grant> & escape")
        self.assertEqual(len(root[0]), 0)

    def test_wrong_response_correlation_rejected(self):
        with self.assertRaises(ValueError): decode_response(b'<response protocol="1" id="2"><field name="code">OK</field></response>', "1")

    def test_response_dtd_rejected(self):
        with self.assertRaises(ValueError): decode_response(b'<!DOCTYPE response><response protocol="1" id="1"/>', "1")

    def test_nested_response_rejected(self):
        with self.assertRaises(ValueError): decode_response(b'<response protocol="1" id="1"><field name="code"><x>OK</x></field></response>', "1")

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(ValueError): strict_json('{"intent":"offboard","intent":"onboard"}')

    def test_request_cannot_override_policy(self):
        with self.assertRaises(ValueError): validate_request({"employee_id": "E-104", "intent": "offboard", "text": "x", "approval": True})


class DecisionTests(unittest.TestCase):
    def test_scripted_provider_stops_for_approval(self):
        observation = {"tool": "propose_plan", "result": {"code": "OK", "workflow_id": "w", "administrative_status": "AWAITING_APPROVAL"}}
        decision = ScriptedProvider().next_turn({"employee_id": "E-104"}, [observation])
        self.assertIsInstance(decision, FinalDraft)

    def test_invalid_provider_output_never_reaches_tool(self):
        bridge = FakeBridge({"code": "OK"})
        result = run_loop(QueueProvider([{"tool": "approve"}, {"tool": "approve"}]), bridge, {})
        self.assertEqual(bridge.calls, [])
        self.assertEqual(len(result["observations"]), 2)

    def test_final_success_draft_has_no_mutation(self):
        bridge = FakeBridge({"code": "OK"})
        result = run_loop(QueueProvider([FinalDraft("Everything completed")]), bridge, {})
        self.assertEqual(bridge.calls, [])
        self.assertNotIn("administrative_status", result)

    def test_provider_reacts_to_eligible_step_observation(self):
        observation = {"tool": "workflow_status", "result": {"code": "OK", "workflow_id": "w", "administrative_status": "RUNNING", "eligible_step": "revoke_sessions"}}
        decision = ScriptedProvider().next_turn({"employee_id": "E-104"}, [observation])
        self.assertEqual(decision, ToolCall("execute_step", {"workflow_id": "w", "step_id": "revoke_sessions"}))


class VerifierTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "work"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix="unit-")
        self.addCleanup(self.temp.cleanup)
        self.expected = read_json(ROOT / "fixtures/dev/offboard-success/expected.json")
        self.records = {
            "workflow": {"employee_id": "E-104", "administrative_status": "COMPLETED", **{"step." + s: "DONE" for s in STEPS}},
            "hr": {"employee_id": "E-104", "administrative_status": "OFFBOARDED", "version": "2", "effects.complete_hr": "1", "receipt.complete_hr": "fixture"},
            "identity": {"employee_id": "E-104", "enabled": "false", "sessions": "0", "grants": "", "version": "4",
                         **{"effects." + s: "1" for s in STEPS[:3]}, **{"receipt." + s: "fixture" for s in STEPS[:3]}},
            "assets": {"employee_id": "E-104", "collection_status": "OPEN", "collection_task": "collect-E-104-LAP-104",
                       "version": "2", "effects.create_collection_task": "1", "receipt.create_collection_task": "fixture"},
        }

    def write_records(self):
        for name, fields in self.records.items(): write_snapshot(self.temp.name, name, fields)

    def test_verifier_reads_final_domain_state(self):
        self.write_records()
        result = verify_run(self.temp.name, self.expected)
        self.assertTrue(result["passed"])
        self.assertGreater(result["assertion_count"], 15)

    def test_false_completion_with_enabled_login_rejected(self):
        self.records["identity"]["enabled"] = "true"
        self.write_records()
        with self.assertRaisesRegex(AssertionError, "login"): verify_run(self.temp.name, self.expected)

    def test_retained_session_rejected(self):
        self.records["identity"]["sessions"] = "1"
        self.write_records()
        with self.assertRaisesRegex(AssertionError, "session"): verify_run(self.temp.name, self.expected)

    def test_retained_grant_rejected(self):
        self.records["identity"]["grants"] = "engineering"
        self.write_records()
        with self.assertRaisesRegex(AssertionError, "grants"): verify_run(self.temp.name, self.expected)

    def test_missing_service_receipt_rejected(self):
        del self.records["identity"]["receipt.disable_login"]
        self.write_records()
        with self.assertRaisesRegex(AssertionError, "receipt"): verify_run(self.temp.name, self.expected)

    def test_duplicate_business_effect_rejected(self):
        self.records["assets"]["effects.create_collection_task"] = "2"
        self.write_records()
        with self.assertRaisesRegex(AssertionError, "duplicate"): verify_run(self.temp.name, self.expected)


if __name__ == "__main__": unittest.main()
