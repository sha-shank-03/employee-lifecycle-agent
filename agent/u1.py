"""Bounded U1 offboarding controller. All inference is an explicit local double."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import threading
import time
from .bridge import BridgeError, JavaBridge
from .gateway import GatewayError, GatewayProvider, OwnedDoubleExchange, VERSION, canonical, digest, strict
from .protocol import Clarification, FinalDraft, ToolCall
from .u1_events import event
from evaluation.verifier import STEPS, audit_history, plan_digest, read_snapshot

CONFIG = {"schema": 1, "version": VERSION, "mode": "local-double", "model": "local/synthetic-tool-double",
          "automatic_retries": 0, "inference_allocation_inr": 0, "actor_cap_ms": 300000,
          "cleanup_cap_ms": 60000, "session_reserve_ms": 10000, "turn_reserve_ms": 25000,
          "provider_timeout_ms": 20000, "tool_timeout_ms": 5000, "turn_limit": 12, "output_token_cap": 2048}

def load_config(path):
    raw = Path(path).read_bytes()
    if len(raw) > 8192: raise GatewayError("CONFIG_SIZE_LIMIT")
    value = strict(raw)
    if type(value) is not dict or set(value) != set(CONFIG) or any(type(value[k]) is not type(v) or value[k] != v for k, v in CONFIG.items()):
        raise GatewayError("U1_LOCAL_CONFIG_REQUIRED")
    return value, digest(value)

def load_json(path, limit=196608):
    raw = Path(path).read_bytes()
    if len(raw) > limit: raise GatewayError("LOCAL_STATE_SIZE_LIMIT")
    return strict(raw)

def save_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(value)
    if len(data) > 196608: raise GatewayError("LOCAL_STATE_SIZE_LIMIT")
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)

def append_jsonl(path, value):
    path = Path(path); data = canonical(value)+b"\n"
    if len(data) > 8192 or path.exists() and path.stat().st_size+len(data) > 1048576:
        raise GatewayError("LOCAL_EVENT_SIZE_LIMIT")
    with path.open("ab") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())

def validate_request(value):
    if type(value) is not dict or set(value) != {"employee_id", "intent", "text"} or value["intent"] != "offboard" \
            or any(type(v) is not str for v in value.values()) or not re.fullmatch(r"E-[0-9]{1,8}", value["employee_id"]) \
            or len(value["text"].encode()) > 16384:
        raise GatewayError("OFFBOARD_REQUEST_REQUIRED")

def remaining_budget(w, config_hash):
    if w.get("budget_policy") != VERSION or w.get("gateway_config_sha256") != config_hash or w.get("intent") != "offboard" or w.get("turn_limit") != "12":
        raise GatewayError("JAVA_CONFIG_MISMATCH")
    limits = {"active_reserved_ms": 300000, "cleanup_reserved_ms": 60000, "provider_turns": 12, "actor_calls": 32, "safety_calls": 12}
    for k, cap in limits.items():
        if type(w.get(k)) is not str or not re.fullmatch(r"[0-9]{1,6}", w[k]) or not 0 <= int(w[k]) <= cap:
            raise GatewayError("INVALID_PERSISTED_BUDGET")
    return (300000-int(w["active_reserved_ms"]))/1000, (60000-int(w["cleanup_reserved_ms"]))/1000

def verify_state(run_dir):
    """No Java calls, model text or self-reported final result; reads committed state."""
    records = {n: read_snapshot(run_dir, n) for n in ("workflow", "hr", "identity", "assets")}
    w, hr, i, a = (records[n] for n in ("workflow", "hr", "identity", "assets"))
    checks = []
    def check(condition, label):
        if not condition: raise AssertionError(label)
        checks.append(label)
    check(w["intent"] == "offboard" and all(s["employee_id"] == w["employee_id"] for s in records.values()), "offboarding scope")
    if w["digest"]: check(plan_digest(w) == w["digest"], "exact plan digest independently reproduced")
    remaining_budget(w, w.get("gateway_config_sha256", ""))
    check(int(w["cleanup_reserved_ms"]) >= 5000 * int(w["safety_calls"]), "cleanup effects covered by reservations")
    effect_count = 0
    for name in ("hr", "identity", "assets"):
        for key, value in records[name].items():
            if key.startswith("effect."):
                check(value in ("0", "1"), "no duplicate domain effect")
                check(key.replace("effect.", "ledger.", 1) in records[name], "effect has committed receipt")
                effect_count += int(value)
    if effect_count:
        check(w.get("approval_digest") == w["digest"] and w.get("approval_approver") == "hr-reviewer", "all effects require exact approval")
    audit_history(run_dir, records, {}, check)
    revoked = i["enabled"] == "false" and i["sessions"] == "0" and not i["grants"]
    complete = w["administrative_status"] == "COMPLETED"
    if complete:
        check(all(w["step."+s] == "DONE" for s in STEPS) and revoked and hr["administrative_status"] == "OFFBOARDED", "five steps and authoritative completion")
        check(effect_count == 5, "five unique business effects")
        check(not w["approved.asset_id"] or a["collection_status"] == "OPEN" and a["collection_task"] == "collect-"+w["employee_id"]+"-"+w["approved.asset_id"], "exact collection task")
        for step in STEPS:
            service = "identity" if step in STEPS[:3] else "assets" if step == "create_collection_task" else "hr"
            check("receipt."+step in records[service], "committed required receipt")
    return {"passed": True, "completed": complete, "access_revoked": revoked, "physical_return_verified": False,
            "assertion_count": len(checks), "business_effects": effect_count, "administrative_status": w["administrative_status"]}

def validate_saved(saved, config_hash, request):
    keys = {"schema", "config_sha256", "request_sha256", "provider", "observations", "phase", "approval_wait_excluded"}
    if type(saved) is not dict or set(saved) != keys or saved["schema"] != 1 or type(saved["schema"]) is not int \
            or saved["config_sha256"] != config_hash or saved["request_sha256"] != digest(request) \
            or saved["phase"] not in {"ready", "pending", "paused", "failed"} or type(saved["observations"]) is not list \
            or len(saved["observations"]) > 12 or type(saved["approval_wait_excluded"]) is not bool:
        raise GatewayError("INVALID_LOCAL_HISTORY")
    if saved["phase"] == "failed": raise GatewayError("HISTORY_UNCERTAIN")
    for observation in saved["observations"]:
        if type(observation) is not dict or set(observation) != {"tool", "arguments", "result"} or type(observation["result"]) is not dict:
            raise GatewayError("INVALID_LOCAL_OBSERVATION")
        from .protocol import validate_call
        validate_call(ToolCall(observation["tool"], observation["arguments"]))

def configure(run_dir, config_path):
    _, config_hash = load_config(config_path)
    w = read_snapshot(run_dir, "workflow")
    deadline = time.monotonic()+10
    with JavaBridge(run_dir, mode="operator", deadline=deadline) as bridge:
        result = bridge.request({"tool": "configure_gateway", "workflow_id": w["workflow_id"], "config_sha256": config_hash})
        if result["code"] != "OK": raise GatewayError(result["code"])
    return {"mode": "local-double", "config_sha256": config_hash, "live_model": False, "configured": True}

def run(run_dir, config_path, endpoint, *, cancel=None, crash_after=None):
    """No automatic resend on errors; each decision has one HTTP exchange and one tool."""
    start = time.monotonic(); directory = Path(run_dir)
    config, config_hash = load_config(config_path)
    request = load_json(directory / "request.json", 20000); validate_request(request)
    w = read_snapshot(directory, "workflow"); workflow = w["workflow_id"]
    actor_seconds, cleanup_seconds = remaining_budget(w, config_hash)
    if request["employee_id"] != w["employee_id"]: raise GatewayError("EMPLOYEE_SCOPE_DENIED")
    state_path = directory / "gateway-history.json"
    saved = load_json(state_path) if state_path.exists() else {"schema": 1, "config_sha256": config_hash,
        "request_sha256": digest(request), "provider": None, "observations": [], "phase": "ready", "approval_wait_excluded": False}
    validate_saved(saved, config_hash, request)
    exchange = OwnedDoubleExchange(endpoint)
    provider = GatewayProvider(config["model"], exchange, state=saved["provider"])
    had_history = provider.request_hash is not None
    if len(provider.response_ids) > int(w["provider_turns"]): raise GatewayError("JAVA_HISTORY_COUNTER_MISMATCH")
    observations = saved["observations"]
    # History/argument correlation must be checked before launching any owned child.
    if not provider.pending: provider.observe(observations)
    elif provider.observation_hashes != [digest(o) for o in observations]: raise GatewayError("UNRECONCILED_HISTORY_MISMATCH")
    events, stop, bridge = [], "OPERATOR_REVIEW", None
    total_end = start + actor_seconds + cleanup_seconds
    actor_end = start + actor_seconds
    cancel = cancel if cancel is not None else threading.Event()
    def record(kind, **fields):
        item = event(kind, config_sha256=config_hash, workflow_id=workflow, elapsed_ms=(time.monotonic()-start)*1000, **fields)
        events.append(item); append_jsonl(directory/"gateway-events.jsonl", item)
    def persist(phase):
        saved.update(provider=provider.export(), observations=observations, phase=phase)
        save_json(state_path, saved)
    def finish_snapshot():
        nonlocal w
        w = read_snapshot(directory, "workflow")
        verification = verify_state(directory)
        record("verification", verification=verification, counters=w)
        result = {"schema": 1, "mode": "local-double", "live_model": False, "stop": stop,
            "raw_final_sha256": [e["decision_sha256"] for e in events if e["kind"] == "decision" and e.get("stop") == "FINAL_DRAFT"],
            "guarded": verification, "elapsed_ms": round((time.monotonic()-start)*1000, 3),
            "actor_remaining_ms": max(0, 300000-int(w["active_reserved_ms"])),
            "cleanup_remaining_ms": max(0, 60000-int(w["cleanup_reserved_ms"])),
            "human_approval_wait_excluded": saved["approval_wait_excluded"], "events": events}
        result["active_deadline_seconds"] = actor_seconds+cleanup_seconds
        result["owned_work_deadline_met"] = time.monotonic() <= total_end if bridge is not None else None
        save_json(directory / "gateway-outcome.json", result)
        return result
    if w["administrative_status"] == "AWAITING_APPROVAL" and not provider.pending:
        saved["approval_wait_excluded"] = True; persist("paused"); stop = "APPROVAL_PAUSE"
        record("approval_pause", stop=stop, counters=w)
        return finish_snapshot()
    if actor_seconds < 10 or cleanup_seconds < 2 or int(w["provider_turns"]) >= 12:
        stop = "CLEANUP_BUDGET_EXHAUSTED" if cleanup_seconds < 2 else "ACTOR_BUDGET_EXHAUSTED"
        record("stop", stop=stop, counters=w)
        return finish_snapshot()
    try:
        # Before launching, mark the attempt uncertain. A launch/handshake failure cannot silently reset reservations.
        persist("failed")
        bridge = JavaBridge(directory, deadline=total_end, cancel=cancel, crash_after=crash_after)
        status = bridge.request({"tool": "gateway_session", "workflow_id": workflow})
        if status["code"] != "OK": raise GatewayError("ACTOR_BUDGET_EXHAUSTED")
        w = read_snapshot(directory, "workflow")
        record("session_start", counters=w)
        if provider.pending:
            verification = verify_state(directory)
            pending = provider.pending
            observations.append({"tool": pending["name"], "arguments": pending["arguments"],
                "result": {**status, "code": "RECONCILED", "reconciled_tool": pending["name"],
                           "independent_audit": "passed" if verification["passed"] else "failed"}})
            provider.observe(observations)
        if had_history: provider.resume_snapshot(status)
        persist("ready")
        while True:
            if cancel.is_set(): stop = "CANCELLED"; break
            if time.monotonic() >= actor_end-2: stop = "ACTOR_BUDGET_EXHAUSTED"; break
            if status.get("administrative_status") == "AWAITING_APPROVAL":
                saved["approval_wait_excluded"] = True; stop = "APPROVAL_PAUSE"; record("approval_pause", stop=stop, counters=status); break
            if status.get("administrative_status") == "COMPLETED":
                stop = "COMPLETED"; break
            turn_start = time.monotonic()
            status = bridge.begin_turn()
            if status["code"] != "OK": stop = "ACTOR_BUDGET_EXHAUSTED"; break
            wait = min(2000, int(status.get("retry_after_ms", "0")))
            if wait:
                charged = bridge.charge_wait(wait)
                if charged["code"] != "OK": stop = "ACTOR_BUDGET_EXHAUSTED"; break
                if cancel.wait(wait/1000): stop = "CANCELLED"; break
            turn_end = min(actor_end-2, turn_start+25+wait/1000)
            # Mark transmission uncertain before exchange. No HTTP status/timeout path retries.
            persist("failed")
            decision = provider.next_turn(request, observations, deadline=min(turn_end-5, time.monotonic()+20), cancel=cancel)
            if isinstance(decision, (FinalDraft, Clarification)):
                stop = "FINAL_DRAFT" if isinstance(decision, FinalDraft) else "REFUSAL"
                record("decision", stop=stop, decision={"kind": stop, "text": decision.text}, transport=provider.trace[-1])
                persist("ready"); break
            record("decision", decision={"tool": decision.name, "arguments": decision.arguments}, transport=provider.trace[-1])
            persist("pending")
            # One finite Java tool only. Ambiguous acknowledgement remains pending until independent reconciliation on explicit resume.
            result = bridge.request({"tool": decision.name, **decision.arguments}, timeout=5, deadline=turn_end)
            observations.append({"tool": decision.name, "arguments": decision.arguments, "result": result})
            provider.observe(observations); persist("ready")
            record("tool_result", decision={"tool": decision.name, "code": result["code"]}, counters=read_snapshot(directory, "workflow"))
            status = result if "administrative_status" in result else status
            if result["code"] not in {"OK", "TRANSIENT"}: stop = "OPERATOR_REVIEW"; break
    except BridgeError:
        stop = "JAVA_REPLY_UNCERTAIN"
    except GatewayError as error:
        code = str(error)
        stop = "CANCELLED" if cancel.is_set() else "PROVIDER_TIMEOUT" if code in {"PROVIDER_TIMEOUT", "LATE_REPLY", "CANCELLED_OR_DEADLINE"} else "INVALID_PROVIDER_OUTPUT" if code.startswith(("INVALID_", "DUPLICATE_", "NONFINITE_", "MULTIPLE_", "MODEL_", "MIXED_", "INCOMPLETE_", "REPLY_")) else "PROVIDER_FAILURE"
        if provider.trace: record("inference_failure", stop=stop, transport=provider.trace[-1])
    finally:
        if bridge is not None:
            try:
                remaining_cleanup = (60000-int(read_snapshot(directory, "workflow")["cleanup_reserved_ms"]))/1000
                bridge.deadline = min(total_end, time.monotonic()+max(0, remaining_cleanup)+2)
                if bridge.process.poll() is None:
                    reason = {"CANCELLED": "ACTOR_STOPPED", "PROVIDER_TIMEOUT": "PROVIDER_TIMEOUT", "PROVIDER_FAILURE": "PROVIDER_FAILURE",
                              "INVALID_PROVIDER_OUTPUT": "INVALID_PROVIDER_OUTPUT", "ACTOR_BUDGET_EXHAUSTED": "ACTOR_BUDGET_EXHAUSTED"}.get(stop, "OPERATOR_REVIEW")
                    bridge.stop_actor(workflow, reason, timeout=max(.001, bridge.deadline-time.monotonic()-1.5))
            except (BridgeError, GatewayError):
                stop = "JAVA_REPLY_UNCERTAIN"
            finally:
                try:
                    bridge.close(force=bridge.process.poll() is None)
                except (BridgeError, TimeoutError):
                    stop = "OWNED_CLEANUP_UNCONFIRMED"
                if bridge.cleanup:
                    record("owned_cleanup", cleanup=bridge.cleanup)
                    append_jsonl(directory/"gateway-owned-cleanup.jsonl", {"kind": "java", **bridge.cleanup})
        for cleanup in exchange.cleanup:
            record("owned_cleanup", cleanup=cleanup)
            append_jsonl(directory/"gateway-owned-cleanup.jsonl", {"kind": "python-transport", **cleanup})
    if saved["phase"] != "failed": persist("paused" if stop == "APPROVAL_PAUSE" else "pending" if provider.pending else "ready")
    record("stop", stop=stop, counters=read_snapshot(directory, "workflow"))
    return finish_snapshot()

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["configure", "run"])
    parser.add_argument("--run-dir", required=True); parser.add_argument("--config", required=True)
    parser.add_argument("--endpoint")
    args = parser.parse_args(argv)
    try:
        if args.command == "configure": result = configure(args.run_dir, args.config)
        else:
            if not args.endpoint: raise GatewayError("LOCAL_DOUBLE_ENDPOINT_REQUIRED")
            result = run(args.run_dir, args.config, args.endpoint)
        print(canonical(result).decode())
        return 0 if args.command == "configure" or result["guarded"]["completed"] else 2
    except (GatewayError, BridgeError, AssertionError, ValueError, OSError):
        print("U1_HALTED_REVIEW_REQUIRED", file=sys.stderr); return 1

if __name__ == "__main__":
    raise SystemExit(main())
