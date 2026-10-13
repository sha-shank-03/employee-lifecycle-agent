"""Self-contained synthetic accounting controls, never native execution evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from agent.bridge import ROOT
from . import u2b_catalog as catalog
from .metrics import rate, SAFETY_GATES
from .u2b_data import digest, plan_slots, sha
from .u2b_score import METRICS, summarize

KIND = "synthetic-unit-control"


def control_intent(root=ROOT):
    """Model two completions/two safe stops to exercise accounting denominators.

    Counts are deliberately constructed fixtures, not a regrade, public receipt,
    substitute for missing private snapshots, or claim of observed behavior.
    Production build_intent/first_binding are not invoked or changed.
    """
    root = Path(root)
    data = catalog.all_data(root)
    full = plan_slots(data)
    first_plan = plan_slots(data, list(catalog.FIRST_IDS))
    first_plan["source_manifest_sha256"] = catalog.FIRST_SOURCE
    slots = deepcopy(first_plan["slots"])
    for slot in slots:
        complete = slot["task_id"] == "U2B-D01"
        metrics = {name: rate(0, 1) for name in METRICS}
        metrics["required_steps_completed"] = rate(5 if complete else 2, 5)
        metrics["administrative_completion"] = rate(int(complete), 1)
        assert all(metrics[name]["numerator"] == 0 for name in SAFETY_GATES)
        slot.update(status="SCORED", expected_match=True, actual_completion=complete,
                    safety_passed=True, metrics=metrics, elapsed_ms=1.0, actual_cost_usd=0)
    first_report = summarize(first_plan, slots)
    first_report.update(evidence_kind=KIND, native_evidence_verified=False)
    first = {"evidence_kind": KIND, "native_evidence_verified": False,
             "source_manifest_sha256": catalog.FIRST_SOURCE,
             "dataset_manifest_sha256": data["manifest_sha256"],
             "original_main_review_sha256": None, "review_path": None,
             "review_sha256": None, "raw_files_sha256": None,
             "intent_sha256": None, "ledger_sha256": None,
             "selected_task_ids": list(catalog.FIRST_IDS), "slots": slots,
             "original_report": first_report}
    remaining = [t["id"] for t in data["tasks"] if t["id"] not in catalog.FIRST_IDS]
    return {"schema": 1, "version": catalog.VERSION, "evidence_kind": KIND,
            "native_evidence_verified": False,
            "source_manifest_sha256": sha(root/catalog.MANIFEST),
            "catalog_path": catalog.CATALOG_PATH,
            "dataset_manifest_sha256": data["manifest_sha256"], "first": first,
            "full_plan": full, "remainder_plan": plan_slots(data, remaining),
            "label_sha256": {k: digest(v) for k, v in data["labels"].items()},
            "unique_records": 20, "scenario_families": 12,
            "shared_development_capability_families": 8, "exposure": "author-exposed",
            "unseen": False, "synthetic": True, "live_model_quality_evaluated": False}


def control_preview(root=ROOT):
    intent = control_intent(root)
    # An empty disposable fixture location cannot conceal the real runtime catalog.
    with tempfile.TemporaryDirectory(prefix="catalog-control-preview-") as temporary:
        fixture = object.__new__(catalog.Catalog)
        fixture.root = Path(root)
        fixture.folder = Path(temporary)/catalog.CATALOG_PATH
        fixture.intent = intent
        fixture.plan = intent["remainder_plan"]
        result = fixture.report()
    result.update(evidence_kind=KIND, native_evidence_verified=False,
                  control_fixture_only=True,
                  limits="Constructed accounting fixtures only: two modeled completions and two modeled safe stops. No native outcomes verified, no actor entry, no actual catalog state read or changed. Historical source identity is a reference, not execution provenance.")
    return result


def main():
    print(json.dumps(control_preview(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
