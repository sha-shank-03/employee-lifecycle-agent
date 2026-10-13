"""Observation-driven offline baseline and shared evaluation input boundary.

No dataset, label, task ID, evaluator, credential or filesystem import. Both
policies use the existing typed provider loop and Java authority unchanged.
"""
import hashlib
import json
import re
from .protocol import FinalDraft, ToolCall, validate_call
from .providers import ScriptedProvider, TERMINAL

TEXT = "Process the current authorized lifecycle request using observed facts."
MODES = ("deterministic-v2", "scripted-adaptive")
FORBIDDEN = {"expected","label","labels","task_id","scenario_id","scenario","family","split",
             "driver","control","provenance","score","oracle","outcome_label"}

def reject_metadata(value):
    if type(value) is dict:
        if FORBIDDEN & set(value): raise ValueError("evaluation metadata in actor context")
        for child in value.values(): reject_metadata(child)
    elif type(value) is list:
        for child in value: reject_metadata(child)
    elif type(value) is str and re.search(r"U2B-[DC][0-9]{2}",value):
        raise ValueError("task identity in actor context")

def actor_request(value):
    if type(value) is not dict or set(value)!={"employee_id","intent","text"} \
            or any(type(v) is not str for v in value.values()) or value["intent"] not in {"onboard","offboard"} \
            or value["text"]!=TEXT:
        raise ValueError("neutral bounded actor request required")
    reject_metadata(value)
    if not value["employee_id"].startswith("E-") or not value["employee_id"][2:].isdigit() or len(value["employee_id"])>10:
        raise ValueError("fictional employee ID required")
    return dict(value)

def actor_context(request, observations):
    actor_request(request);reject_metadata(observations)
    if type(observations) is not list or len(observations)>32:
        raise ValueError("bounded observations required")
    for item in observations:
        if type(item) is not dict or set(item)-{"tool","arguments","result"} or not {"tool","result"}<=set(item) \
                or type(item["tool"]) is not str or type(item["result"]) is not dict:
            raise ValueError("typed observed tool result required")
    if len(json.dumps([request,observations],allow_nan=False).encode())>131072:
        raise ValueError("actor context too large")

class ObservationPolicy:
    mode="deterministic-v2"
    def next_turn(self,request,observations):
        employee=request["employee_id"]
        if not observations:return ToolCall("inspect_employee",{"employee_id":employee})
        last=observations[-1];result=last["result"]
        if result.get("code") not in {"OK","TRANSIENT"}:
            return FinalDraft("Operator review required; inspect authoritative state.")
        if last["tool"]=="inspect_employee":
            return ToolCall("read_policy",{"policy_id":"onboarding-v1" if request["intent"]=="onboard" else "offboarding-v1"})
        if last["tool"]=="read_policy":return ToolCall("propose_plan",{"employee_id":employee,"intent":request["intent"]})
        workflow=result.get("workflow_id")
        if not workflow:return FinalDraft("No authoritative workflow; operator review required.")
        state=result.get("administrative_status")
        if state in TERMINAL:return FinalDraft("Safe stop; inspect authoritative disposition.")
        if state=="COMPLETED":
            if last["tool"]=="verify_outcome":return FinalDraft("Inspect the independently scored final state.")
            return ToolCall("verify_outcome",{"workflow_id":workflow})
        # Java's current eligibility, including retry/compensation, overrides a
        # completed-step count or a remembered fixed action order.
        if str(result.get("retry_after_ms","0"))!="0" or not result.get("eligible_step"):
            return ToolCall("workflow_status",{"workflow_id":workflow})
        return ToolCall("execute_step",{"workflow_id":workflow,"step_id":result["eligible_step"]})

class EvaluationPolicy:
    def __init__(self,mode):
        if mode not in MODES:raise ValueError("offline comparison mode required")
        self.mode=mode;self.policy=ObservationPolicy() if mode=="deterministic-v2" else ScriptedProvider()
        self.decisions=[]
    def next_turn(self,request,observations):
        actor_context(request,observations)
        decision=self.policy.next_turn(request,observations)
        if isinstance(decision,ToolCall):validate_call(decision)
        elif not isinstance(decision,FinalDraft):raise ValueError("bounded offline decision required")
        self.decisions.append({"kind":"tool" if isinstance(decision,ToolCall) else "draft",
            "tool":decision.name if isinstance(decision,ToolCall) else None,
            "context_sha256":hashlib.sha256(json.dumps([request,observations],sort_keys=True,allow_nan=False).encode()).hexdigest()})
        return decision
