"""Main-leased offline paired runner. No auto-build, downloads, live provider or retry."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from agent.bridge import ROOT
from agent.deterministic_v2 import EvaluationPolicy
from .current_source import MANIFEST, check_current_source
from .scenarios import run_case
from .u2b_data import DATA, digest, load_split, plan_slots, read_json, sha
from .u2b_score import score_evidence, summarize

LEASE="employee-u2b-first-pair-20261012"
RESOURCES={"ram_mib":768,"disk_mib":128,"java_processes":1,"python_processes_including_launcher":2,
           "command_seconds":180,"active_lease_seconds":300,"downloads_bytes":0,"spend_usd":0,
           "external_calls":0,"http_servers":0}

def fresh_output(value,root=ROOT):
    root=Path(root).resolve();output=Path(value).resolve()
    if not output.is_relative_to(root/"runs") or output==root/"runs" or output.exists():
        raise ValueError("fresh child of repository runs required")
    if any(p.is_symlink() for p in output.parents if p.is_relative_to(root)):
        raise ValueError("output symlink forbidden")
    return output

def validate_grant(grant,plan,source_sha,root=ROOT,now=None):
    now=now or datetime.now(timezone.utc)
    if type(grant) is not dict or grant.get("name")!=LEASE or grant.get("status")!="active" \
            or grant.get("owner")!="main" or grant.get("slug")!="employee-lifecycle-agent" \
            or grant.get("source_manifest_sha256")!=source_sha or grant.get("dataset_manifest_sha256")!=plan["dataset_manifest_sha256"] \
            or grant.get("selected_task_ids")!=plan["intended_task_ids"] or grant.get("split")!=plan["split"] \
            or grant.get("resources")!=RESOURCES or not 1<=len(plan["intended_task_ids"])<=2 or plan["intended_slots"]>4:
        raise ValueError("exact named main lease/source/data/resource grant required")
    if any(type(grant["resources"][k]) is not type(v) for k,v in RESOURCES.items()):
        raise ValueError("typed exact resource limits required")
    expires=datetime.fromisoformat(grant["expires_at_utc"])
    if expires.utcoffset() is None or (expires-now).total_seconds()<240:
        raise ValueError("at least 240 seconds remain for execution and teardown")
    pins=grant.get("class_sha256")
    actual=sorted(p.relative_to(Path(root)/".build/classes").as_posix() for p in (Path(root)/".build/classes").rglob("*.class"))
    if type(pins) is not dict or len(pins)!=14 or actual!=sorted(pins):raise ValueError("exact 14 existing class pins required; no auto-build")
    for relative,expected in pins.items():
        if relative not in actual or sha(Path(root)/".build/classes"/relative)!=expected:raise ValueError("class pin mismatch")
    return True

def atomic_json(path,value):
    path=Path(path);temp=path.with_suffix(path.suffix+".pending")
    temp.write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    temp.replace(path)

def execute(split,ids,out,grant_path):
    # Gate and intent are established before the first native application call.
    check_current_source();bundle=load_split(split);plan=plan_slots(bundle,ids)
    plan["source_manifest_sha256"]=sha(ROOT/MANIFEST)
    validate_grant(read_json(grant_path),plan,plan["source_manifest_sha256"])
    output=fresh_output(out);output.mkdir(parents=True)
    slots=deepcopy(plan["slots"]);start=time.monotonic();deadline=start+RESOURCES["command_seconds"]
    tasks={t["id"]:t for t in bundle["tasks"]}
    atomic_json(output/"intent.json",plan)  # Written once; evolving ledger cannot shrink the original roster.
    def persist():
        atomic_json(output/"ledger.json",{"schema":1,"plan":plan,"plan_sha256":digest(plan),"slots":slots})
        atomic_json(output/"metrics.json",summarize(plan,slots))
    persist()  # Includes every intended paired slot, even if the supervisor kills this process.
    for index,slot in enumerate(slots):
        if time.monotonic()>=deadline:
            for pending in slots[index:]:pending.update(status="UNKNOWN",error_code="COMMAND_DEADLINE_BEFORE_SLOT")
            persist();break
        task=tasks[slot["task_id"]];slot.update(status="RUNNING");persist()
        slot_start=time.monotonic();run_dir=output/f"slot-{index+1:02d}"
        policy=EvaluationPolicy(slot["policy"])
        try:
            # No expected labels/task IDs/families/control schedule reach next_turn.
            run_case(deepcopy(task["seed"]),deepcopy(task["request"]),deepcopy(task["control"]),run_dir,mode=policy)
            slot["status"]="SCORED"
        except TimeoutError:
            slot.update(status="TIMEOUT",error_code="ACTOR_TimeoutError")
        except Exception as error:
            slot.update(status="FAILED",error_code="ACTOR_"+type(error).__name__)
        # run_case's bridges have closed. Score independently even after failure.
        measured=score_evidence(run_dir,bundle["labels"][slot["task_id"]],task["control"])
        slot.update({k:measured[k] for k in ("expected_match","actual_completion","safety_passed","metrics")})
        if measured["metrics"] is None and slot["status"]=="SCORED":slot["status"]="UNKNOWN"
        if slot["error_code"] is None:slot["error_code"]=measured["error_code"]
        slot["elapsed_ms"]=round((time.monotonic()-slot_start)*1000,3)
        # This runner has only two offline implementations and makes no chargeable call.
        slot["actual_cost_usd"]=0;slot["usage"]=None
        atomic_json(output/f"score-{index+1:02d}.json",{**measured,"schema":1,"slot_id":slot["slot_id"],
            "employee_sha256":digest(task["request"]["employee_id"]),"source_manifest_sha256":plan["source_manifest_sha256"],
            "dataset_manifest_sha256":plan["dataset_manifest_sha256"],"policy":slot["policy"],
            "decision_count":len(policy.decisions),"decision_digest":digest(policy.decisions),
            "provider":"offline","model":None,"generation_id":None,"usage":None,"actual_cost_usd":0,
            "estimated_cost_usd":None,"elapsed_ms":slot["elapsed_ms"]})
        persist()
    return 0 if all(s["status"]=="SCORED" and s["expected_match"] is True for s in slots) else 1

def summarize_saved(out):
    ledger=read_json(Path(out)/"ledger.json")
    if digest(ledger["plan"])!=ledger["plan_sha256"]:raise ValueError("saved plan changed")
    if ledger["plan"]!=read_json(Path(out)/"intent.json"):raise ValueError("saved ledger differs from initial intent")
    plan=ledger["plan"];bundle=load_split(plan["split"]);rebuilt=plan_slots(bundle,plan["intended_task_ids"])
    rebuilt["source_manifest_sha256"]=plan["source_manifest_sha256"]
    if rebuilt!=plan:raise ValueError("saved intent differs from current authored data")
    tasks={t["id"]:t for t in bundle["tasks"]}
    for index,slot in enumerate(ledger["slots"]):
        if slot["metrics"] is None:continue
        task=tasks[slot["task_id"]]
        measured=score_evidence(Path(out)/f"slot-{index+1:02d}",bundle["labels"][slot["task_id"]],task["control"])
        if any(slot[k]!=measured[k] for k in ("expected_match","actual_completion","safety_passed","metrics")):
            raise ValueError("saved verdict disagrees with independent histories")
    # This is accounting only. RUNNING/PLANNED remain unknown; no implicit retry or success.
    return summarize(ledger["plan"],ledger["slots"])

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="command",required=True)
    plan_parser=sub.add_parser("plan");plan_parser.add_argument("--split",choices=("development","capability"),required=True)
    run=sub.add_parser("run");run.add_argument("--split",choices=("development","capability"),required=True)
    run.add_argument("--ids",required=True);run.add_argument("--out",required=True);run.add_argument("--main-grant",required=True)
    summary=sub.add_parser("summary");summary.add_argument("--out",required=True)
    args=parser.parse_args(argv)
    if args.command=="plan":print(json.dumps(plan_slots(load_split(args.split)),indent=2));return 0
    if args.command=="summary":print(json.dumps(summarize_saved(args.out),indent=2));return 0
    return execute(args.split,args.ids.split(","),args.out,args.main_grant)

if __name__=="__main__":raise SystemExit(main())
