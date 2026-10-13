"""Self-contained synthetic catalog controls; no saved native run required."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import dev
from agent.bridge import ROOT
from evaluation import u2b_catalog as c
from evaluation import u2b_catalog_controls as controls
from evaluation.u2b_data import digest, sha

class CatalogPure(unittest.TestCase):
    def setUp(self):
        for name in ("subprocess.Popen","socket.socket"):
            guard=patch(name,side_effect=AssertionError("catalog pure attempted native operation"))
            guard.start();self.addCleanup(guard.stop)
        (ROOT/"work").mkdir(exist_ok=True)
        folder=tempfile.TemporaryDirectory(prefix="catalog-pure-",dir=ROOT/"work")
        self.addCleanup(folder.cleanup);self.root=Path(folder.name);self.folder=self.root/c.CATALOG_PATH
        self.intent=controls.control_intent(ROOT);self.data=c.all_data(ROOT)
        immutable=deepcopy(self.intent);data=deepcopy(self.data)
        for name,func in (("build_intent",lambda *a,**k:deepcopy(immutable)),("all_data",lambda *a,**k:deepcopy(data)),("check_current_source",lambda *a,**k:None)):
            mock=patch.object(c,name,side_effect=func);mock.start();self.addCleanup(mock.stop)
        c.initialize(self.folder,self.root);self.catalog=c.Catalog(self.folder,self.root)
        self.rows=self.catalog.state()["slots"];self.row=self.rows[0]
        original=self.intent["first"]["slots"][2]
        self.mock_safe={"status":"SCORED","verdict":{**{k:deepcopy(original[k]) for k in c.VERDICT},"error_code":None}}
        self.grant_path=self.root/"grant.json"
        self.grant_path.write_text(json.dumps({"name":"employee-u2b-catalog-pure-control"}),encoding="utf-8")
    def write(self,p,value):p.write_text(json.dumps(value,sort_keys=True),encoding="utf-8")
    def capture(self,row=None,result="RETURNED"):
        row=row or self.row;return {"actor_result":result,"error_code":None if result=="RETURNED" else "ACTOR_TimeoutError",
            "elapsed_ms":1.0,"raw_files":c.file_pins(self.catalog.run_folder(row)),"decision_count":0,"decision_sha256":digest([])}
    def start(self,row=None):self.catalog.append("STARTED",row or self.row,{"lease_name":"pure-control"},"a"*64)
    def fake_actor(self,seed,request,control,path,mode):
        # Only a fixture byte for bookkeeping; no Java/provider loop/business effect.
        self.assertEqual(self.catalog.state()["slots"][0]["status"],"STARTED" if path==self.catalog.run_folder(self.row) else "SCORED")
        self.assertEqual(set(request),{"employee_id","intent","text"});self.assertNotIn("expected",control)
        path.mkdir(parents=True);(path/"receipt.txt").write_text("authored pure fixture; not domain evidence",encoding="utf-8")
        return {"draft":"not authoritative"}
    def fake_grant(self,grant,catalog,ids,root):return catalog.selected(ids)
    def run_mock(self,actor=None,classified=None,ids=None):
        with patch.object(c,"validate_slice_grant",side_effect=self.fake_grant), \
                patch.object(c,"run_case",side_effect=actor or self.fake_actor) as mocked, \
                patch.object(c.Catalog,"classify",return_value=deepcopy(classified or self.mock_safe)):
            code=c.run_slice(self.folder,ids or ["U2B-D02"],self.grant_path,self.root)
        return code,mocked.call_count

    def test_full36_intent_preserves_first4_and_all20_identities(self):
        saved=json.loads((self.folder/"intent.json").read_text());self.assertEqual(len(saved["remainder_plan"]["slots"]),36)
        self.assertEqual(saved["remainder_plan"]["intended_task_ids"],[t["id"] for t in self.data["tasks"] if t["id"] not in c.FIRST_IDS])
        self.assertEqual(saved["first"]["slots"],self.intent["first"]["slots"])
        self.assertEqual(len(saved["full_plan"]["slots"]),40);self.assertEqual(len(saved["label_sha256"]),20)
    def test_initial_report_counts2_complete2_safe_and36_unexecuted(self):
        report=self.catalog.report();total=report["entire_catalog"]["all_intended"]
        self.assertEqual(total["actual_completion_per_intended_slot"]["numerator"],2)
        self.assertEqual(total["actual_completion_per_intended_slot"]["denominator"],40)
        self.assertEqual(total["expected_safe_stops"],2);self.assertEqual(total["unknown_outcomes"],36)
        self.assertEqual(report["remainder_status_counts"],{"UNEXECUTED":36})
        self.assertEqual(len(report["unexecuted_slot_ids"]),36)
        self.assertEqual(report["first_original_report"]["source_manifest_sha256"],c.FIRST_SOURCE)
        self.assertNotIn("E-6101",json.dumps(report));self.assertNotIn(str(ROOT),json.dumps(report))
    def test_unknown_remainder_cost_usage_stays_null(self):
        total=self.catalog.report()["entire_catalog"]["all_intended"]
        self.assertEqual(total["known_cost_subtotal_usd"],0);self.assertEqual(total["unknown_cost_slots"],36)
        self.assertIsNone(total["actual_cost_usd"]);self.assertIsNone(total["cost_per_actual_completion_usd"])
        self.assertEqual(total["unknown_usage_slots"],40)
    def test_preview_is_reproducible_read_only_and_cannot_hide_existing_state(self):
        other=self.root/"preview-root"
        with patch.object(c,"run_case") as actor:
            preview=c.preview_report(other)
        self.assertEqual(actor.call_count,0);self.assertFalse(other.exists())
        self.assertEqual(preview["remainder_status_counts"],{"UNEXECUTED":36})
        self.assertEqual(preview["entire_catalog"],self.catalog.report()["entire_catalog"])
        with self.assertRaises(ValueError):c.preview_report(self.root)
    def test_missing_slot_and_replacement_population_rejected(self):
        intent=json.loads((self.folder/"intent.json").read_text());intent["remainder_plan"]["slots"].pop();intent["remainder_plan"]["intended_slots"]-=1
        self.write(self.folder/"intent.json",intent)
        with self.assertRaises(ValueError):c.Catalog(self.folder,self.root)
        with self.assertRaises(ValueError):c.initialize(self.folder,self.root)
    def test_alternate_catalog_location_is_rejected(self):
        with self.assertRaises(ValueError):c.catalog_path(self.root/"runs/replacement-catalog",self.root)
    def test_selection_allows_only_two_canonical_untouched_pairs(self):
        rows,_=self.catalog.selected(["U2B-D02","U2B-D03"]);self.assertEqual(len(rows),4)
        for ids in ([],["U2B-D01"],["U2B-D02"]*2,["U2B-D03","U2B-D02"],["U2B-D02","U2B-D03","U2B-D04"]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):self.catalog.selected(ids)
    def test_started_slot_cannot_replay_or_start_parallel_slot(self):
        self.start()
        with self.assertRaises(ValueError):self.start()
        with self.assertRaises(ValueError):self.start(self.rows[1])
        with self.assertRaises(ValueError):self.catalog.selected(["U2B-D02"])
        self.assertEqual(self.catalog.report()["unknown_slot_ids"],[self.row["slot_id"]])
    def test_classification_before_capture_and_changed_authority_rejected(self):
        with self.assertRaises(ValueError):self.catalog.append("CLASSIFIED",self.row,self.mock_safe,"a"*64)
        self.start();changed={**self.row,"budget_sha256":"f"*64}
        with self.assertRaises(ValueError):self.catalog.append("CAPTURED",changed,self.capture(),"a"*64)
    def test_serial_capture_is_durable_before_mock_classification(self):
        def classify(row,capture):
            events=sorted((self.folder/"events").glob("*.json"))
            self.assertEqual(json.loads(events[-1].read_text())["kind"],"CAPTURED")
            self.assertEqual(json.loads(events[-1].read_text())["body"],capture)
            return deepcopy(self.mock_safe)
        with patch.object(c,"validate_slice_grant",side_effect=self.fake_grant),patch.object(c,"run_case",side_effect=self.fake_actor) as actor, \
                patch.object(c.Catalog,"classify",side_effect=classify):
            self.assertEqual(c.run_slice(self.folder,["U2B-D02"],self.grant_path,self.root),0)
        self.assertEqual(actor.call_count,2)
        kinds=[json.loads(p.read_text())["kind"] for p in sorted((self.folder/"events").glob("*.json"))]
        self.assertEqual(kinds,["STARTED","CAPTURED","CLASSIFIED"]*2)
    def test_completed_mock_pair_cannot_replay(self):
        self.assertEqual(self.run_mock(),(0,2))
        with patch.object(c.Catalog,"classify",return_value=self.mock_safe),self.assertRaises(ValueError):self.catalog.selected(["U2B-D02"])
    def test_unexpected_negative_outcome_stops_before_next_slot(self):
        negative=deepcopy(self.mock_safe);negative["status"]="FAILED";negative["verdict"]["expected_match"]=False
        self.assertEqual(self.run_mock(classified=negative,ids=["U2B-D02","U2B-D03"]),(1,1))
        state=self.catalog.state();self.assertTrue(state["halted"]);self.assertEqual(state["slots"][0]["status"],"FAILED")
        self.assertEqual(sum(s["status"]=="UNEXECUTED" for s in state["slots"]),35)
        with patch.object(c.Catalog,"classify",return_value=negative),self.assertRaises(ValueError):self.catalog.selected(["U2B-D03"])
    def test_timeout_capture_is_terminal_and_never_replayed(self):
        def timeout(*a,**k):raise TimeoutError("private exception message")
        with patch.object(c,"validate_slice_grant",side_effect=self.fake_grant),patch.object(c,"run_case",side_effect=timeout) as actor:
            self.assertEqual(c.run_slice(self.folder,["U2B-D02","U2B-D03"],self.grant_path,self.root),1)
        self.assertEqual(actor.call_count,1);self.assertEqual(self.catalog.state()["slots"][0]["status"],"TIMEOUT")
        self.assertNotIn("private exception message",(self.folder/"events/000002.json").read_text())
        with self.assertRaises(ValueError):self.catalog.selected(["U2B-D03"])
    def test_forged_actor_success_without_histories_is_unknown(self):
        with patch.object(c,"validate_slice_grant",side_effect=self.fake_grant),patch.object(c,"run_case",return_value={"success":True,"draft":"all done"}) as actor:
            self.assertEqual(c.run_slice(self.folder,["U2B-D02"],self.grant_path,self.root),1)
        self.assertEqual(actor.call_count,1);row=self.catalog.state()["slots"][0]
        self.assertEqual(row["status"],"UNKNOWN");self.assertIsNone(row["verdict"]["actual_completion"])
        self.assertEqual(self.catalog.report()["entire_catalog"]["all_intended"]["actual_completion_per_intended_slot"]["numerator"],2)
    def test_negative_actor_result_cannot_be_promoted_to_scored(self):
        self.start();capture=self.capture(result="FAILED");self.catalog.append("CAPTURED",self.row,capture,"a"*64)
        with self.assertRaises(ValueError):self.catalog.append("CLASSIFIED",self.row,self.mock_safe,"a"*64)
        classified=self.catalog.classify(self.row,capture);self.assertEqual(classified["status"],"FAILED")
    def test_start_write_failure_prevents_any_actor_entry(self):
        with patch.object(c,"validate_slice_grant",side_effect=self.fake_grant),patch.object(c,"run_case") as actor, \
                patch.object(c.os,"fsync",side_effect=OSError("authored write failure")),self.assertRaises(OSError):
            c.run_slice(self.folder,["U2B-D02"],self.grant_path,self.root)
        self.assertEqual(actor.call_count,0);state=self.catalog.state();self.assertEqual(len(state["pending"]),1)
        self.assertTrue(self.catalog.report()["blocked_incomplete_write_or_capture"])
        with self.assertRaises(ValueError):self.catalog.selected(["U2B-D02"])
    def test_capture_write_failure_retains_started_unknown_and_no_retry(self):
        original=c.publish
        def fail(path,value):
            if value.get("kind")=="CAPTURED":
                path.with_suffix(".pending").write_text(json.dumps(value));raise OSError("capture write control")
            return original(path,value)
        with patch.object(c,"validate_slice_grant",side_effect=self.fake_grant),patch.object(c,"run_case",side_effect=self.fake_actor) as actor, \
                patch.object(c,"publish",side_effect=fail),self.assertRaises(OSError):
            c.run_slice(self.folder,["U2B-D02"],self.grant_path,self.root)
        self.assertEqual(actor.call_count,1);report=self.catalog.report()
        self.assertEqual(report["unknown_slot_ids"],[self.row["slot_id"]]);self.assertEqual(len(report["unexecuted_slot_ids"]),35)
        with self.assertRaises(ValueError):self.catalog.selected(["U2B-D03"])
    def test_classification_write_failure_retains_durable_raw_capture(self):
        original=c.publish
        def fail(path,value):
            if value.get("kind")=="CLASSIFIED":raise OSError("classification write control")
            return original(path,value)
        with patch.object(c,"validate_slice_grant",side_effect=self.fake_grant),patch.object(c,"run_case",side_effect=self.fake_actor) as actor, \
                patch.object(c.Catalog,"classify",return_value=self.mock_safe),patch.object(c,"publish",side_effect=fail),self.assertRaises(OSError):
            c.run_slice(self.folder,["U2B-D02"],self.grant_path,self.root)
        self.assertEqual(actor.call_count,1);row=self.catalog.state()["slots"][0];self.assertEqual(row["status"],"CAPTURED")
        self.assertIsNotNone(row["capture"]);self.assertTrue(self.catalog.report()["blocked_incomplete_write_or_capture"])
    def test_intent_write_failure_cannot_replace_existing_partial_catalog(self):
        other=self.root/"other";path=other/c.CATALOG_PATH
        with patch.object(c.os,"fsync",side_effect=OSError("intent write control")),self.assertRaises(OSError):c.initialize(path,other)
        self.assertFalse((path/"intent.json").exists());self.assertTrue((path/"intent.pending").exists())
        with self.assertRaises(ValueError):c.initialize(path,other)
    def test_missing_event_and_orphan_output_are_fail_closed(self):
        self.start();self.catalog.append("CAPTURED",self.row,self.capture(),"a"*64)
        (self.folder/"events/000001.json").unlink()
        with self.assertRaises(ValueError):self.catalog.state()
        (self.folder/"events/000002.json").unlink();self.catalog.run_folder(self.row).mkdir(parents=True)
        with self.assertRaises(ValueError):self.catalog.report()
    def test_raw_evidence_forgery_blocks_report_and_future_entry(self):
        self.assertEqual(self.run_mock(),(0,2))
        (self.catalog.run_folder(self.row)/"receipt.txt").write_text("forged bytes")
        with self.assertRaises(ValueError):self.catalog.report()
        with self.assertRaises(ValueError):self.catalog.selected(["U2B-D03"])
    def test_saved_verdict_forgery_cannot_override_raw_classification(self):
        self.start();self.catalog.append("CAPTURED",self.row,self.capture(),"a"*64)
        with patch.object(c.Catalog,"classify",return_value=self.mock_safe):self.catalog.append("CLASSIFIED",self.row,self.mock_safe,"a"*64)
        p=self.folder/"events/000003.json";event=json.loads(p.read_text());event["body"]["verdict"]["actual_completion"]=True;self.write(p,event)
        with patch.object(c.Catalog,"classify",return_value=self.mock_safe),self.assertRaises(ValueError):self.catalog.report()
    def test_classified_event_after_failure_cannot_start_more_work(self):
        self.start();capture=self.capture(result="TIMEOUT");self.catalog.append("CAPTURED",self.row,capture,"a"*64)
        self.catalog.append("CLASSIFIED",self.row,self.catalog.classify(self.row,capture),"a"*64)
        with self.assertRaises(ValueError):self.start(self.rows[2])
    def test_stale_or_unbound_grant_rejected_with_inherited_caps(self):
        classes=self.root/".build/classes/lifecycle";classes.mkdir(parents=True)
        for i in range(14):(classes/f"Fixture{i}.class").write_bytes(b"pure file-pin fixture; no executable bytecode")
        pins={p.relative_to(self.root/".build/classes").as_posix():sha(p) for p in classes.iterdir()}
        ids=["U2B-D02","U2B-D03"];rows,state=self.catalog.selected(ids)
        grant={"name":"employee-u2b-catalog-d02-d03-20261013","status":"active","owner":"main","slug":"employee-lifecycle-agent",
            "source_manifest_sha256":self.intent["source_manifest_sha256"],"dataset_manifest_sha256":self.intent["dataset_manifest_sha256"],
            "catalog_intent_sha256":digest(self.intent),"catalog_state_sha256":state["state_sha256"],"selected_task_ids":ids,
            "selected_slot_sha256":digest([{k:s[k] for k in c.IDENTITY} for s in rows]),"resources":c.RESOURCES,
            "expires_at_utc":"2026-10-13T00:10:00+00:00","class_sha256":pins}
        now=datetime(2026,10,13,tzinfo=timezone.utc)
        self.assertEqual(len(c.validate_slice_grant(grant,self.catalog,ids,self.root,now)[0]),4)
        for change in ({"catalog_state_sha256":"0"*64},{"catalog_intent_sha256":"0"*64},{"selected_slot_sha256":"0"*64},
                       {"source_manifest_sha256":"0"*64},{"resources":{}},{"class_sha256":{}},{"expires_at_utc":"2026-10-13T00:01:00+00:00"}):
            with self.subTest(change=change),self.assertRaises(ValueError):c.validate_slice_grant({**grant,**change},self.catalog,ids,self.root,now)
    def test_exclusive_crash_lock_blocks_run_without_actor(self):
        (self.folder/"active.lock").write_text("preserved crash lock")
        with patch.object(c,"run_case") as actor,self.assertRaises(FileExistsError):c.run_slice(self.folder,["U2B-D02"],self.grant_path,self.root)
        self.assertEqual(actor.call_count,0);self.assertTrue(self.catalog.report()["active_lock_present"])
    def test_nonfinite_capture_rejected_and_suite_registered(self):
        capture=self.capture();capture["elapsed_ms"]=float("nan")
        with self.assertRaises(ValueError):c.validate_capture(capture)
        capture["elapsed_ms"]=True
        with self.assertRaises(ValueError):c.validate_capture(capture)
        self.assertEqual(dev.test_patterns("u2b-catalog-unit"),["test_u2b_catalog_unit.py"])
        self.assertIn("test_u2b_catalog_unit.py",dev.test_patterns("all"))

class StandaloneControls(unittest.TestCase):
    def setUp(self):
        for name in ("subprocess.Popen", "socket.socket"):
            guard=patch(name,side_effect=AssertionError("standalone control attempted native operation"))
            guard.start();self.addCleanup(guard.stop)
        temporary=tempfile.TemporaryDirectory(prefix="standalone-catalog-controls-")
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        shutil.copytree(ROOT/"fixtures",self.root/"fixtures")
        manifest=self.root/c.MANIFEST;manifest.parent.mkdir(parents=True)
        shutil.copyfile(ROOT/c.MANIFEST,manifest)

    def test_preview_without_native_run_or_review_uses_only_constructed_controls(self):
        with patch.object(c,"first_binding",side_effect=AssertionError("private evidence accessed")), \
                patch.object(c,"run_case",side_effect=AssertionError("actor entry")):
            result=controls.control_preview(self.root)
        self.assertEqual(result["evidence_kind"],controls.KIND)
        self.assertFalse(result["native_evidence_verified"])
        self.assertIsNone(result["first_main_review_sha256"])
        self.assertFalse((self.root/"runs").exists())
        self.assertFalse((self.root/".build").exists())
        self.assertEqual(result["remainder_status_counts"],{"UNEXECUTED":36})

    def test_real_first_binding_still_rejects_missing_and_partial_native_evidence(self):
        review=self.root/c.REVIEW;review.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/c.REVIEW,review)
        with self.assertRaisesRegex(ValueError,"first native evidence changed"):
            c.first_binding(self.root)
        partial=self.root/"runs/u2b-main-first-20261012";partial.mkdir(parents=True)
        (partial/"receipt.txt").write_text("synthetic bytes cannot replace native evidence",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"first native evidence changed"):
            c.first_binding(self.root)

    def test_control_data_hash_tamper_is_rejected(self):
        data=self.root/"fixtures/u2b/capability-inputs.jsonl"
        data.write_bytes(data.read_bytes()+b"\n")
        with self.assertRaises(ValueError):controls.control_intent(self.root)

    def test_control_cli_is_explicit_and_never_calls_native_binding_or_actor(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output), \
                patch.object(c,"first_binding",side_effect=AssertionError("native binding")), \
                patch.object(c,"run_case",side_effect=AssertionError("actor entry")):
            self.assertEqual(controls.main(),0)
        result=json.loads(output.getvalue())
        self.assertTrue(result["control_fixture_only"])
        self.assertFalse(result["native_evidence_verified"])

if __name__=="__main__":unittest.main()
