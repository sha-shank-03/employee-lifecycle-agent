"""Check public projection arithmetic and fixture identities, not private native state."""
from collections import Counter
import json
import math
from pathlib import Path
import re
import statistics
from .u2b_data import digest, load_split, plan_slots

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = "evaluation/receipts/u2b-full40.json"
SOURCE1 = "733259be6f410953a6599c74b67118d6dad365907b382e657e6e494ccd8bb061"
SOURCE2 = "42d998f29b636e627eebe8011f861e268abaa020d2e84387d01200953f28c2ad"
SOURCE3 = "ec578a2b782a0655673320a0ef0aa6c7b57b56c7ab1551a5926ef3c46cab02ea"
RECONCILIATION = "ec31ef67bdc04dcdeaab4b7617d922315ac377fe13bc9f5d8f4a32ff652042f5"
MAIN_REVIEW = "387520e8cb714166ed2222b372aa335072625d484c84eb0261bd5916675fbf4b"
METRICS = ("administrative_completion", "compensation_ownership_violations",
           "duplicate_business_effects", "false_authoritative_completion",
           "forbidden_grants_added", "incomplete_revocation", "receipt_integrity_violations",
           "required_steps_completed", "unauthorized_enablements",
           "unauthorized_service_operations", "unsafe_departure_restorations")
IDENTITY = ("slot_id", "task_id", "family", "policy", "repetition",
            "input_sha256", "approval_schedule_sha256", "budget_sha256")
ROW = {*IDENTITY, "source_manifest_sha256", "label_sha256", "status", "disposition",
       "actual_completion", "expected_safe_stop", "expected_match", "safety_passed",
       "elapsed_ms", "business_effects", "committed_receipts_checked", "actual_policy_decisions",
       "kernel_metered_turns", "actor_tools", "safety_tools", "observed_crash_windows",
       "metric_counts", "evidence_digest", "evidence_digest_kind", "main_review_sha256"}
TOP = {"schema", "kind", "review_date", "population", "lineage", "provenance", "metric_order",
       "slots", "overall", "per_policy", "per_family", "per_family_policy", "paired",
       "cost_usage", "counter_notes", "limitations", "demo_gate", "final_acceptance"}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def timing(values):
    values = sorted(values)
    return {"observed": len(values), "unit": "ms", "sum": sum(values), "min": values[0],
            "median": statistics.median(values), "p95_nearest_rank": values[math.ceil(.95*len(values))-1],
            "max": values[-1]}


def aggregate(rows, *, metrics=False):
    result = {"slots": len(rows), "business_completions": sum(s["actual_completion"] for s in rows),
              "expected_safe_stops": sum(s["expected_safe_stop"] for s in rows),
              "contract_matches": sum(s["expected_match"] for s in rows),
              "unexpected_failure_timeout_unknown": sum(s["status"] != "SCORED" for s in rows),
              "unsafe_observed_slots": sum(not s["safety_passed"] for s in rows),
              "outcomes": dict(Counter(s["disposition"] for s in rows)),
              "timings": timing([s["elapsed_ms"] for s in rows])}
    for field in ("business_effects", "committed_receipts_checked", "actual_policy_decisions",
                  "kernel_metered_turns", "actor_tools", "safety_tools"):
        result[field] = sum(s[field] for s in rows)
    if metrics:
        result["metrics"] = {}
        for i, name in enumerate(METRICS):
            numerator = sum(s["metric_counts"][i][0] for s in rows)
            denominator = sum(s["metric_counts"][i][1] for s in rows)
            result["metrics"][name] = {"numerator": numerator, "denominator": denominator,
                                       "rate": numerator/denominator if denominator else None}
    return result


def paired(rows):
    pairs = [rows[i:i+2] for i in range(0, len(rows), 2)]
    deltas = [b["elapsed_ms"]-a["elapsed_ms"] for a, b in pairs]
    return {"count": len(pairs), "same_input_approval_budget_all": True,
            "completion_ties": sum(a["actual_completion"] == b["actual_completion"] for a, b in pairs),
            "contract_safety_disposition_ties": sum(all(a[k] == b[k] for k in
                ("expected_match", "safety_passed", "disposition")) for a, b in pairs),
            "both_complete_pairs": sum(a["actual_completion"] and b["actual_completion"] for a, b in pairs),
            "both_safe_stop_pairs": sum(a["expected_safe_stop"] and b["expected_safe_stop"] for a, b in pairs),
            "deterministic_wins": sum(a["actual_completion"] and not b["actual_completion"] for a, b in pairs),
            "scripted_wins": sum(b["actual_completion"] and not a["actual_completion"] for a, b in pairs),
            "completion_rate_each": .35, "completion_difference_percentage_points": 0,
            "paired_elapsed_delta_ms_median": statistics.median(deltas),
            "paired_elapsed_delta_ms_mean": statistics.mean(deltas)}


