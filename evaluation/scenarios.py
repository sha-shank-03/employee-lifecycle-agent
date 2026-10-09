"""Operator-owned fictional scenario driver. Control schedules and labels stay outside providers."""
from pathlib import Path
import xml.etree.ElementTree as ET
from agent.bridge import BridgeError, JavaBridge
from agent.cli import act, approve_review, create_review, operator, read_json, write_json
from agent.loop import run_loop
from agent.protocol import FinalDraft, ToolCall
from evaluation.verifier import parse_snapshot, read_snapshot, snapshot_files
from evaluation.recovery import read_packets


def string_fields(fields):
    return {k: str(v).lower() if type(v) is bool else str(v) for k, v in fields.items()}


def initialize_case(seed, request, run_dir):
    directory = Path(run_dir)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError("run directory must be empty")
    result = operator(directory, "init", **string_fields(seed))
    write_json(directory / "request.json", request)
    return result["workflow_id"]


def raw_step(run_dir, workflow, step, crash_hook=None):
    with JavaBridge(run_dir, crash_after=crash_hook) as bridge:
        return bridge.call(ToolCall("execute_step", {"workflow_id": workflow, "step_id": step}))


def advance_to(run_dir, workflow, target=None, crash_hook=None):
    state = operator(run_dir, "report", workflow_id=workflow)
    bridge = None
    try:
        for _ in range(20):
            if state["administrative_status"] not in {"RUNNING", "RETRY_PENDING"}:
                return state
            step = state["eligible_step"]
            if not step:
                if bridge is not None:
                    bridge.close()
                    bridge = None
                operator(run_dir, "advance_clock", workflow_id=workflow, seconds="3")
                state = operator(run_dir, "report", workflow_id=workflow)
                continue
            if bridge is None:
                bridge = JavaBridge(run_dir, crash_after=crash_hook)
            try:
                state = bridge.call(ToolCall("execute_step", {"workflow_id": workflow, "step_id": step}))
            except BridgeError as error:
                error.child_returncode = bridge.process.returncode
                error.owned_child_pid = bridge.process.pid
                raise
            if state["code"] not in {"OK", "TRANSIENT"}:
                raise AssertionError("unexpected driver denial " + state["code"])
            if step == target and state["code"] == "OK":
                return state
        raise AssertionError("finite driver bound exceeded")
    finally:
        if bridge is not None:
            bridge.close()


def external_edit(run_dir, changes):
    files = snapshot_files(run_dir, "identity")
    state = parse_snapshot(files[-1])
    state.update(string_fields(changes))
    state["version"] = str(int(state["version"]) + 1)
    state["external_edit"] = "authored-fixture"
    root = ET.Element("snapshot", schema="1")
    for k, v in sorted(state.items()):
        ET.SubElement(root, "field", name=k).text = v
    generation = int(files[-1].stem) + 1
    (Path(run_dir) / "identity" / f"{generation:020d}.xml").write_bytes(ET.tostring(root, encoding="utf-8"))


class AdversarialDouble:
    mode = "authored-adversarial-double"
    def __init__(self, kind):
        self.kind = kind
    def next_turn(self, *_):
        return FinalDraft("Everything completed") if self.kind == "false_success" else {"tool": "approve", "digest": "invented"}


