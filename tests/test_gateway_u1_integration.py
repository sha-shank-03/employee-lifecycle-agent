"""LEASE REQUIRED: real Java + loopback HTTP + owned-child deadline/recovery checks."""
from pathlib import Path
import threading
import time
import subprocess
import unittest
import uuid
from unittest.mock import patch
from agent.bridge import JavaBridge, ROOT
from agent.cli import approve_review, create_review, initialize, operator, read_json
from agent.gateway import GatewayError, OwnedDoubleExchange, canonical
from agent.u1 import configure, load_json, run, save_json, verify_state
from agent.u1_double import LocalDouble, envelope
from evaluation.verifier import read_snapshot, verify_run
from tests.transport_phases import DispatchedAttempt, held_startup_factory

FIXTURE = ROOT / "fixtures/dev/offboard-success"
CONFIG = ROOT / "fixtures/providers/gateway-u1-config.json"

class GatewayIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / ".build/classes/lifecycle/Main.class").is_file():
            raise RuntimeError("Build Java under the lease before this suite")
        cls.evidence_root = ROOT / "work/u1-integration" / ("batch-"+uuid.uuid4().hex[:12])
        cls.evidence_root.mkdir(parents=True)
        print("U1_LOCAL_DOUBLE_EVIDENCE="+cls.evidence_root.relative_to(ROOT).as_posix(), flush=True)
    def setUp(self):
        self.directory = self.evidence_root / self._testMethodName
        self.start = time.monotonic()
        self.workflow = initialize(FIXTURE, self.directory)["workflow_id"]
        configure(self.directory, CONFIG)
    def tearDown(self):
        save_json(self.directory / "case-observation.json", {"mode": "local-double", "live_model": False,
            "elapsed_ms": round((time.monotonic()-self.start)*1000, 3), "test": self._testMethodName,
            "verification": verify_state(self.directory), "workflow": read_snapshot(self.directory, "workflow")})
    def approve(self):
        packet, path = create_review(self.directory, self.workflow)
        approve_review(self.directory, self.workflow, path, "hr-reviewer")
        return packet
    def prepare_approved(self):
        with LocalDouble() as double:
            outcome = run(self.directory, CONFIG, double.endpoint)
        self.assertEqual(outcome["stop"], "APPROVAL_PAUSE"); self.approve()
    def assert_initial_domain(self):
        expected = {"employee_id": "E-104", "administrative_status": "AWAITING_APPROVAL", "enabled": True,
            "sessions": 2, "grants": ["employees", "engineering"], "hr_status": "ACTIVE", "collection_status": "NONE",
            "collection_task": False, "business_effects": 0}
        return verify_run(self.directory, expected)
    def test_success_approval_and_resume_history(self):
        with LocalDouble() as double:
            before = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(before["stop"], "APPROVAL_PAUSE"); self.assert_initial_domain()
            first = read_snapshot(self.directory, "workflow")
            self.assertEqual(first["provider_turns"], "3"); self.assertEqual(first["active_reserved_ms"], "85000")
            packet = self.approve()
            self.assertEqual(packet["approved.gateway_config_sha256"], first["gateway_config_sha256"])
            after = run(self.directory, CONFIG, double.endpoint)
            self.assertTrue(after["guarded"]["completed"]); self.assertEqual(len(double.requests), 8)
            self.assertFalse(any(r["authorization_present"] for r in double.requests))
            self.assertTrue(all(r["model"] == "local/synthetic-tool-double" for r in double.requests))
        self.assertFalse(double.cleanup["server_thread_live"])
        last = read_snapshot(self.directory, "workflow")
        self.assertEqual(last["provider_turns"], "8"); self.assertEqual(last["active_reserved_ms"], "220000")
        self.assertEqual(last["cleanup_reserved_ms"], "4000")
        history = load_json(self.directory / "gateway-history.json")["provider"]
        tool_ids = [m["tool_call_id"] for m in history["messages"] if m["role"] == "tool"]
        self.assertEqual(len(tool_ids), 8); self.assertEqual(len(set(tool_ids)), 8)
        self.assertTrue(verify_run(self.directory, read_json(FIXTURE / "expected.json"))["passed"])
    def test_absent_approval_pauses_without_spending_on_resume(self):
        with LocalDouble() as double:
            run(self.directory, CONFIG, double.endpoint)
            before = read_snapshot(self.directory, "workflow")
            resumed = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(resumed["stop"], "APPROVAL_PAUSE"); self.assertEqual(len(double.requests), 3)
        self.assertEqual(before, read_snapshot(self.directory, "workflow")); self.assert_initial_domain()
        with JavaBridge(self.directory) as bridge:
            self.assertEqual(bridge.request({"tool": "gateway_session", "workflow_id": self.workflow})["code"], "OK")
            denied = bridge.request({"tool": "execute_step", "workflow_id": self.workflow, "step_id": "disable_login"})
            self.assertEqual(denied["code"], "APPROVAL_REQUIRED")
            forbidden = bridge.request({"tool": "approve", "workflow_id": self.workflow, "digest": before["digest"], "approver": "hr-reviewer"})
            self.assertEqual(forbidden["code"], "TOOL_NOT_ALLOWED")
            injected = bridge.request({"tool": "propose_plan", "employee_id": "E-104", "intent": "offboard", "permission": "approved"})
            self.assertEqual(injected["code"], "INVALID_ARGUMENTS")
            self.assertEqual(bridge.request({"tool": "inspect_employee", "employee_id": "E-999"})["code"], "EMPLOYEE_SCOPE_DENIED")
            self.assertEqual(bridge.request({"tool": "execute_step", "workflow_id": "wf-other", "step_id": "disable_login"})["code"], "WORKFLOW_SCOPE_DENIED")
        self.assert_initial_domain()
    def test_expired_approval_cannot_complete_or_mutate(self):
        self.prepare_approved()
        operator(self.directory, "advance_clock", workflow_id=self.workflow, seconds="86401")
        with LocalDouble() as double: outcome = run(self.directory, CONFIG, double.endpoint)
        self.assertFalse(outcome["guarded"]["completed"]); self.assertEqual(outcome["guarded"]["business_effects"], 0)
        self.assertEqual(outcome["guarded"]["administrative_status"], "STALE_APPROVAL")
    def test_tampered_approval_and_changed_config_rejected(self):
        with LocalDouble() as double: run(self.directory, CONFIG, double.endpoint)
        with JavaBridge(self.directory, mode="operator") as bridge:
            result = bridge.request({"tool": "approve", "workflow_id": self.workflow, "digest": "0"*64, "approver": "hr-reviewer"})
            self.assertEqual(result["code"], "APPROVAL_DIGEST_MISMATCH")
            result = bridge.request({"tool": "configure_gateway", "workflow_id": self.workflow, "config_sha256": "0"*64})
            self.assertEqual(result["code"], "GATEWAY_CONFIG_IMMUTABLE")
        self.assert_initial_domain()
    def test_false_completion_raw_draft_guarded_and_handed_off(self):
        self.prepare_approved()
        with LocalDouble(lambda _, generation, __: envelope(generation, final="Everything completed successfully")) as double:
            outcome = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(len(double.requests), 1)
        self.assertEqual(outcome["stop"], "FINAL_DRAFT"); self.assertEqual(len(outcome["raw_final_sha256"]), 1)
        self.assertFalse(outcome["guarded"]["completed"]); self.assertTrue(outcome["guarded"]["access_revoked"])
        self.assertEqual(outcome["guarded"]["administrative_status"], "HANDOFF")
        self.assertEqual(read_snapshot(self.directory, "workflow")["cleanup_reserved_ms"], "60000")
        expected = {"employee_id": "E-104", "administrative_status": "HANDOFF", "enabled": False, "sessions": 0,
            "grants": [], "hr_status": "ACTIVE", "collection_status": "NONE", "collection_task": False, "business_effects": 3}
        self.assertTrue(verify_run(self.directory, expected)["passed"])
        self.assertNotIn("Everything completed successfully", canonical(outcome).decode())
    def test_unknown_tool_has_no_effect_and_no_retry(self):
        with LocalDouble(lambda _, generation, __: envelope(generation, tool="approve", arguments={"workflow_id": self.workflow})) as double:
            outcome = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(len(double.requests), 1)
            with self.assertRaisesRegex(GatewayError, "HISTORY_UNCERTAIN"): run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(len(double.requests), 1)
        self.assertEqual(outcome["stop"], "INVALID_PROVIDER_OUTPUT")
        self.assertEqual(outcome["guarded"]["business_effects"], 0)
    def test_http_denials_and_errors_one_attempt_unknown_cost(self):
        for status in (401, 402, 403, 429, 500, 503):
            with self.subTest(status=status):
                directory = self.directory/str(status)
                initialize(FIXTURE, directory); configure(directory, CONFIG)
                with LocalDouble(lambda *_: (status, b"{}")) as double:
                    outcome = run(directory, CONFIG, double.endpoint)
                    self.assertEqual(len(double.requests), 1)
                self.assertEqual(outcome["stop"], "PROVIDER_FAILURE")
                failed = [e for e in outcome["events"] if e["kind"] == "inference_failure"][0]
                self.assertEqual(failed["http_status"], status); self.assertIsNone(failed["actual_cost"])
                self.assertEqual(read_snapshot(directory, "workflow")["provider_turns"], "1")
    def test_redirect_is_not_followed(self):
        with LocalDouble(lambda *_: (302, b"{}", {"Location": "http://127.0.0.1:1/forbidden"})) as double:
            outcome = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(len(double.requests), 1)
        self.assertEqual(outcome["stop"], "PROVIDER_FAILURE")
        self.assertEqual(outcome["guarded"]["business_effects"], 0)
    def test_wrong_media_type_is_rejected(self):
        with LocalDouble(lambda *_: (200, b"{}", {"Content-Type": "text/plain"})) as double:
            outcome = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(len(double.requests), 1)
        self.assertEqual(outcome["stop"], "PROVIDER_FAILURE")
        self.assertEqual(outcome["guarded"]["business_effects"], 0)
    def test_oversized_reply_is_rejected(self):
        with LocalDouble(lambda *_: (200, b"x"*65537)) as double:
            outcome = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(len(double.requests), 1)
        self.assertEqual(outcome["stop"], "PROVIDER_FAILURE")
        self.assertEqual(outcome["guarded"]["business_effects"], 0)
    def test_response_loss_halts_without_resend(self):
        with LocalDouble(lambda *_: None) as double:
            outcome = run(self.directory, CONFIG, double.endpoint)
            self.assertEqual(len(double.requests), 1)
            with self.assertRaisesRegex(GatewayError, "HISTORY_UNCERTAIN"): run(self.directory, CONFIG, double.endpoint)
        self.assertEqual(outcome["stop"], "PROVIDER_FAILURE")
        self.assertEqual(outcome["guarded"]["business_effects"], 0)
        self.assertTrue(all(not e["owned_cleanup"]["live"] for e in outcome["events"] if e["kind"] == "owned_cleanup"))
    def test_owned_transport_does_not_create_relative_windows_cache(self):
        relative_cache = ROOT / "%SystemDrive%"
        self.assertFalse(relative_cache.exists(), "quarantine the retained failure before this check")
        with LocalDouble(lambda _, generation, __: envelope(generation, final="transport response")) as double:
            exchange = OwnedDoubleExchange(double.endpoint); start = time.monotonic(); deadline = start+5
            status, reply = exchange(canonical({"model": "local/synthetic-tool-double", "messages": []}), deadline)
            elapsed = time.monotonic()-start
            self.assertEqual(status, 200); self.assertTrue(reply); self.assertEqual(len(double.requests), 1)
            self.assertLess(time.monotonic(), deadline); self.assertEqual(len(exchange.cleanup), 1)
            self.assertFalse(exchange.cleanup[0]["live"])
            save_json(self.directory / "owned-transport-cleanup.json", exchange.cleanup)
            save_json(self.directory / "owned-transport-observation.json", {"elapsed_ms": round(elapsed*1000, 3),
                "requests": len(double.requests), "cleanup_confirmed": True, "mode": "local-double"})
        self.assertFalse(relative_cache.exists(), "transport recreated an unresolved Windows runtime cache")
    def test_total_transport_deadline_owns_and_reaps_child(self):
        def stalled(_, generation, abort): abort.wait(30); return envelope(generation, final="late")
        with LocalDouble(stalled) as double:
            body = canonical({"model": "local/synthetic-tool-double", "messages": []})
            with DispatchedAttempt(double,body,phase="stalled-response") as attempt:
                exchange = OwnedDoubleExchange(double.endpoint); start = time.monotonic(); deadline = start+2.3
                with patch("agent.gateway.subprocess.Popen",side_effect=attempt.claim), self.assertRaisesRegex(GatewayError,"PROVIDER_TIMEOUT"):
                    exchange(body,deadline)
                self.assertLess(time.monotonic(), deadline+.2); self.assertEqual(len(double.requests), 1)
                self.assertEqual(len(exchange.cleanup), 1); self.assertFalse(exchange.cleanup[0]["live"])
                save_json(self.directory / "owned-transport-cleanup.json", exchange.cleanup)
                save_json(self.directory / "transport-phase.json", {**attempt.observation(),"response_total_bound_seconds":2.3,"tolerance_seconds":.2})
    def test_cold_start_deadline_owns_and_reaps_undispatched_child(self):
        with LocalDouble() as double:
            exchange = OwnedDoubleExchange(double.endpoint); launch = subprocess.Popen
            start = time.monotonic(); deadline = start+2.3
            with patch("agent.gateway.subprocess.Popen",side_effect=held_startup_factory(launch)), self.assertRaisesRegex(GatewayError,"PROVIDER_TIMEOUT"):
                exchange(canonical({"model":"local/synthetic-tool-double","messages":[]}),deadline)
            self.assertLess(time.monotonic(),deadline+.2); self.assertEqual(len(double.requests),0)
            self.assertEqual(len(exchange.cleanup),1); self.assertFalse(exchange.cleanup[0]["live"])
            save_json(self.directory / "owned-transport-cleanup.json",exchange.cleanup)
            save_json(self.directory / "transport-phase.json",{"mode":"local-double","phase":"cold-start-held-before-worker","confirmed_requests":0,
                "startup_included_in_total_timer":True,"total_bound_seconds":2.3,"tolerance_seconds":.2,"stalled_http_exercised":False})
    def test_transport_cancellation_after_confirmed_dispatch_reaps_child(self):
        def stalled(_,generation,abort): abort.wait(30); return envelope(generation,final="late")
        with LocalDouble(stalled) as double:
            body=canonical({"model":"local/synthetic-tool-double","messages":[]})
            with DispatchedAttempt(double,body,phase="stalled-response") as attempt:
                exchange=OwnedDoubleExchange(double.endpoint); cancel=threading.Event(); timer=threading.Timer(.15,cancel.set)
                start=time.monotonic(); timer.start()
                try:
                    with patch("agent.gateway.subprocess.Popen",side_effect=attempt.claim), self.assertRaisesRegex(GatewayError,"PROVIDER_CANCELLED"):
                        exchange(body,start+3,cancel)
                finally: timer.cancel(); timer.join(timeout=1)
                self.assertLess(time.monotonic()-start,1); self.assertFalse(timer.is_alive()); self.assertEqual(len(double.requests),1)
                self.assertEqual(len(exchange.cleanup),1); self.assertFalse(exchange.cleanup[0]["live"])
                save_json(self.directory / "owned-transport-cleanup.json",exchange.cleanup)
                save_json(self.directory / "transport-phase.json",{**attempt.observation(),"cancellation_bound_seconds":1})
    def test_transport_cancellation_reaps_child(self):
        def stalled(_, generation, abort): abort.wait(30); return envelope(generation, final="late")
        cancel = threading.Event(); timer = threading.Timer(.15, cancel.set)
        with LocalDouble(stalled) as double:
            exchange = OwnedDoubleExchange(double.endpoint); timer.start(); start = time.monotonic()
            try:
                with self.assertRaisesRegex(GatewayError, "PROVIDER_CANCELLED"):
                    exchange(canonical({"model": "local/synthetic-tool-double", "messages": []}), start+3, cancel)
            finally: timer.cancel(); timer.join(timeout=1)
            self.assertLess(time.monotonic()-start, 1); self.assertFalse(timer.is_alive())
            self.assertFalse(exchange.cleanup[0]["live"])
            save_json(self.directory / "owned-transport-cleanup.json", exchange.cleanup)
    def test_trickled_body_obeys_parent_deadline(self):
        with LocalDouble(lambda _, generation, __: envelope(generation, final="late"), trickle=True) as double:
            body=canonical({"model":"local/synthetic-tool-double","messages":[]})
            with DispatchedAttempt(double,body,phase="trickled-body") as attempt:
                exchange = OwnedDoubleExchange(double.endpoint); start = time.monotonic(); deadline = start+2.3
                with patch("agent.gateway.subprocess.Popen",side_effect=attempt.claim), self.assertRaisesRegex(GatewayError, "PROVIDER_TIMEOUT"):
                    exchange(body, deadline)
                self.assertLess(time.monotonic(), deadline+.2); self.assertEqual(len(double.requests), 1)
                self.assertFalse(exchange.cleanup[0]["live"])
                save_json(self.directory / "owned-transport-cleanup.json", exchange.cleanup)
                save_json(self.directory / "transport-phase.json",{**attempt.observation(),"response_total_bound_seconds":2.3,"tolerance_seconds":.2})
    def test_java_reply_loss_reconciles_receipt_without_duplicate(self):
        self.prepare_approved()
        with LocalDouble() as double:
            failed = run(self.directory, CONFIG, double.endpoint, crash_after="after_service_commit:disable_login")
            self.assertEqual(failed["stop"], "JAVA_REPLY_UNCERTAIN")
            before = read_snapshot(self.directory, "workflow")
            self.assertEqual(before["step.disable_login"], "INTENT")
            self.assertEqual(read_snapshot(self.directory, "identity")["effects.disable_login"], "1")
            saved = load_json(self.directory / "gateway-history.json"); self.assertEqual(saved["phase"], "pending")
            after = run(self.directory, CONFIG, double.endpoint)
        self.assertTrue(after["guarded"]["completed"])
        last = read_snapshot(self.directory, "workflow")
        self.assertGreater(int(last["active_reserved_ms"]), int(before["active_reserved_ms"]))
        self.assertEqual(read_snapshot(self.directory, "identity")["effects.disable_login"], "1")
        expected = {**read_json(FIXTURE / "expected.json"), "recovered_step": "disable_login"}
        self.assertTrue(verify_run(self.directory, expected)["passed"])
        history = load_json(self.directory / "gateway-history.json")["provider"]
        self.assertTrue(any(m["role"] == "tool" and "RECONCILED" in m["content"] for m in history["messages"]))
    def test_controller_cancellation_runs_approved_safety_only(self):
        self.prepare_approved(); cancel = threading.Event()
        def stalled(_, generation, abort):
            cancel.set(); abort.wait(30); return envelope(generation, final="late")
        with LocalDouble(stalled) as double:
            outcome = run(self.directory, CONFIG, double.endpoint, cancel=cancel)
            self.assertEqual(len(double.requests), 1)
        self.assertEqual(outcome["stop"], "CANCELLED")
        self.assertFalse(outcome["guarded"]["completed"]); self.assertTrue(outcome["guarded"]["access_revoked"])
        self.assertEqual(outcome["guarded"]["business_effects"], 3)
        self.assertTrue(all(not e["owned_cleanup"]["live"] for e in outcome["events"] if e["kind"] == "owned_cleanup"))
    def test_controller_deadline_includes_cleanup(self):
        self.prepare_approved()
        def stalled(_, generation, abort): abort.wait(30); return envelope(generation, final="late")
        with LocalDouble(stalled) as double:
            started = time.monotonic(); outcome = run(self.directory, CONFIG, double.endpoint)
            self.assertLess(time.monotonic()-started, 23)
            self.assertEqual(len(double.requests), 1)
        self.assertEqual(outcome["stop"], "PROVIDER_TIMEOUT")
        self.assertTrue(outcome["guarded"]["access_revoked"]); self.assertFalse(outcome["guarded"]["completed"])
        self.assertEqual(outcome["guarded"]["business_effects"], 3)
    def test_cleanup_crash_spends_reservation_across_restart(self):
        self.prepare_approved()
        with LocalDouble(lambda _, generation, __: envelope(generation, final="Completed")) as double:
            failed = run(self.directory, CONFIG, double.endpoint, crash_after="after_intent:disable_login")
            self.assertEqual(failed["stop"], "JAVA_REPLY_UNCERTAIN")
            before = read_snapshot(self.directory, "workflow")
            self.assertEqual(before["cleanup_reserved_ms"], "60000")
            resumed = run(self.directory, CONFIG, double.endpoint)
            self.assertFalse(resumed["guarded"]["completed"]); self.assertEqual(len(double.requests), 1)
        # Constructor may reconcile an intent but cannot restart a spent safety batch.
        state = operator(self.directory, "report", workflow_id=self.workflow)
        self.assertEqual(state["administrative_status"], "BLOCKED_COMPENSATION")
        self.assertEqual(state["reason"], "CLEANUP_BUDGET_EXHAUSTED")
        self.assertEqual(read_snapshot(self.directory, "workflow")["cleanup_reserved_ms"], "60000")
        self.assertEqual(verify_state(self.directory)["business_effects"], 0)

if __name__ == "__main__": unittest.main(verbosity=2)
