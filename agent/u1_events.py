"""U1 telemetry is a whitelist projection; raw provider/domain text stays out."""
import hashlib
import math
import re
from .gateway import VERSION, PROMPT, canonical

EVENTS = {"session_start", "decision", "tool_result", "approval_pause", "stop", "verification", "owned_cleanup", "inference_failure"}
STOPS = {"APPROVAL_PAUSE", "FINAL_DRAFT", "REFUSAL", "CANCELLED", "PROVIDER_FAILURE", "PROVIDER_TIMEOUT",
         "INVALID_PROVIDER_OUTPUT", "ACTOR_BUDGET_EXHAUSTED", "JAVA_REPLY_UNCERTAIN", "HISTORY_UNCERTAIN",
         "OPERATOR_REVIEW", "COMPLETED", "OWNED_CLEANUP_UNCONFIRMED", "CLEANUP_BUDGET_EXHAUSTED"}

def hashed(value):
    return hashlib.sha256(str(value).encode()).hexdigest()

def event(kind, *, config_sha256, workflow_id, elapsed_ms=0, stop=None, counters=None,
          decision=None, transport=None, verification=None, cleanup=None):
    if kind not in EVENTS or not re.fullmatch(r"[0-9a-f]{64}", config_sha256) or stop is not None and stop not in STOPS:
        raise ValueError("INVALID_EVENT_METADATA")
    elapsed = float(elapsed_ms)
    if not math.isfinite(elapsed) or elapsed < 0: raise ValueError("INVALID_EVENT_TIME")
    result = {"schema": 1, "code_version": VERSION, "prompt_sha256": hashed(PROMPT),
              "config_sha256": config_sha256, "dataset": "authored-u1-offboard-v1", "kind": kind,
              "workflow_sha256": hashed(workflow_id), "mode": "local-double", "live_model": False,
              "model": "local/synthetic-tool-double", "elapsed_ms": round(elapsed, 3),
              "automatic_retries": 0, "actual_cost": None, "currency": None, "stop": stop}
    result["inference_allocation_inr"] = 0
    result["estimated_cost_reservation"] = None
    if counters is not None:
        result["counters"] = {k: int(counters[k]) for k in
            ("actor_calls", "provider_turns", "active_reserved_ms", "safety_calls", "cleanup_reserved_ms") if k in counters}
        limits = {"actor_calls": 32, "provider_turns": 12, "active_reserved_ms": 300000, "safety_calls": 12, "cleanup_reserved_ms": 60000}
        if any(not 0 <= v <= limits[k] for k, v in result["counters"].items()): raise ValueError("INVALID_EVENT_COUNTER")
    if decision is not None:
        result["decision_sha256"] = hashed(canonical(decision).decode())
    if transport is not None:
        result["generation_id_sha256"] = None if transport.get("generation_id") is None else hashed(transport["generation_id"])
        result["usage"] = None if transport.get("usage") is None else {k: int(transport["usage"][k]) for k in ("input_tokens", "output_tokens", "total_tokens")}
        for key in ("request_sha256", "response_sha256"):
            value = transport.get(key)
            if value is None: result[key] = None; continue
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value): raise ValueError("INVALID_EVENT_HASH")
            result[key] = value
        status = transport.get("http_status")
        if status is not None and (type(status) is not int or not 100 <= status <= 599): raise ValueError("INVALID_EVENT_HTTP_STATUS")
        result["http_status"] = status
    if verification is not None:
        result["guarded_completion"] = verification["completed"] is True
        result["verification_passed"] = verification["passed"] is True
        result["domain_access_revoked"] = verification["access_revoked"] is True
        result["physical_return_verified"] = False
    if cleanup is not None:
        exit_code = cleanup.get("exit_code")
        if exit_code is not None and (type(exit_code) is not int or not -(2**31) <= exit_code < 2**32): raise ValueError("INVALID_EVENT_EXIT_CODE")
        result["owned_cleanup"] = {"exit_code": exit_code, "live": cleanup.get("live") is not False,
            "owned_pid_sha256": hashed(cleanup.get("owned_pid")),
            "reader_live": cleanup.get("reader_live", False) is not False,
            "stderr_reader_live": cleanup.get("stderr_reader_live", False) is not False}
    return result
