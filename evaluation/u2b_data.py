"""Pure authored-data validation and complete intended-slot planning. No unseen set."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from agent.bridge import ROOT
from agent.deterministic_v2 import MODES, actor_request
from agent.protocol import strict_json

DATA=Path("fixtures/u2b/manifest.json")
VERSION="u2b-author-exposed-1"
BUDGET={"actor_wall_seconds":120,"provider_decision_seconds":2,"max_turns":24,
        "max_actor_tools":32,"max_safety_tools":12,"retry_wait_cap_ms":2000}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def read_json(path):return strict_json(Path(path).read_text(encoding="utf-8"))

def validate_task(task,label):
    if type(task) is not dict or set(task)!={"schema","id","family","seed","request","control"} or task["schema"]!=1 \
            or type(task["id"]) is not str or type(task["family"]) is not str \
            or not re.fullmatch(r"U2B-[DC][0-9]{2}",task["id"]) or not re.fullmatch(r"[a-z_]{1,48}",task["family"]):
        raise ValueError("authored task schema required")
    request=actor_request(task["request"]);seed=task["seed"];control=task["control"]
    allowed={"employee_id","event_id","event_sequence","effective_at","enabled","sessions","grants","asset_id","asset_outage",
             "intent","role","account_exists","inventory_id","inventory_available","failure_step","cleanup_failure","turn_limit","receipt_unavailable","initial_version"}
    if type(seed) is not dict or set(seed)-allowed or seed.get("employee_id")!=request["employee_id"] \
            or seed.get("intent","offboard")!=request["intent"] or type(seed.get("turn_limit",24)) is not int \
            or not 1<=seed.get("turn_limit",24)<=24:
        raise ValueError("seed/actor identity or budget differs")
    if type(control) is not dict or set(control)-{"approve","cancel","after_step","crash_hooks","event","advance_seconds"} \
            or type(control.get("approve",True)) is not bool:
        raise ValueError("fixed operator schedule required")
    for key,value in seed.items():
        if key in {"event_sequence","sessions","initial_version","turn_limit"}:
            if type(value) is not int or value<0:raise ValueError("finite seed integer required")
        elif key in {"enabled","asset_outage","account_exists","inventory_available","cleanup_failure","receipt_unavailable"}:
            if type(value) is not bool:raise ValueError("typed seed boolean required")
        elif type(value) is not str or len(value)>256:raise ValueError("bounded seed string required")
    if type(control.get("cancel",False)) is not bool or type(control.get("after_step","")) is not str \
            or type(control.get("advance_seconds",0)) is not int or not 0<=control.get("advance_seconds",0)<=86400:
        raise ValueError("typed operator schedule required")
    hooks=control.get("crash_hooks",[])
    if type(hooks) is not list or len(hooks)>4 or any(h not in {
        "after_service_commit:disable_login"} for h in hooks):raise ValueError("authored recovery hook required")
    event=control.get("event")
    if event is not None and (type(event) is not dict or set(event)!={"employee_id","event_id","event_sequence","effective_at","intent","role"}
            or event["employee_id"]!=request["employee_id"] or type(event["event_sequence"]) is not int
            or event["event_sequence"]<=seed["event_sequence"] or event["intent"]!="offboard"):
        raise ValueError("declared successor event required")
    if type(label) is not dict or set(label)!={"id","expected"} or label["id"]!=task["id"] \
            or type(label["expected"]) is not dict \
            or label["expected"].get("employee_id")!=request["employee_id"]:
        raise ValueError("matching scorer-only label required")
    if type(label["expected"].get("business_effects")) is not int or label["expected"]["business_effects"]<0:
        raise ValueError("independent expected effects required")
    return task,label

def load_split(split,root=ROOT):
    if split not in {"development","capability"}:raise ValueError("author-exposed split only")
    root=Path(root).resolve();manifest=read_json(root/DATA)
    if type(manifest) is not dict or manifest.get("schema")!=1 or manifest.get("version")!=VERSION or manifest.get("license")!="MIT" or manifest.get("exposure")!="author-exposed" \
            or manifest.get("synthetic") is not True or manifest.get("unseen") is not False:
        raise ValueError("explicit synthetic provenance/exposure required")
    entry=manifest["splits"][split]
    for key in ("inputs","labels"):
        relative=entry[key]["path"];path=PurePosixPath(relative);target=root/relative
        if relative!=f"fixtures/u2b/{split}-{key}.jsonl" or path.is_absolute() or ".." in path.parts \
                or not target.resolve().is_relative_to(root) or target.stat().st_size>65536 \
                or any(p.is_symlink() for p in (target,*target.parents) if p.is_relative_to(root)) \
                or sha(target)!=entry[key]["sha256"]:
            raise ValueError("authored file path/hash differs")
    tasks=[strict_json(line) for line in (root/entry["inputs"]["path"]).read_text(encoding="utf-8").splitlines()]
    labels=[strict_json(line) for line in (root/entry["labels"]["path"]).read_text(encoding="utf-8").splitlines()]
    if not 1<=len(tasks)<=({"development":12,"capability":24}[split]) or len(tasks)!=len(labels):raise ValueError("bounded complete data rows required")
    ids=[t["id"] for t in tasks]
    if len(set(ids))!=len(ids) or ids!=entry["ids"] or [l["id"] for l in labels]!=ids:raise ValueError("missing/duplicate/reordered task label")
    families=sorted({t["family"] for t in tasks})
    if families!=entry["families"] or len(tasks)!=entry["tasks"]:raise ValueError("declared task/family counts differ")
    for task,label in zip(tasks,labels):validate_task(task,label)
    declared=manifest["splits"]
    all_ids=declared["development"]["ids"]+declared["capability"]["ids"]
    if len(set(all_ids))!=len(all_ids) or len(all_ids)!=manifest["unique_records"] \
            or len(set(declared["development"]["families"]+declared["capability"]["families"]))!=manifest["scenario_families"]:
        raise ValueError("cross-split counts differ")
    provenance={p["id"]:p for p in manifest["provenance"]}
    if len(provenance)!=len(all_ids) or set(provenance)!=set(all_ids):raise ValueError("complete authored provenance required")
    for task in tasks:
        record=provenance[task["id"]]
        if record["license"]!="MIT" or record["source_family"].replace("-","_")!=task["family"]:
            raise ValueError("family provenance differs")
        if set(record["source_hashes"])!={f"fixtures/dev/{record['source_family']}/{name}.json" for name in ("seed","driver","expected")}:
            raise ValueError("complete source provenance hashes required")
        for relative,expected in record["source_hashes"].items():
            if relative not in {f"fixtures/dev/{record['source_family']}/{name}.json" for name in ("seed","driver","expected")} \
                    or sha(root/relative)!=expected:raise ValueError("source provenance hash differs")
    return {"manifest":manifest,"manifest_sha256":sha(root/DATA),"split":split,"tasks":tasks,"labels":{l["id"]:l["expected"] for l in labels},"families":families}

def plan_slots(bundle,selected=None):
    available={t["id"]:t for t in bundle["tasks"]};ids=list(available if selected is None else selected)
    if not ids or len(set(ids))!=len(ids) or set(ids)-set(available):raise ValueError("declared unique selected task IDs required")
    slots=[]
    for task_id in ids:
        task=available[task_id]
        for mode in MODES:
            slots.append({"slot_id":task_id+":"+mode,"task_id":task_id,"family":task["family"],"policy":mode,"repetition":1,
                "input_sha256":digest(task),"approval_schedule_sha256":digest(task["control"]),
                "budget_sha256":digest({**BUDGET,"task_turn_limit":task["seed"].get("turn_limit",24)}),
                "status":"PLANNED","elapsed_ms":None,"expected_match":None,"actual_completion":None,
                "safety_passed":None,"metrics":None,"usage":None,"actual_cost_usd":None,"error_code":None})
    return {"schema":1,"version":VERSION,"split":bundle["split"],"dataset_manifest_sha256":bundle["manifest_sha256"],
        "exposure":"author-exposed","unseen":False,"synthetic":True,"policies":list(MODES),"budget":dict(BUDGET),
        "intended_task_ids":ids,"available_tasks":len(available),"intended_slots":len(slots),"slots":slots,
        "provider_quality_evaluated":False,"live_model_calls":0}

def check_slots(plan,slots):
    ids=plan["intended_task_ids"]
    roster=[task_id+":"+mode for task_id in ids for mode in MODES]
    if not ids or len(set(ids))!=len(ids) or plan["policies"]!=list(MODES) \
            or [s["slot_id"] for s in plan["slots"]]!=roster or plan["intended_slots"]!=len(roster):
        raise ValueError("complete paired plan required")
    expected=[s["slot_id"] for s in plan["slots"]];actual=[s["slot_id"] for s in slots]
    if len(set(actual))!=len(actual) or actual!=expected or len(slots)!=plan["intended_slots"]:
        raise ValueError("omitted/duplicate/reordered intended slot")
    for original,slot in zip(plan["slots"],slots):
        for key in ("slot_id","task_id","family","policy","repetition","input_sha256","approval_schedule_sha256","budget_sha256"):
            if original[key]!=slot[key]:raise ValueError("slot input/authority/budget identity changed")
        if slot["status"] not in {"PLANNED","RUNNING","SCORED","FAILED","TIMEOUT","UNKNOWN"}:raise ValueError("unknown slot status")
        for key in ("actual_completion","safety_passed","expected_match"):
            if slot[key] is not None and type(slot[key]) is not bool:raise ValueError("typed verdict required")
        if slot["status"] in {"PLANNED","RUNNING"} and any(slot[k] is not None for k in ("metrics","actual_completion","safety_passed","expected_match")):
            raise ValueError("unscored slot claims an outcome")
        if slot["status"]=="SCORED" and slot["metrics"] is None:raise ValueError("scored slot missing evidence")
    return True