def run_case(seed, request, control, run_dir, mode="scripted-adaptive"):
    """Labels are deliberately not an argument."""
    workflow = initialize_case(seed, request, run_dir)
    if control.get("proposal_extra"):
        with JavaBridge(run_dir) as bridge:
            result = bridge.request({"tool": "propose_plan", "employee_id": seed["employee_id"],
                                     "intent": request["intent"], **control["proposal_extra"]})
        if result["code"] != "INVALID_ARGUMENTS":
            raise AssertionError("injected proposal field was accepted")
        return operator(run_dir, "report", workflow_id=workflow)
    try:
        act(run_dir, request, provider=mode)
    except ValueError:
        if not control.get("request_rejection"):
            raise
        return operator(run_dir, "report", workflow_id=workflow)
    state = operator(run_dir, "report", workflow_id=workflow)
    if state["administrative_status"] != "AWAITING_APPROVAL":
        return state
    if not control.get("approve", True):
        return state
    packet, review_path = create_review(run_dir, workflow)
    denial = control.get("approval_denial")
    if denial:
        with JavaBridge(run_dir, mode="operator") as bridge:
            result = bridge.request({"tool": "approve", "workflow_id": workflow,
                                     "digest": "0" * 64 if denial == "APPROVAL_DIGEST_MISMATCH" else packet["digest"],
                                     "approver": "asset_operator" if denial == "APPROVER_DENIED" else "hr-reviewer"})
        if result["code"] != denial:
            raise AssertionError("approval denial contract failed")
        return operator(run_dir, "report", workflow_id=workflow)
    approve_review(run_dir, workflow, review_path, "hr-reviewer")
    if control.get("advance_seconds"):
        operator(run_dir, "advance_clock", workflow_id=workflow, seconds=str(control["advance_seconds"]))
    if control.get("external_edit"):
        external_edit(run_dir, control["external_edit"])
    if control.get("after_step"):
        advance_to(run_dir, workflow, target=control["after_step"])
    if control.get("cancel"):
        return operator(run_dir, "cancel", workflow_id=workflow)
    if control.get("event"):
        operator(run_dir, "import_event", **string_fields(control["event"]))
        # Directly prove both old access-addition entry points are fenced.
        denials = {a: raw_step(run_dir, workflow, a)["code"] for a in ("add_role_grants", "enable_login")}
        if set(denials.values()) != {"STALE_APPROVAL"}:
            raise AssertionError("superseded grant/enable not fenced")
        write_json(Path(run_dir) / "event-fence-check.json", denials)
        return operator(run_dir, "report", workflow_id=workflow)
    if control.get("event_attempt"):
        with JavaBridge(run_dir, mode="operator") as bridge:
            denied = bridge.request({"tool": "import_event", **string_fields(control["event_attempt"])})
        if denied["code"] != control["event_denial"]:
            raise AssertionError("source event denial contract failed")
    if control.get("event_replay"):
        before = read_snapshot(run_dir, "hr")
        event = {k: seed[k] for k in ("employee_id", "event_id", "event_sequence", "effective_at")}
        event.update(intent=seed.get("intent", "offboard"), role=seed.get("role", "engineer"))
        operator(run_dir, "import_event", **string_fields(event))
        if read_snapshot(run_dir, "hr") != before:
            raise AssertionError("same-event replay mutated authority")
    if control.get("duplicate_step"):
        target = control["duplicate_step"]
        advance_to(run_dir, workflow, target=target)
        before = {n: read_snapshot(run_dir, n) for n in ("hr", "identity", "assets")}
        raw_step(run_dir, workflow, target)
        if before != {n: read_snapshot(run_dir, n) for n in before}:
            raise AssertionError("duplicate step changed domain state")
    for index, hook in enumerate(control.get("crash_hooks", [])):
        marker = Path(run_dir) / "crash-fired.marker"
        if index:
            marker.unlink()  # exact harness-owned marker, never a recursive operation
        try:
            advance_to(run_dir, workflow, crash_hook=hook)
        except BridgeError as error:
            if getattr(error, "child_returncode", None) != 91 or not marker.exists() or marker.read_text().strip() != hook:
                raise
            phase, step = hook.split(":")
            checkpoint = read_snapshot(run_dir, "workflow")
            service = "assets" if step == "create_collection_task" else "identity"
            committed = "ledger." + str(seed["event_sequence"]) + "." + step in read_snapshot(run_dir, service)
            if committed != (phase in {"after_service_commit", "after_result"}):
                raise AssertionError("crash window service evidence differs")
            packet = {"owned_process_crash": True, "child_exit_code": error.child_returncode,
                      "owned_child_pid": error.owned_child_pid, "marker": marker.read_text().strip(),
                      "service_committed": committed, "workflow_acknowledged": checkpoint["step." + step] == "DONE",
                      "hook": hook, "workflow": checkpoint,
                      "services": {n: read_snapshot(run_dir, n) for n in ("hr", "identity", "assets")}}
            write_json(Path(run_dir) / "recovery-checkpoint.json", packet)
            packets_path = Path(run_dir) / "recovery-checkpoints.json"
            prior_packets = read_packets(packets_path) if packets_path.exists() else []
            write_json(packets_path, {"packets": prior_packets + [packet]})
        else:
            raise AssertionError("expected actual owned-process crash")
    if control.get("adversarial_provider"):
        with JavaBridge(run_dir) as bridge:
            trace = run_loop(AdversarialDouble(control["adversarial_provider"]), bridge,
                             {**request, "workflow_id": workflow})
        write_json(Path(run_dir) / "adversarial-trace.json", trace)
    else:
        act(run_dir, request, provider=mode)
    return operator(run_dir, "report", workflow_id=workflow)

