"""One frozen catalog, append-only remainder accounting and bounded main slices.

The first four native slots remain under their original bindings. This layer
does not change actors, labels, approval schedules, budgets or domain semantics.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from agent.bridge import ROOT
from agent.deterministic_v2 import EvaluationPolicy
from .current_source import MANIFEST, check_current_source
from .scenarios import run_case
from .u2b import RESOURCES, summarize_saved
from .u2b_data import BUDGET, MODES, digest, load_split, plan_slots, read_json, sha
from .u2b_score import ERRORS, number, score_evidence, summarize
from .verifier import parse_snapshot, snapshot_files

VERSION="u2b-catalog-continuation-1"
REVIEW="evaluation/upgrade/history/u2b-first-native-main-review.json"
FIRST_SOURCE="733259be6f410953a6599c74b67118d6dad365907b382e657e6e494ccd8bb061"
FIRST_IDS=("U2B-D01","U2B-D07")
CATALOG_PATH="runs/u2b-catalog-20261012"
IDENTITY=("slot_id","task_id","family","policy","repetition","input_sha256","approval_schedule_sha256","budget_sha256")
VERDICT=("expected_match","actual_completion","safety_passed","metrics")
TERMINAL={"SCORED","FAILED","TIMEOUT","UNKNOWN"}

def all_data(root=ROOT):
    bundles=[load_split(s,root) for s in ("development","capability")]
    return {"manifest_sha256":bundles[0]["manifest_sha256"],"split":"catalog",
        "tasks":[t for b in bundles for t in b["tasks"]],"labels":{k:v for b in bundles for k,v in b["labels"].items()}}

def file_pins(folder):
    folder=Path(folder).resolve()
    files={}
    for p in sorted(folder.rglob("*")):
        if p.is_symlink() or not p.resolve().is_relative_to(folder):raise ValueError("raw evidence path escape")
        if p.is_file():files[p.relative_to(folder).as_posix()]=sha(p)
    return files

def verify_pins(folder,pins):
    if type(pins) is not dict or file_pins(folder)!=pins:raise ValueError("raw evidence binding changed")

def first_binding(root=ROOT):
    root=Path(root);review=read_json(root/REVIEW)
    if review["source_manifest_sha256"]!=FIRST_SOURCE or review["first_path"]!="runs/u2b-main-first-20261012" \
            or (review["actual_completions"],review["expected_safe_compensations"],review["remaining_records"],review["remaining_slots"])!=(2,2,18,36):
        raise ValueError("original first-slice review differs")
    run=root/review["first_path"]
    actual={review["first_path"]+"/"+k:v for k,v in file_pins(run).items()}
    if actual!=review["first_raw_files"]:raise ValueError("first native evidence changed")
    ledger=read_json(run/"ledger.json")
    if ledger["plan"]["source_manifest_sha256"]!=FIRST_SOURCE or ledger["plan"]["intended_task_ids"]!=list(FIRST_IDS):
        raise ValueError("first original population changed")
    if len(ledger["slots"])!=4 or any(s["status"]!="SCORED" or s["expected_match"] is not True for s in ledger["slots"]):
        raise ValueError("first original verdict changed")
    report=summarize_saved(run)
    if report["all_intended"]["actual_completion_per_intended_slot"]["numerator"]!=2 \
            or report["all_intended"]["expected_safe_stops"]!=2:raise ValueError("first completion misclassified")
    return {"review_path":REVIEW,"review_sha256":sha(root/REVIEW),
            "original_main_review_sha256":review["original_main_review_sha256"],
            "source_manifest_sha256":FIRST_SOURCE,"dataset_manifest_sha256":ledger["plan"]["dataset_manifest_sha256"],
            "raw_files_sha256":digest(review["first_raw_files"]),"intent_sha256":sha(run/"intent.json"),
            "ledger_sha256":sha(run/"ledger.json"),"selected_task_ids":list(FIRST_IDS),"slots":deepcopy(ledger["slots"]),
            "original_report":report}

def build_intent(root=ROOT):
    data=all_data(root);first=first_binding(root);whole=plan_slots(data)
    remaining=[t["id"] for t in data["tasks"] if t["id"] not in FIRST_IDS]
    remainder=plan_slots(data,remaining)
    if len(remaining)!=18 or remainder["intended_slots"]!=36 or whole["intended_slots"]!=40 \
            or data["manifest_sha256"]!=first["dataset_manifest_sha256"]:raise ValueError("original 20-record catalog differs")
    return {"schema":1,"version":VERSION,"source_manifest_sha256":sha(Path(root)/MANIFEST),
            "catalog_path":CATALOG_PATH,
            "dataset_manifest_sha256":data["manifest_sha256"],"first":first,"full_plan":whole,"remainder_plan":remainder,
            "label_sha256":{k:digest(v) for k,v in data["labels"].items()},"unique_records":20,"scenario_families":12,
            "shared_development_capability_families":8,"exposure":"author-exposed","unseen":False,
            "synthetic":True,"live_model_quality_evaluated":False}

def initial_state_sha(intent):return digest({"intent_sha256":digest(intent),"events":[],"pending":{}})

def validate_capture(body):
    if type(body) is not dict or set(body)!={"actor_result","error_code","elapsed_ms","raw_files","decision_count","decision_sha256"} \
            or body["actor_result"] not in {"RETURNED","FAILED","TIMEOUT"} \
            or type(body["decision_count"]) is not int or body["decision_count"]<0 \
            or type(body["raw_files"]) is not dict or not re.fullmatch(r"[0-9a-f]{64}",body["decision_sha256"]):
        raise ValueError("bounded durable capture required")
    number(body["elapsed_ms"])
    if body["elapsed_ms"] is None or (body["error_code"] is not None and not re.fullmatch(r"ACTOR_[A-Za-z][A-Za-z0-9_]{0,63}",body["error_code"])):
        raise ValueError("redacted capture error/time required")

def catalog_path(value,root=ROOT):
    root=Path(root).resolve();p=Path(value).resolve()
    if p!=root/CATALOG_PATH \
            or any(a.is_symlink() for a in (p,*p.parents) if a.is_relative_to(root)):
        raise ValueError("owned catalog child of runs required")
    return p

def publish(path,value):
    """Exclusive staging + file fsync + rename. No Windows power-loss guarantee."""
    path=Path(path);pending=path.with_suffix(".pending")
    if path.exists():raise ValueError("immutable accounting file already exists")
    with pending.open("x",encoding="utf-8") as stream:
        stream.write(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n")
        stream.flush();os.fsync(stream.fileno())
    if path.exists():raise ValueError("immutable accounting file collision")
    pending.rename(path)

def initialize(folder,root=ROOT):
    check_current_source(root);folder=catalog_path(folder,root)
    if folder.exists():raise ValueError("catalog already exists; never replace its population")
    intent=build_intent(root);folder.mkdir(parents=True);(folder/"events").mkdir()
    publish(folder/"intent.json",intent)  # All 36 future slots before any actor entry.
    return intent

class Catalog:
    def __init__(self,folder,root=ROOT):
        self.root=Path(root);self.folder=catalog_path(folder,root);self.intent=read_json(self.folder/"intent.json")
        if self.intent!=build_intent(root):raise ValueError("catalog source/data/first/authority/budget population changed")
        self.plan=self.intent["remainder_plan"]
    def state(self):
        slots={s["slot_id"]:{**deepcopy(s),"status":"UNEXECUTED","capture":None,"verdict":None} for s in self.plan["slots"]}
        events=[];previous=None;halted=False
        paths=sorted((self.folder/"events").glob("*.json"))
        for number,path in enumerate(paths,1):
            event=read_json(path)
            if path.name!=f"{number:06d}.json" or event["schema"]!=1 or event["sequence"]!=number \
                    or event["previous_sha256"]!=previous or event["source_manifest_sha256"]!=self.intent["source_manifest_sha256"]:
                raise ValueError("event ordering/source/chain changed")
            row=slots.get(event["slot_id"])
            if row is None or any(event[k]!=row[k] for k in IDENTITY):raise ValueError("event slot authority/budget changed")
            kind=event["kind"];body=event["body"]
            if kind=="STARTED":
                if halted or row["status"]!="UNEXECUTED" or any(s["status"] in {"STARTED","CAPTURED"} for s in slots.values()):
                    raise ValueError("started slot replay, parallel entry or work after stop")
                row["status"]="STARTED"
            elif kind=="CAPTURED":
                validate_capture(body)
                if row["status"]!="STARTED" or body["actor_result"] not in {"RETURNED","FAILED","TIMEOUT"}:
                    raise ValueError("result without serial start")
                row.update(status="CAPTURED",capture=body)
            elif kind=="CLASSIFIED":
                if row["status"]!="CAPTURED" or body["status"] not in TERMINAL:raise ValueError("classification before durable capture")
                row.update(status=body["status"],verdict=body["verdict"])
                if row["capture"]["actor_result"]!="RETURNED" and body["status"]=="SCORED":raise ValueError("negative actor result promoted to success")
                if body["status"]!="SCORED" or body["verdict"]["expected_match"] is not True:halted=True
            else:raise ValueError("unknown accounting event")
            previous=sha(path);events.append(previous)
        pending={p.name:sha(p) for p in sorted((self.folder/"events").glob("*.pending"))}
        for row in slots.values():
            if row["status"]=="UNEXECUTED" and self.run_folder(row).exists():raise ValueError("orphan output or missing STARTED event")
        state_sha=digest({"intent_sha256":digest(self.intent),"events":events,"pending":pending})
        return {"slots":list(slots.values()),"events":events,"pending":pending,"halted":halted,
                "state_sha256":state_sha,"tail_sha256":previous,
                "incomplete_capture":any(s["status"] in {"STARTED","CAPTURED"} for s in slots.values())}
    def append(self,kind,row,body,grant_sha):
        state=self.state()
        current=next((s for s in state["slots"] if s["slot_id"]==row["slot_id"]),None)
        if current is None or any(current[k]!=row[k] for k in IDENTITY):raise ValueError("event authority/budget identity changed")
        if state["pending"]:raise ValueError("unfinished durable write; no further entries")
        if kind=="STARTED":
            if state["halted"] or state["incomplete_capture"] or current["status"]!="UNEXECUTED":raise ValueError("slot replay/parallel entry or work after stop")
        elif kind=="CAPTURED":
            if current["status"]!="STARTED":raise ValueError("capture without durable start")
            validate_capture(body)
        elif kind=="CLASSIFIED":
            if current["status"]!="CAPTURED" or body!=self.classify(current,current["capture"]):raise ValueError("classification before capture or forged verdict")
        else:raise ValueError("unknown accounting event")
        event={"schema":1,"sequence":len(state["events"])+1,"previous_sha256":state["tail_sha256"],
               "source_manifest_sha256":self.intent["source_manifest_sha256"],"grant_sha256":grant_sha,
               "kind":kind,**{k:row[k] for k in IDENTITY},"body":body}
        publish(self.folder/"events"/f"{event['sequence']:06d}.json",event)
        return event
    def selected(self,ids):
        self.report()  # Existing classified/raw results must still bind before any new actor entry.
        state=self.state();allowed=self.plan["intended_task_ids"]
        if state["halted"] or state["pending"] or state["incomplete_capture"]:raise ValueError("catalog stopped or incomplete; main review required")
        if not 1<=len(ids)<=2 or len(set(ids))!=len(ids) or ids!=[x for x in allowed if x in ids]:
            raise ValueError("at most two canonical untouched task pairs required")
        rows=[s for s in state["slots"] if s["task_id"] in ids]
        if len(rows)!=2*len(ids) or any(s["status"]!="UNEXECUTED" for s in rows):raise ValueError("task pair was already started")
        return rows,state
    def run_folder(self,row):return self.folder/"slots"/row["task_id"]/row["policy"]
    def classify(self,row,capture):
        path=self.run_folder(row);verify_pins(path,capture["raw_files"])
        data=all_data(self.root);task=next(t for t in data["tasks"] if t["id"]==row["task_id"])
        try:
            for service in ("workflow","hr","identity","assets"):
                for snapshot in snapshot_files(path,service):
                    if parse_snapshot(snapshot).get("employee_id")!=task["request"]["employee_id"]:
                        raise ValueError("evidence identity differs")
        except ERRORS as error:
            return {"status":"UNKNOWN","verdict":{"expected_match":False,"actual_completion":None,
                "safety_passed":None,"metrics":None,"error_code":"EVIDENCE_"+type(error).__name__}}
        verdict=score_evidence(path,data["labels"][row["task_id"]],task["control"])
        verify_pins(path,capture["raw_files"])
        status="TIMEOUT" if capture["actor_result"]=="TIMEOUT" else "FAILED" if capture["actor_result"]=="FAILED" \
            else "UNKNOWN" if verdict["metrics"] is None else "FAILED" if verdict["expected_match"] is not True else "SCORED"
        return {"status":status,"verdict":verdict}
    def report(self):
        state=self.state();legacy=[]
        for row in state["slots"]:
            original=next(s for s in self.plan["slots"] if s["slot_id"]==row["slot_id"]);slot=deepcopy(original)
            if row["capture"] is not None:verify_pins(self.run_folder(row),row["capture"]["raw_files"])
            if row["verdict"] is not None:
                fresh=self.classify(row,row["capture"])
                if fresh!={"status":row["status"],"verdict":row["verdict"]}:raise ValueError("stored verdict/raw evidence forgery")
                slot.update(status=row["status"],**{k:row["verdict"][k] for k in VERDICT},elapsed_ms=row["capture"]["elapsed_ms"],actual_cost_usd=0)
            elif row["status"]!="UNEXECUTED":slot["status"]="UNKNOWN"
            legacy.append(slot)
        first={s["slot_id"]:deepcopy(s) for s in self.intent["first"]["slots"]}
        remaining={s["slot_id"]:s for s in legacy};full=self.intent["full_plan"]
        combined=[first.get(s["slot_id"],remaining.get(s["slot_id"])) for s in full["slots"]]
        report={"schema":1,"version":VERSION,"intent_sha256":digest(self.intent),"state_sha256":state["state_sha256"],
            "source_manifest_sha256":self.intent["source_manifest_sha256"],"dataset_manifest_sha256":self.intent["dataset_manifest_sha256"],
            "first_original_source_sha256":FIRST_SOURCE,"first_main_review_sha256":self.intent["first"]["original_main_review_sha256"],
            "first_original_slots":4,"first_original_report":self.intent["first"]["original_report"],
            "remaining_intended_slots":36,"catalog_intended_slots":40,"unique_records":20,
            "scenario_families":12,"shared_split_families":8,"remainder_status_counts":dict(Counter(s["status"] for s in state["slots"])),
            "unexecuted_slot_ids":[s["slot_id"] for s in state["slots"] if s["status"]=="UNEXECUTED"],
            "unknown_slot_ids":[s["slot_id"] for s in state["slots"] if s["status"] in {"STARTED","CAPTURED","UNKNOWN"}],
            "slots":[{"slot_id":s["slot_id"],"status":s["status"],"actual_completion":s["actual_completion"],
                "expected_match":s["expected_match"],"safety_passed":s["safety_passed"],
                "source_manifest_sha256":FIRST_SOURCE if s["slot_id"] in first else self.intent["source_manifest_sha256"],
                "input_sha256":s["input_sha256"],"approval_schedule_sha256":s["approval_schedule_sha256"],
                "budget_sha256":s["budget_sha256"]} for s in combined],
            "halted":state["halted"],"active_lock_present":(self.folder/"active.lock").exists(),
            "blocked_incomplete_write_or_capture":bool(state["pending"] or state["incomplete_capture"]),
            "remainder":summarize(self.plan,legacy),"entire_catalog":summarize(full,combined),
            "exposure":"author-exposed","unseen":False,"live_model_calls":0,"external_sandbox_calls":0,
            "limits":"Four first slots retain original evidence/source bindings: two departures complete, two safe compensations. This is one correlated20-record/12-family catalog, not40independent tasks. Unexecuted/unknown slots remain denominators; no live/provider uplift. Exclusive/fsync/rename accounting is not a portable Windows power-loss guarantee."}
        return report

def preview_report(root=ROOT):
    """Read-only projection of the initial catalog; never ignore an existing registry."""
    folder=Path(root)/CATALOG_PATH
    if folder.exists():raise ValueError("catalog exists; use its actual report")
    intent=build_intent(root)
    catalog=object.__new__(Catalog)
    catalog.root=Path(root);catalog.folder=folder;catalog.intent=intent;catalog.plan=intent["remainder_plan"]
    return catalog.report()

def validate_slice_grant(grant,catalog,ids,root=ROOT,now=None):
    rows,state=catalog.selected(ids);now=now or datetime.now(timezone.utc)
    if type(grant) is not dict or not re.fullmatch(r"employee-u2b-catalog-[a-z0-9-]{1,48}",grant.get("name","")) \
            or grant.get("status")!="active" or grant.get("owner")!="main" or grant.get("slug")!="employee-lifecycle-agent" \
            or grant.get("source_manifest_sha256")!=catalog.intent["source_manifest_sha256"] \
            or grant.get("dataset_manifest_sha256")!=catalog.intent["dataset_manifest_sha256"] \
            or grant.get("catalog_intent_sha256")!=digest(catalog.intent) or grant.get("catalog_state_sha256")!=state["state_sha256"] \
            or grant.get("selected_task_ids")!=ids or grant.get("selected_slot_sha256")!=digest([{k:s[k] for k in IDENTITY} for s in rows]) \
            or grant.get("resources")!=RESOURCES or any(type(grant["resources"][k]) is not type(v) for k,v in RESOURCES.items()):
        raise ValueError("exact main source/data/intent/state/authority/budget grant required")
    expires=datetime.fromisoformat(grant["expires_at_utc"])
    if expires.utcoffset() is None or (expires-now).total_seconds()<240:raise ValueError("240 seconds including teardown must remain")
    pins=grant.get("class_sha256");classes=Path(root)/".build/classes"
    actual={p.relative_to(classes).as_posix():sha(p) for p in sorted(classes.rglob("*.class"))}
    if type(pins) is not dict or len(actual)!=14 or actual!=pins:raise ValueError("14 unchanged cached class pins required")
    return rows,state

def run_slice(folder,ids,grant_path,root=ROOT):
    check_current_source(root);catalog=Catalog(folder,root);lock=catalog.folder/"active.lock"
    with lock.open("x",encoding="utf-8") as stream:stream.write("main slice; never automatically clear a crash lock\n")
    try:
        grant=read_json(grant_path);rows,_=validate_slice_grant(grant,catalog,ids,root);grant_sha=digest(grant)
        data=all_data(root);tasks={t["id"]:t for t in data["tasks"]};deadline=time.monotonic()+RESOURCES["command_seconds"]
        for row in rows:
            if time.monotonic()>=deadline:return 1  # Untouched future slots stay UNEXECUTED.
            path=catalog.run_folder(row)
            if path.exists():raise ValueError("original slot output exists; never replace or replay")
            catalog.append("STARTED",row,{"lease_name":grant["name"]},grant_sha)
            started=time.monotonic();task=tasks[row["task_id"]];policy=EvaluationPolicy(row["policy"])
            actor_result="RETURNED";error_code=None
            try:run_case(deepcopy(task["seed"]),deepcopy(task["request"]),deepcopy(task["control"]),path,mode=policy)
            except TimeoutError:actor_result="TIMEOUT";error_code="ACTOR_TimeoutError"
            except Exception as error:actor_result="FAILED";error_code="ACTOR_"+type(error).__name__
            capture={"actor_result":actor_result,"error_code":error_code,"elapsed_ms":round((time.monotonic()-started)*1000,3),
                "raw_files":file_pins(path),"decision_count":len(policy.decisions),"decision_sha256":digest(policy.decisions)}
            catalog.append("CAPTURED",row,capture,grant_sha)  # Durable raw evidence before any label/scoring decision.
            classified=catalog.classify(row,capture)
            catalog.append("CLASSIFIED",row,classified,grant_sha)
            if classified["status"]!="SCORED" or classified["verdict"]["expected_match"] is not True:return 1
        return 0
    finally:
        lock.unlink()  # Only this invocation's exact exclusive sentinel; process death leaves it for main review.

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("plan")
    sub.add_parser("preview")
    init=sub.add_parser("init");init.add_argument("--catalog",required=True)
    report=sub.add_parser("report");report.add_argument("--catalog",required=True)
    run=sub.add_parser("run");run.add_argument("--catalog",required=True);run.add_argument("--ids",required=True);run.add_argument("--main-grant",required=True)
    args=parser.parse_args(argv)
    if args.command=="plan":print(json.dumps(build_intent(),indent=2));return 0
    if args.command=="preview":print(json.dumps(preview_report(),indent=2));return 0
    if args.command=="init":print(json.dumps({"intent_sha256":digest(initialize(args.catalog))}));return 0
    if args.command=="report":print(json.dumps(Catalog(args.catalog).report(),indent=2));return 0
    return run_slice(args.catalog,args.ids.split(","),args.main_grant)

if __name__=="__main__":raise SystemExit(main())
