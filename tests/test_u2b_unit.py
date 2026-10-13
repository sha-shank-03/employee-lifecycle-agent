"""Guarded pure synthetic controls; no U2B business runs or native evidence."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import dev
from agent.bridge import ROOT
from agent.deterministic_v2 import EvaluationPolicy, MODES, ObservationPolicy, TEXT, actor_context, actor_request
from agent.protocol import FinalDraft, ToolCall
from evaluation import u2b
from evaluation.metrics import rate
from evaluation.u2b_data import BUDGET, DATA, check_slots, digest, load_split, plan_slots, sha, validate_task
from evaluation.u2b_score import completion, number, score_evidence, summarize, usage
from evaluation.verifier import plan_digest
from tests import test_audit_unit as audit_fixture

ASOF=datetime(2026,10,12,tzinfo=timezone.utc)

class U2BPure(unittest.TestCase):
    def setUp(self):
        for name in ("subprocess.Popen","socket.socket"):
            guard=patch(name,side_effect=AssertionError("U2B pure test attempted native operation"))
            guard.start();self.addCleanup(guard.stop)
        (ROOT/"work").mkdir(exist_ok=True)
        folder=tempfile.TemporaryDirectory(prefix="u2b-pure-",dir=ROOT/"work")
        self.addCleanup(folder.cleanup);self.temp=Path(folder.name)
        self.bundle=load_split("development");self.plan=plan_slots(self.bundle,["U2B-D01","U2B-D07"])
        self.slots=deepcopy(self.plan["slots"])
        self.request=dict(self.bundle["tasks"][0]["request"])
    def clone_data(self):
        root=self.temp/"data";shutil.copytree(ROOT/"fixtures",root/"fixtures",ignore=shutil.ignore_patterns("heldout"))
        return root
    def json_write(self,path,value):path.write_text(json.dumps(value,sort_keys=True),encoding="utf-8")
    def history(self):
        fixture=audit_fixture.AuditHistoryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        for w in fixture.histories["workflow"]:
            w["approval_approver"]="hr-reviewer";w["event_sequence"]=w["approved.event_sequence"]
        fixture.write();return fixture
    def score(self,fixture,expected=None):return score_evidence(fixture.run,expected or fixture.expected,{},as_of=ASOF)
    def measured_slots(self,result):
        for slot in self.slots:
            slot.update(status="SCORED",**{k:result[k] for k in ("expected_match","actual_completion","safety_passed","metrics")})
        return self.slots
    def observation(self,**changes):
        return [{"tool":"workflow_status","result":{"code":"OK","workflow_id":"wf-X","administrative_status":"RUNNING","eligible_step":"remove_grants","completed_steps":"0","retry_after_ms":"0",**changes}}]

    def test_counts_provenance_and_label_exposure_are_explicit(self):
        cap=load_split("capability")
        self.assertEqual((len(self.bundle["tasks"]),len(cap["tasks"])),(8,12))
        self.assertEqual(len(set(self.bundle["families"]+cap["families"])),12)
        self.assertEqual(self.bundle["manifest"]["unique_records"],20)
        self.assertFalse(cap["manifest"]["unseen"]);self.assertEqual(cap["manifest"]["license"],"MIT")
        self.assertEqual(len(plan_slots(cap)["slots"]),24)
        for task in self.bundle["tasks"]+cap["tasks"]:
            self.assertEqual(set(task["request"]),{"employee_id","intent","text"})
            self.assertNotIn("expected",task);self.assertEqual(task["request"]["text"],TEXT)
    def test_authored_set_cannot_be_relabeled_unseen(self):
        root=self.clone_data();m=json.loads((root/DATA).read_text());m["unseen"]=True;self.json_write(root/DATA,m)
        with self.assertRaises(ValueError):load_split("development",root)
    def test_input_hash_tamper_is_rejected(self):
        root=self.clone_data();p=root/"fixtures/u2b/development-inputs.jsonl";p.write_bytes(p.read_bytes()+b"\n")
        with self.assertRaises(ValueError):load_split("development",root)
    def test_rehashed_duplicate_label_is_rejected(self):
        root=self.clone_data();p=root/"fixtures/u2b/development-labels.jsonl";rows=p.read_text().splitlines();rows[1]=rows[0]
        p.write_text("\n".join(rows)+"\n");m=json.loads((root/DATA).read_text());m["splits"]["development"]["labels"]["sha256"]=sha(p);self.json_write(root/DATA,m)
        with self.assertRaises(ValueError):load_split("development",root)
    def test_dataset_path_escape_fails_before_read(self):
        root=self.clone_data();m=json.loads((root/DATA).read_text());m["splits"]["development"]["inputs"]["path"]="../outside.jsonl";self.json_write(root/DATA,m)
        with self.assertRaises(ValueError):load_split("development",root)
    def test_task_budget_boolean_and_hidden_field_are_rejected(self):
        task=deepcopy(self.bundle["tasks"][0]);label={"id":task["id"],"expected":self.bundle["labels"][task["id"]]}
        task["seed"]["turn_limit"]=True
        with self.assertRaises(ValueError):validate_task(task,label)
        task["seed"]["turn_limit"]=24;task["control"]["expected"]="COMPLETED"
        with self.assertRaises(ValueError):validate_task(task,label)
    def test_selected_ids_must_be_unique_known_and_nonempty(self):
        for ids in ([],["U2B-D01"]*2,["UNKNOWN"]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):plan_slots(self.bundle,ids)
    def test_actor_boundary_rejects_request_label_and_text_cues(self):
        for change in ({"label":"COMPLETE"},{"text":"case U2B-D01 should complete"},{"task_id":"U2B-D01"}):
            with self.subTest(change=change),self.assertRaises(ValueError):actor_request({**self.request,**change})
    def test_actor_boundary_rejects_nested_observation_labels(self):
        obs=self.observation();obs[0]["result"]["nested"]={"labels":["COMPLETE"]}
        for mode in MODES:
            with self.subTest(mode=mode),self.assertRaises(ValueError):EvaluationPolicy(mode).next_turn(self.request,obs)
        with self.assertRaises(ValueError):actor_context(self.request,self.observation(detail="answer for U2B-C01"))
    def test_actor_boundary_rejects_malformed_and_oversized_context(self):
        for obs in ([{"tool":"x","result":[],"family":"x"}],self.observation(detail="x"*131073)):
            with self.assertRaises(ValueError):actor_context(self.request,obs)
    def test_baseline_follows_authoritative_eligible_step(self):
        decision=EvaluationPolicy(MODES[0]).next_turn(self.request,self.observation())
        self.assertEqual(decision,ToolCall("execute_step",{"workflow_id":"wf-X","step_id":"remove_grants"}))
    def test_baseline_does_not_dispatch_on_employee_identity(self):
        policy=ObservationPolicy();obs=self.observation()
        self.assertEqual(policy.next_turn(self.request,obs),policy.next_turn({**self.request,"employee_id":"E-9999"},obs))
    def test_baseline_retry_and_terminal_controls(self):
        policy=EvaluationPolicy(MODES[0])
        self.assertEqual(policy.next_turn(self.request,self.observation(retry_after_ms="10")).name,"workflow_status")
        self.assertEqual(policy.next_turn(self.request,self.observation(retry_after_ms=0)).name,"execute_step")
        self.assertIsInstance(policy.next_turn(self.request,self.observation(administrative_status="AWAITING_APPROVAL")),FinalDraft)
        self.assertIsInstance(policy.next_turn(self.request,self.observation(code="DENIED")),FinalDraft)
    def test_baseline_verifies_observed_completion(self):
        policy=EvaluationPolicy(MODES[0]);obs=self.observation(administrative_status="COMPLETED")
        self.assertEqual(policy.next_turn(self.request,obs).name,"verify_outcome")
        obs[-1]["tool"]="verify_outcome";self.assertIsInstance(policy.next_turn(self.request,obs),FinalDraft)
    def test_both_policies_use_same_context_tools_authority_and_budget(self):
        policies=[EvaluationPolicy(m) for m in MODES]
        decisions=[p.next_turn(self.request,self.observation()) for p in policies]
        self.assertEqual(decisions[0],decisions[1]);self.assertEqual(policies[0].decisions,policies[1].decisions)
        for a,b in zip(self.slots[::2],self.slots[1::2]):
            for k in ("input_sha256","approval_schedule_sha256","budget_sha256"):self.assertEqual(a[k],b[k])
        self.assertEqual(self.plan["budget"],BUDGET)
        tree=ast.parse((ROOT/"agent/deterministic_v2.py").read_text())
        self.assertFalse(any(isinstance(n,ast.ImportFrom) and (n.module or "").startswith("evaluation") for n in ast.walk(tree)))
    def test_intended_slots_precede_execution_and_unknowns_remain(self):
        self.slots[0]["status"]="TIMEOUT";self.slots[1]["status"]="FAILED";self.slots[2]["status"]="UNKNOWN"
        report=summarize(self.plan,self.slots)
        self.assertEqual(report["all_intended"]["intended_slots"],4)
        self.assertEqual(report["all_intended"]["unknown_outcomes"],4)
        self.assertEqual(report["all_intended"]["actual_completion_per_intended_slot"],rate(0,4))
        self.assertEqual(report["paired_actual_completion"]["unknown_pairs"],2)
    def test_omitted_duplicate_and_reordered_slots_are_rejected(self):
        for rows in (self.slots[:-1],self.slots+[self.slots[0]],list(reversed(self.slots))):
            with self.assertRaises(ValueError):check_slots(self.plan,rows)
    def test_plan_cannot_omit_one_paired_policy(self):
        plan=deepcopy(self.plan);plan["slots"].pop();plan["intended_slots"]-=1
        with self.assertRaises(ValueError):check_slots(plan,plan["slots"])
    def test_changed_authority_or_budget_identity_is_rejected(self):
        for key in ("input_sha256","approval_schedule_sha256","budget_sha256"):
            rows=deepcopy(self.slots);rows[0][key]="f"*64
            with self.assertRaises(ValueError):check_slots(self.plan,rows)
    def test_forged_unscored_completion_is_rejected(self):
        self.slots[0].update(status="SCORED",actual_completion=True)
        with self.assertRaises(ValueError):summarize(self.plan,self.slots)
    def test_clean_independent_histories_prove_completion(self):
        result=self.score(self.history());self.assertTrue(result["expected_match"]);self.assertTrue(result["actual_completion"])
        self.assertEqual(result["business_effects"],5);self.assertEqual(result["metrics"]["incomplete_revocation"],rate(0,0))
        self.assertNotIn("E-900",json.dumps(result));self.assertIsNotNone(result["evidence_sha256"])
    def test_wrong_expected_state_preserves_measured_actual_completion(self):
        f=self.history();wrong={**f.expected,"hr_status":"ACTIVE"};result=self.score(f,wrong)
        self.assertFalse(result["expected_match"]);self.assertTrue(result["actual_completion"])
        self.assertEqual(result["metrics"]["required_steps_completed"],rate(5,5))
    def test_actor_draft_and_forged_state_do_not_confer_completion(self):
        f=self.history();(f.run/"draft.json").write_text('{"text":"Everything completed"}')
        f.histories["identity"][-1]["enabled"]="false";f.write();result=self.score(f)
        self.assertFalse(result["actual_completion"]);self.assertGreater(result["metrics"]["false_authoritative_completion"]["numerator"],0)
    def test_stale_approval_receipts_fail_independent_safety(self):
        f=self.history()
        for w in f.histories["workflow"]:w["approval_digest"]="0"*64
        f.write();result=self.score(f)
        self.assertFalse(result["safety_passed"]);self.assertFalse(result["actual_completion"])
        self.assertGreater(result["metrics"]["unauthorized_service_operations"]["numerator"],0)
    def test_expired_forward_effect_receipts_fail_independent_safety(self):
        f=self.history()
        for w in f.histories["workflow"]:w["approval_expires"]="2025-01-01T00:00:00Z"
        f.write();result=self.score(f)
        self.assertFalse(result["safety_passed"]);self.assertFalse(result["actual_completion"])
    def test_forged_effect_payload_is_not_counted_as_safe_completion(self):
        f=self.history()
        for row in f.histories["identity"][1:]:
            row["ledger.1.prepare_account"]="wf-E900-1/1/prepare_account:"+"0"*64
            row["receipt.prepare_account"]=row["ledger.1.prepare_account"]
        f.write();result=self.score(f)
        self.assertFalse(result["expected_match"]);self.assertFalse(result["actual_completion"])
    def test_duplicate_effects_survive_failed_expectation(self):
        f=self.history();f.histories["identity"][-1].update({"effect.1.prepare_account":"2","effects.prepare_account":"2"});f.write()
        result=self.score(f);self.assertFalse(result["expected_match"])
        self.assertEqual(result["metrics"]["duplicate_business_effects"]["numerator"],1)
        self.assertEqual(result["business_effects"],6)
    def test_missing_evidence_keeps_unknown_completion_and_redacts_error(self):
        result=score_evidence(self.temp/"private-employee",self.bundle["labels"]["U2B-D01"],{},as_of=ASOF)
        self.assertIsNone(result["actual_completion"]);self.assertIsNone(result["metrics"])
        self.assertNotIn(str(self.temp),json.dumps(result));self.assertEqual(result["error_code"],"MEASURE_ValueError")
    def test_expected_compensation_is_distinct_from_actual_completion(self):
        result=self.score(self.history());result["metrics"]["administrative_completion"]=rate(0,1)
        result["actual_completion"]=False;result["expected_match"]=True
        report=summarize(self.plan,self.measured_slots(result))
        self.assertEqual(report["all_intended"]["expected_safe_stops"],4)
        self.assertEqual(report["all_intended"]["actual_completion_per_intended_slot"],rate(0,4))
        self.assertEqual(report["paired_actual_completion"]["both_incomplete"],2)
    def test_due_approved_departure_denominator_is_not_all_slots(self):
        f=self.history()
        for w in f.histories["workflow"]:
            w["intent"]="offboard";w["digest"]=w["approval_digest"]=plan_digest(w)
        f.write();result=self.score(f)
        self.assertEqual(result["metrics"]["incomplete_revocation"],rate(1,1))
        report=summarize(self.plan,self.measured_slots(result))
        self.assertEqual(report["all_intended"]["metrics"]["incomplete_revocation"],rate(4,4))
    def test_forged_completion_disagreeing_with_metrics_is_rejected(self):
        result=self.score(self.history());self.measured_slots(result);self.slots[0]["metrics"]["administrative_completion"]=rate(0,1)
        with self.assertRaises(ValueError):summarize(self.plan,self.slots)
    def test_unknown_usage_cost_and_zero_success_remain_null(self):
        report=summarize(self.plan,self.slots)["all_intended"]
        self.assertIsNone(report["actual_cost_usd"]);self.assertIsNone(report["cost_per_actual_completion_usd"])
        self.assertEqual(report["unknown_cost_slots"],4);self.assertEqual(report["unknown_usage_slots"],4)
        self.slots[0]["actual_cost_usd"]=0;report=summarize(self.plan,self.slots)["all_intended"]
        self.assertEqual(report["known_cost_subtotal_usd"],0);self.assertEqual(report["unknown_cost_slots"],3)
    def test_nonfinite_boolean_and_inconsistent_usage_are_rejected(self):
        for value in (True,-1,float("inf"),float("nan"),"0"):
            with self.subTest(value=value),self.assertRaises(ValueError):number(value)
        for value in ({"input_tokens":True,"output_tokens":0,"total_tokens":1},{"input_tokens":2,"output_tokens":3,"total_tokens":4},{}):
            with self.assertRaises(ValueError):usage(value)
        self.assertEqual(usage({"input_tokens":2,"output_tokens":3,"total_tokens":5})["total_tokens"],5)
    def test_grant_requires_current_hashes_exact_resources_and_time(self):
        classes=self.temp/".build/classes/lifecycle";classes.mkdir(parents=True)
        for i in range(14):(classes/f"Fixture{i}.class").write_bytes(b"pure hash fixture, not Java bytecode")
        pins={p.relative_to(self.temp/".build/classes").as_posix():sha(p) for p in classes.iterdir()}
        grant={"name":u2b.LEASE,"status":"active","owner":"main","slug":"employee-lifecycle-agent",
               "source_manifest_sha256":"a"*64,"dataset_manifest_sha256":self.plan["dataset_manifest_sha256"],
               "selected_task_ids":self.plan["intended_task_ids"],"split":"development","resources":u2b.RESOURCES,
               "expires_at_utc":"2026-10-12T00:10:00+00:00","class_sha256":pins}
        now=datetime(2026,10,12,tzinfo=timezone.utc)
        self.assertTrue(u2b.validate_grant(grant,self.plan,"a"*64,self.temp,now))
        for changes in ({"source_manifest_sha256":"b"*64},{"resources":{}},{"expires_at_utc":"2026-10-12T00:01:00+00:00"},{"class_sha256":{}}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):u2b.validate_grant({**grant,**changes},self.plan,"a"*64,self.temp,now)
    def test_fake_runner_persists_all_slots_before_any_call_and_retains_failures(self):
        out=self.temp/"fake-runner";seen=[]
        def fail(*args,**kwargs):
            ledger=json.loads((out/"ledger.json").read_text());seen.append(ledger)
            self.assertEqual(len(ledger["slots"]),4);self.assertEqual(ledger["slots"][len(seen)-1]["status"],"RUNNING")
            raise TimeoutError("private raw error should not escape")
        with patch.object(u2b,"check_current_source"),patch.object(u2b,"validate_grant"),patch.object(u2b,"read_json",return_value={}), \
                patch.object(u2b,"fresh_output",return_value=out),patch.object(u2b,"run_case",side_effect=fail):
            self.assertEqual(u2b.execute("development",["U2B-D01","U2B-D07"],out,"unused-grant"),1)
        ledger=json.loads((out/"ledger.json").read_text());self.assertEqual([s["status"] for s in ledger["slots"]],["TIMEOUT"]*4)
        self.assertEqual(u2b.summarize_saved(out)["all_intended"]["intended_slots"],4)
        self.assertNotIn("private raw error",(out/"ledger.json").read_text())
    def test_saved_plan_tamper_and_populated_output_are_rejected(self):
        out=self.temp/"saved";out.mkdir();u2b.atomic_json(out/"ledger.json",{"plan":self.plan,"plan_sha256":"0"*64,"slots":self.slots})
        with self.assertRaises(ValueError):u2b.summarize_saved(out)
        with self.assertRaises(ValueError):u2b.fresh_output(ROOT/"runs",ROOT)
        with self.assertRaises(ValueError):u2b.fresh_output(out,self.temp)
        self.assertIn("test_u2b_unit.py",dev.test_patterns("unit"))
    def test_saved_forged_metric_counts_require_independent_raw_histories(self):
        result=self.score(self.history());self.measured_slots(result)
        plan=deepcopy(self.plan);plan["source_manifest_sha256"]=sha(ROOT/"evaluation/upgrade/current-manifest.json")
        out=self.temp/"forged";out.mkdir()
        u2b.atomic_json(out/"intent.json",plan)
        u2b.atomic_json(out/"ledger.json",{"plan":plan,"plan_sha256":digest(plan),"slots":self.slots})
        with self.assertRaisesRegex(ValueError,"independent histories"):u2b.summarize_saved(out)

if __name__=="__main__":unittest.main()
