"""M2 checks using only memory doubles, authored snapshots and local file reads."""
import copy
from pathlib import Path
import unittest
from agent.bridge import ROOT
from agent.cli import read_json
from agent.loop import bounded_decision, run_loop
from agent.protocol import Clarification, FinalDraft, ToolCall
from agent.providers import FixedProvider, ScriptedProvider
from evaluation.verifier import verify_run
from tests import test_unit as base_unit
from tests.test_unit import FakeBridge, QueueProvider, write_snapshot


class MeterDouble(FakeBridge):
    def __init__(self, limit):
        super().__init__({"code": "OK", "workflow_id": "w", "administrative_status": "RUNNING"})
        self.limit, self.turns, self.stops = limit, 0, []
    def begin_turn(self):
        if self.turns >= self.limit:
            return {"code": "ACTOR_BUDGET_EXHAUSTED", "workflow_id": "w"}
        self.turns += 1
        return self.result
    def stop_actor(self, workflow, reason):
        self.stops.append((workflow, reason))
        return {"code": "OK", "workflow_id": workflow, "administrative_status": "HANDOFF"}


class M2DecisionTests(unittest.TestCase):
    def test_persisted_meter_denial_stops_before_provider(self):
        bridge = MeterDouble(1)
        provider = QueueProvider([ToolCall("workflow_status", {"workflow_id": "w"})])
        result = run_loop(provider, bridge, {})
        self.assertEqual(bridge.turns, 1)
        self.assertEqual(len(bridge.calls), 1)
        self.assertEqual(result["stop_reason"], "ACTOR_BUDGET_EXHAUSTED")
        self.assertEqual(bridge.stops, [("w", "ACTOR_BUDGET_EXHAUSTED")])

    def test_exception_triggers_java_safety_control(self):
        bridge = MeterDouble(2)
        run_loop(QueueProvider([]), bridge, {})
        self.assertEqual(bridge.stops, [("w", "PROVIDER_FAILURE")])

    def test_false_draft_triggers_safety_without_claiming_authority(self):
        bridge = MeterDouble(2)
        result = run_loop(QueueProvider([FinalDraft("Completed")]), bridge, {})
        self.assertEqual(bridge.calls, [])
        self.assertEqual(bridge.stops, [("w", "ACTOR_STOPPED")])
        self.assertNotIn("administrative_status", result)

    def test_clarification_has_no_domain_tool_call(self):
        bridge = MeterDouble(2)
        run_loop(QueueProvider([Clarification("Which HR event?")]), bridge, {})
        self.assertEqual(bridge.calls, [])

    def test_two_invalid_outputs_reach_only_safety_control(self):
        bridge = MeterDouble(3)
        run_loop(QueueProvider([{}, {}]), bridge, {})
        self.assertEqual(bridge.calls, [])
        self.assertEqual(bridge.stops, [("w", "INVALID_PROVIDER_OUTPUT")])

    def test_provider_cannot_rewrite_observation_context(self):
        request, observations = {"employee_id": "E-999"}, [{"result": {"code": "OK"}}]
        class Mutating:
            def next_turn(self, r, o):
                r.clear(); o[0]["result"]["code"] = "COMPLETED"
                return FinalDraft("x")
        bounded_decision(Mutating(), request, observations)
        self.assertEqual(request["employee_id"], "E-999")
        self.assertEqual(observations[0]["result"]["code"], "OK")

    def test_adaptive_reads_onboarding_policy(self):
        decision = ScriptedProvider().next_turn({"employee_id": "E-1", "intent": "onboard"},
                                               [{"tool": "inspect_employee", "result": {"code": "OK"}}])
        self.assertEqual(decision.arguments, {"policy_id": "onboarding-v1"})

    def test_fixed_order_is_independent_of_eligible_hint(self):
        observation = {"tool": "workflow_status", "result": {"code": "OK", "workflow_id": "w",
                       "administrative_status": "RUNNING", "completed_steps": "1", "eligible_step": "complete_hr"}}
        fixed = FixedProvider().next_turn({"intent": "offboard"}, [observation])
        adaptive = ScriptedProvider().next_turn({"employee_id": "E-1", "intent": "offboard"}, [observation])
        self.assertEqual(fixed.arguments["step_id"], "revoke_sessions")
        self.assertEqual(adaptive.arguments["step_id"], "complete_hr")

    def test_modes_share_approval_and_blocked_stop_behavior(self):
        for state in ("AWAITING_APPROVAL", "BLOCKED_COMPENSATION", "RECOVERY_BLOCKED"):
            observation = {"tool": "propose_plan", "result": {"code": "OK", "workflow_id": "w", "administrative_status": state}}
            for provider in (FixedProvider(), ScriptedProvider()):
                self.assertIsInstance(provider.next_turn({"employee_id": "E-1", "intent": "onboard"}, [observation]), FinalDraft)


class FixtureTopologyTests(unittest.TestCase):
    def test_twelve_development_contracts_have_separate_control_and_label(self):
        paths = sorted((ROOT / "fixtures/dev").iterdir())
        self.assertEqual(len(paths), 12)
        for path in paths:
            seed, request, control, expected = (read_json(path / (n + ".json")) for n in ("seed", "request", "driver", "expected"))
            self.assertEqual(seed["employee_id"], request["employee_id"])
            self.assertEqual(expected["employee_id"], seed["employee_id"])
            self.assertNotIn("expected", request)
            self.assertNotIn("expected", control)

    def test_thirty_six_distinct_heldout_inputs_and_labels(self):
        from agent.protocol import strict_json
        inputs = [strict_json(x) for x in (ROOT / "evaluation/heldout/inputs.jsonl").read_text().splitlines()]
        labels = [strict_json(x) for x in (ROOT / "evaluation/heldout/labels.jsonl").read_text().splitlines()]
        self.assertEqual(len(inputs), 36)
        self.assertEqual(len(labels), 36)
        self.assertEqual(len({x["id"] for x in inputs}), 36)
        self.assertEqual(len({x["seed"]["employee_id"] for x in inputs}), 36)
        self.assertEqual({x["id"] for x in inputs}, {x["id"] for x in labels})
        self.assertEqual(sorted(sum(x["group"] == g for x in inputs) for g in {x["group"] for x in inputs}), [6] * 6)


# The existing checks cover grant/login/session/receipt/effect corruption. These add
# the sixth required type (hidden unresolved completion) and a literal duplicated task.
class M2VerifierCorruptionTests(unittest.TestCase):
    def setUp(self): base_unit.VerifierTests.setUp(self)
    def write_records(self): base_unit.VerifierTests.write_records(self)

    def test_hidden_required_step_cannot_be_completed(self):
        self.records["workflow"]["step.complete_hr"] = "PENDING"
        self.write_records()
        with self.assertRaisesRegex(AssertionError, "required steps"):
            verify_run(self.temp.name, self.expected)

    def test_literal_duplicate_collection_task_rejected(self):
        self.records["assets"]["asset_id"] = "LAP-104"
        self.records["assets"]["collection_task"] += ",collect-E-104-LAP-104"
        self.write_records()
        with self.assertRaisesRegex(AssertionError, "single collection"):
            verify_run(self.temp.name, self.expected)

