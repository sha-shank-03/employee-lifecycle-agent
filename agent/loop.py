"""Bounded provider loop. Java meters persisted decisions and owns deterministic safety."""
import copy
import queue
import threading
import time
from .protocol import Clarification, FinalDraft, ToolCall, validate_call


def bounded_decision(provider, request, observations, timeout=2):
    result = queue.Queue(maxsize=1)

    def invoke():
        try:
            result.put((True, provider.next_turn(copy.deepcopy(request), copy.deepcopy(observations))))
        except Exception as error:
            result.put((False, error))

    threading.Thread(target=invoke, daemon=True).start()
    try:
        ok, value = result.get(timeout=timeout)
    except queue.Empty as error:
        raise TimeoutError("offline provider exceeded two-second response bound") from error
    if not ok:
        raise value
    return value


def run_loop(provider, bridge, request, *, observations=None, max_turns=24):
    observations = list(observations or [])
    invalid, workflow = 0, request.get("workflow_id", "")
    deadline = time.monotonic() + 120
    reason, draft = "ACTOR_BUDGET_EXHAUSTED", "Actor stopped; inspect authoritative state."
    for _ in range(min(max_turns, 24)):
        if time.monotonic() >= deadline:
            break
        if hasattr(bridge, "begin_turn"):
            meter = bridge.begin_turn()
            workflow = meter.get("workflow_id", workflow)
            if meter["code"] != "OK":
                observations.append({"tool": "budget", "result": meter})
                break
        if observations:
            wait_ms = int(observations[-1]["result"].get("retry_after_ms", "0"))
            if wait_ms > 0:
                wait_ms = min(wait_ms, 2000)
                if hasattr(bridge, "charge_wait") and bridge.charge_wait(wait_ms)["code"] != "OK":
                    break
                time.sleep(wait_ms / 1000)
        try:
            decision = bounded_decision(provider, request, observations)
        except TimeoutError:
            reason, draft = "PROVIDER_TIMEOUT", "Provider timed out; Java safety work owns the disposition."
            break
        except Exception:
            reason, draft = "PROVIDER_FAILURE", "Provider failed; inspect the authoritative disposition."
            break
        if isinstance(decision, (FinalDraft, Clarification)):
            reason, draft = "ACTOR_STOPPED", decision.text
            break
        try:
            if not isinstance(decision, ToolCall):
                raise ValueError("provider must return one typed decision")
            validate_call(decision)
        except ValueError as error:
            invalid += 1
            observations.append({"tool": "invalid", "result": {"code": "INVALID_PROVIDER_OUTPUT", "detail": str(error)}})
            if invalid >= 2:
                reason = "INVALID_PROVIDER_OUTPUT"
                break
            continue
        result = bridge.call(decision)
        workflow = result.get("workflow_id", workflow)
        observations.append({"tool": decision.name, "arguments": decision.arguments, "result": result})
    if workflow and hasattr(bridge, "stop_actor"):
        safety = bridge.stop_actor(workflow, reason)
        observations.append({"tool": "safety", "result": safety})
    return {"provider": getattr(provider, "mode", "test-double"), "draft": draft,
            "observations": observations, "workflow_id": workflow, "stop_reason": reason}

