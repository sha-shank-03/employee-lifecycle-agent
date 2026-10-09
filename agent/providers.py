"""Authored deterministic providers. Neither mode reads fixture IDs, labels or verifier code."""
from typing import Protocol
from .protocol import Clarification, FinalDraft, ToolCall

OFFBOARD = ("disable_login", "revoke_sessions", "remove_grants", "create_collection_task", "complete_hr")
ONBOARD = ("prepare_account", "add_role_grants", "reserve_asset", "enable_login", "complete_onboarding_hr")
TERMINAL = {"AWAITING_APPROVAL", "WAITING_EFFECTIVE_TIME", "BLOCKED", "HANDOFF", "STALE_APPROVAL",
            "COMPENSATED", "CANCELLED", "SUPERSEDED", "BLOCKED_COMPENSATION", "RECOVERY_BLOCKED"}


class Provider(Protocol):
    def next_turn(self, request: dict, observations: list[dict]) -> ToolCall | FinalDraft | Clarification: ...


class ScriptedProvider:
    mode = "scripted-adaptive"

    def next_turn(self, request, observations):
        employee = request["employee_id"]
        if not observations:
            return ToolCall("inspect_employee", {"employee_id": employee})
        last, result = observations[-1], observations[-1]["result"]
        if result["code"] not in {"OK", "TRANSIENT"}:
            return FinalDraft(f"Operator review required: {result['code']}")
        if last["tool"] == "inspect_employee":
            return ToolCall("read_policy", {"policy_id": "onboarding-v1" if request["intent"] == "onboard" else "offboarding-v1"})
        if last["tool"] == "read_policy":
            return ToolCall("propose_plan", {"employee_id": employee, "intent": request["intent"]})
        workflow = result.get("workflow_id", request.get("workflow_id", ""))
        state = result.get("administrative_status", "")
        if state in TERMINAL:
            return FinalDraft(f"Current administrative status: {state}")
        if state == "COMPLETED":
            return FinalDraft("The local lifecycle postconditions were verified.")
        if result.get("eligible_step"):
            return ToolCall("execute_step", {"workflow_id": workflow, "step_id": result["eligible_step"]})
        return ToolCall("workflow_status", {"workflow_id": workflow})


class FixedProvider(ScriptedProvider):
    """Fixed evidence and action ordering, with the identical approval/recovery/safety boundary."""
    mode = "fixed"

    def next_turn(self, request, observations):
        if not observations or observations[-1]["tool"] in {"inspect_employee", "read_policy"}:
            return super().next_turn(request, observations)
        result = observations[-1]["result"]
        if result["code"] not in {"OK", "TRANSIENT"} or result.get("administrative_status") in TERMINAL | {"COMPLETED"}:
            return super().next_turn(request, observations)
        steps = ONBOARD if request["intent"] == "onboard" else OFFBOARD
        completed = int(result.get("completed_steps", "0"))
        if completed >= len(steps):
            return ToolCall("verify_outcome", {"workflow_id": result["workflow_id"]})
        if int(result.get("retry_after_ms", "0")):
            return ToolCall("workflow_status", {"workflow_id": result["workflow_id"]})
        return ToolCall("execute_step", {"workflow_id": result["workflow_id"], "step_id": steps[completed]})


def provider_for(mode):
    if mode in {"scripted", "scripted-adaptive"}:
        return ScriptedProvider()
    if mode == "fixed":
        return FixedProvider()
    raise ValueError("unknown offline provider")

