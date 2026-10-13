"""Public projection controls; no private evidence, actor or scorer invocation."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import dev
from evaluation import u2b_receipt as receipt


class ReceiptPure(unittest.TestCase):
    def setUp(self):
        for name in ("subprocess.Popen", "socket.socket"):
            guard = patch(name, side_effect=AssertionError("receipt control attempted native operation"))
            guard.start(); self.addCleanup(guard.stop)
        self.value = json.loads((receipt.ROOT/receipt.RECEIPT).read_text(encoding="utf-8"))

    def reject(self, value):
        with self.assertRaises(ValueError):
            receipt.validate(value)

    def test_valid_projection_checks_arithmetic_without_claiming_raw_verification(self):
        result = receipt.check_receipt()
        self.assertEqual((result["slots"], result["business_completions"], result["expected_safe_stops"]), (40, 14, 26))
        self.assertTrue(result["projection_only"])
        self.assertFalse(result["private_raw_verified"])
        self.assertFalse(result["native_reexecuted"])

    def test_omitted_duplicate_or_reordered_original_slot_rejected(self):
        for kind in ("omit", "duplicate", "reorder"):
            value = deepcopy(self.value)
            if kind == "omit": value["slots"].pop()
            elif kind == "duplicate": value["slots"][1] = deepcopy(value["slots"][0])
            else: value["slots"][0], value["slots"][1] = value["slots"][1], value["slots"][0]
            with self.subTest(kind=kind): self.reject(value)

    def test_safe_stop_cannot_be_inflated_to_business_completion(self):
        row = next(s for s in self.value["slots"] if not s["actual_completion"])
        row.update(actual_completion=True, expected_safe_stop=False, disposition="COMPLETED")
        self.reject(self.value)

    def test_wrong_historical_execution_source_is_rejected(self):
        self.value["slots"][0]["source_manifest_sha256"] = receipt.SOURCE3
        self.reject(self.value)

    def test_policy_budget_or_approval_digest_cannot_change(self):
        for field in ("budget_sha256", "approval_schedule_sha256", "input_sha256", "label_sha256"):
            value = deepcopy(self.value); value["slots"][1][field] = "0"*64
            with self.subTest(field=field): self.reject(value)

    def test_existing_account_noop_receipt_cannot_be_an_extra_effect(self):
        row = next(s for s in self.value["slots"] if s["task_id"] == "U2B-C06")
        self.assertEqual((row["business_effects"], row["committed_receipts_checked"]), (4, 5))
        row["business_effects"] = 5
        self.reject(self.value)

    def test_safety_count_and_completion_metrics_must_agree_with_flags(self):
        for metric in ("unauthorized_enablements", "administrative_completion"):
            value = deepcopy(self.value); row = value["slots"][0]; index = receipt.METRICS.index(metric)
            row["metric_counts"][index] = [1, 1] if metric == "unauthorized_enablements" else [0, 1]
            with self.subTest(metric=metric): self.reject(value)

    def test_wrong_p95_and_family_totals_are_rejected(self):
        value = deepcopy(self.value); value["overall"]["timings"]["p95_nearest_rank"] += 1
        self.reject(value)
        value = deepcopy(self.value); value["per_family"]["offboard_success"]["business_completions"] -= 1
        self.reject(value)

    def test_rates_use_summed_denominators_and_preserve_zero_denominator(self):
        # Deliberate arithmetic controls, not observed outcomes or altered fixtures.
        rows = deepcopy(self.value["slots"][:2]); index = receipt.METRICS.index("forbidden_grants_added")
        rows[0]["metric_counts"][index] = [1, 2]; rows[1]["metric_counts"][index] = [0, 8]
        result = receipt.aggregate(rows, metrics=True)["metrics"]["forbidden_grants_added"]
        self.assertEqual(result, {"numerator": 1, "denominator": 10, "rate": .1})
        rows[0]["metric_counts"][index] = [0, 0]; rows[1]["metric_counts"][index] = [0, 0]
        self.assertIsNone(receipt.aggregate(rows, metrics=True)["metrics"]["forbidden_grants_added"]["rate"])

    def test_unknown_usage_and_total_cost_cannot_be_reported_as_zero(self):
        for field in ("unknown_token_slots", "real_provider_or_total_system_cost_per_success"):
            value = deepcopy(self.value); value["cost_usage"][field] = 0
            with self.subTest(field=field): self.reject(value)

    def test_ties_cannot_be_claimed_as_uplift(self):
        self.value["paired"]["scripted_wins"] = 1
        self.reject(self.value)

    def test_D04_original_and_actual_counter_distinction_stays_explicit(self):
        self.value["counter_notes"]["D04_original_review_offline_decisions"] = 4
        self.reject(self.value)
        value = deepcopy(self.value); value["counter_notes"]["D04_original_review_offline_decisions"] = 5
        next(s for s in value["slots"] if s["task_id"] == "U2B-D04")["actual_policy_decisions"] = 5
        self.reject(value)

    def test_C12_harness_turns_cannot_be_called_policy_decisions(self):
        next(s for s in self.value["slots"] if s["task_id"] == "U2B-C12")["actual_policy_decisions"] = 8
        self.reject(self.value)

    def test_projection_cannot_claim_private_originals_or_final_acceptance(self):
        for field in ("raw_originals_published", "projection_is_original_review"):
            value = deepcopy(self.value); value["provenance"][field] = True
            with self.subTest(field=field): self.reject(value)
        self.value["final_acceptance"] = True
        self.reject(self.value)

    def test_private_paths_raw_markup_and_unexpected_trace_fields_rejected(self):
        value = deepcopy(self.value); value["limitations"][0] = "C:" + "/" + "Users" + "/example/private"
        self.reject(value)
        value = deepcopy(self.value); value["limitations"][0] = "<history>private raw state</history>"
        self.reject(value)
        self.value["slots"][0]["raw_trace"] = "provider text"
        self.reject(self.value)

    def test_pure_receipt_suite_is_registered_without_displacing_old_suites(self):
        self.assertEqual(dev.test_patterns("receipt-unit"), ["test_u2b_receipt_unit.py"])
        for suite in ("unit", "all"):
            self.assertIn("test_u2b_receipt_unit.py", dev.test_patterns(suite))
            self.assertIn("test_u2b_catalog_unit.py", dev.test_patterns(suite))


if __name__ == "__main__":
    unittest.main()