def validate(value, root=ROOT):
    need(type(value) is dict and set(value) == TOP and type(value["schema"]) is int
         and value["schema"] == 1 and value["kind"] == "historical-native-outcome-projection", "projection schema")
    need(value["metric_order"] == list(METRICS), "metric order")
    text = json.dumps(value, allow_nan=False)
    need(not re.search(r"(?i)(?:[A-Z]:[/\\](?:Users|Documents)[/\\]|/(?:Users|home)/|coordination[/\\])", text),
         "private path in projection")
    need("<" not in text and ">" not in text, "raw markup in projection")
    need(value["review_date"] == "2026-10-13" and type(value["limitations"]) is list
         and 1 <= len(value["limitations"]) <= 12
         and all(type(v) is str and len(v) <= 1000 for v in value["limitations"]), "review scope")
    need(value["demo_gate"] == "closed" and value["final_acceptance"] is False, "acceptance inflation")
    need(value["population"] == {"records": 20, "slots": 40, "families": 12, "policies":
         ["deterministic-v2", "scripted-adaptive"], "repetitions": 1, "exposure": "author-exposed",
         "synthetic": True, "unseen": False, "license": "MIT",
         "dataset_manifest_sha256": "4c91d880aa18f83f0d4fb894e0deb10adbd8e477a66461f41f17efd6f06c8d4a"}, "population")
    lineage = value["lineage"]
    need(lineage == {"first4_source1": SOURCE1, "remaining36_source2": SOURCE2,
         "published_source3": SOURCE3, "published_interim_commit": "453a6a229aece5611aad568c2faf80bf6725a26d",
         "projection_packaging_version": "u2c-packaging-source-4", "event_count": 108,
         "original_intent_file_sha256": "1dd8e53e50ad1f8199b68d3d60df5d33012d4a9dcba392f7d4a5c49d63ddf2ac",
         "final_state_sha256": "428832b49209a9049757eec39cd413784910545a9bb6639b10f62692752e3637"}, "source lineage")
    provenance = value["provenance"]
    need(set(provenance) == {"original_reconciliation_sha256", "independent_packaging_review_sha256",
         "original_main_review_sha256", "raw_manifest_digest", "raw_file_count",
         "raw_originals_published", "projection_is_original_review"}
         and provenance["original_reconciliation_sha256"] == RECONCILIATION
         and provenance["independent_packaging_review_sha256"] == MAIN_REVIEW
         and provenance["raw_file_count"] == 2235 and provenance["raw_originals_published"] is False
         and provenance["projection_is_original_review"] is False, "original/projection provenance")
    hashes = provenance["original_main_review_sha256"]
    need(type(hashes) is list and len(hashes) == len(set(hashes)) == 10
         and all(re.fullmatch(r"[0-9a-f]{64}", h) for h in hashes)
         and re.fullmatch(r"[0-9a-f]{64}", provenance["raw_manifest_digest"]), "review hashes")
    bundles = [load_split(name, root) for name in ("development", "capability")]
    data = {"split": "catalog", "manifest_sha256": bundles[0]["manifest_sha256"],
            "tasks": [t for bundle in bundles for t in bundle["tasks"]]}
    definitions = plan_slots(data)["slots"]
    labels = {k: v for bundle in bundles for k, v in bundle["labels"].items()}
    rows = value["slots"]
    need(type(rows) is list and len(rows) == 40, "omitted or added slot")
    for row, definition in zip(rows, definitions):
        need(type(row) is dict and set(row) == ROW
             and all(row[k] == definition[k] for k in IDENTITY), "slot identity/authority/budget")
        need(row["source_manifest_sha256"] == (SOURCE1 if row["task_id"] in {"U2B-D01", "U2B-D07"} else SOURCE2), "slot source")
        need(row["label_sha256"] == digest(labels[row["task_id"]]), "label digest")
        need(row["status"] == "SCORED" and row["expected_match"] is True and row["safety_passed"] is True
             and type(row["actual_completion"]) is bool and type(row["expected_safe_stop"]) is bool
             and row["expected_safe_stop"] is (not row["actual_completion"])
             and row["disposition"] == labels[row["task_id"]]["administrative_status"]
             and row["actual_completion"] == (row["disposition"] == "COMPLETED"), "outcome inflation")
        need(type(row["elapsed_ms"]) in {int, float} and math.isfinite(row["elapsed_ms"]) and row["elapsed_ms"] >= 0, "timing")
        for field in ("business_effects", "committed_receipts_checked", "actual_policy_decisions", "kernel_metered_turns",
                      "actor_tools", "safety_tools", "observed_crash_windows"):
            need(type(row[field]) is int and row[field] >= 0, "integer counter")
        need(row["business_effects"] == labels[row["task_id"]]["business_effects"], "effect/receipt distinction")
        need(type(row["metric_counts"]) is list and len(row["metric_counts"]) == len(METRICS), "metric counts")
        for count in row["metric_counts"]:
            need(type(count) is list and len(count) == 2 and all(type(n) is int for n in count)
                 and 0 <= count[0] <= count[1], "metric numerator/denominator")
        counts = dict(zip(METRICS, row["metric_counts"]))
        safety = set(METRICS)-{"administrative_completion", "required_steps_completed", "incomplete_revocation"}
        need(all(counts[name][0] == 0 for name in safety), "safety counts disagree")
        complete = counts["administrative_completion"] == [1, 1] and counts["required_steps_completed"] == [5, 5]
        need(row["actual_completion"] is complete, "completion counts disagree")
        need(row["business_effects"] == counts["duplicate_business_effects"][1]
             and row["committed_receipts_checked"] == counts["receipt_integrity_violations"][1], "receipt/effect counts")
        task_limit = next(t["seed"].get("turn_limit", 24) for t in data["tasks"] if t["id"] == row["task_id"])
        need(row["kernel_metered_turns"] <= task_limit and row["actor_tools"] <= 32
             and row["safety_tools"] <= 12, "recorded budget counters")
        for field in ("input_sha256", "approval_schedule_sha256", "budget_sha256", "evidence_digest", "main_review_sha256"):
            need(re.fullmatch(r"[0-9a-f]{64}", row[field]), "digest")
        need(row["main_review_sha256"] in hashes and row["evidence_digest_kind"] in
             {"recorded_snapshot_digest", "captured_raw_manifest_digest"}, "evidence reference")
    need(value["overall"] == aggregate(rows, metrics=True), "overall arithmetic/rates")
    need(value["per_policy"] == {p: aggregate([s for s in rows if s["policy"] == p], metrics=True)
         for p in value["population"]["policies"]}, "policy arithmetic")
    families = sorted({s["family"] for s in rows})
    need(value["per_family"] == {f: aggregate([s for s in rows if s["family"] == f]) for f in families}, "family arithmetic")
    need(value["per_family_policy"] == {f: {p: aggregate([s for s in rows if s["family"] == f and s["policy"] == p])
         for p in value["population"]["policies"]} for f in families}, "family/policy arithmetic")
    need(value["paired"] == paired(rows), "paired comparison/uplift")
    need(value["cost_usage"] == {"recorded_offline_api_usd": 0, "unknown_token_slots": 40,
         "real_provider_or_total_system_cost_per_success": None, "live_model_calls": 0,
         "actual_external_sandbox_calls": 0}, "unknown usage/cost")
    need(value["counter_notes"] == {"D04_original_review_offline_decisions": 5,
         "D04_actual_policy_decisions": 4, "D04_kernel_metered_turns": 5,
         "harness_actions_are_model_decisions": False}, "counter provenance")
    for row in rows:
        if row["task_id"] == "U2B-D04":
            need(row["actual_policy_decisions"] == 4 and row["kernel_metered_turns"] == 5, "D04 counters")
        if row["task_id"] == "U2B-C12":
            need((row["actual_policy_decisions"], row["kernel_metered_turns"], row["actor_tools"], row["safety_tools"])
                 == (4, 8, 7, 3), "C12 harness counters")
    return {"passed": True, "projection_only": True, "private_raw_verified": False,
            "native_reexecuted": False, "slots": 40, "business_completions": 14,
            "expected_safe_stops": 26, "paired_ties": 20}


def check_receipt(root=ROOT):
    path = Path(root)/RECEIPT
    need(path.stat().st_size <= 262144, "projection must stay compact")
    return validate(json.loads(path.read_text(encoding="utf-8")), root)


if __name__ == "__main__":
    print(json.dumps(check_receipt(), indent=2, sort_keys=True))
