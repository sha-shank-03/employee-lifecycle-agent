"""Guarded source-only packaging tests; no quickstart, Java, sockets, or child tools."""
import ast
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import dev
from agent.bridge import ROOT
from evaluation.current_source import ANCHORS, MANIFEST, check_current_source
from evaluation.u1_source import sha
from tools.fresh_copy import quickstart_commands
from tools.public import check_public, public_files

class CurrentSourcePure(unittest.TestCase):
    def setUp(self):
        for name in ("subprocess.Popen", "socket.socket"):
            guard = patch(name, side_effect=AssertionError("pure packaging attempted native operation"))
            guard.start(); self.addCleanup(guard.stop)
        self.directory = None
    def source(self):
        # A public-byte fixture for negative hash tests, never a quickstart execution.
        if self.directory is None:
            (ROOT/"work").mkdir(exist_ok=True)
            folder = tempfile.TemporaryDirectory(prefix="current-source-pure-", dir=ROOT/"work")
            self.addCleanup(folder.cleanup); self.directory = Path(folder.name)
            for relative in public_files(ROOT):
                target = self.directory/relative; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/relative, target)
        return self.directory
    def current(self, root): return json.loads((root/MANIFEST).read_text())
    def write_current(self, root, value): (root/MANIFEST).write_text(json.dumps(value), encoding="utf-8")
    def update_current_hash(self, root, relative):
        value = self.current(root); value["files"][relative] = sha(root/relative); self.write_current(root, value)
    def test_current_gate_covers_all_public_bytes_and_preserved_lineage(self):
        result = check_current_source()
        self.assertEqual(result["current_hashed_files"], len(public_files())-1)
        self.assertEqual(result["predecessor_hashed_files"], {"u2b-evaluation-source-1":199,"u2a-transport-phase-source-1":180,"u2a-packaging-source-1":169,"u2a-source-1":159, "u1-source-3":147, "u1-source-2":137, "u1-source-1":128})
        self.assertEqual(result["original_frozen_files"], 40)
        self.assertEqual(result["v1_source_archives"], 7)
        self.assertFalse(result["remote_dispatch_enabled"])
    def test_cli_current_gate_runs_without_native_operations(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output): result = dev.main(["source-check"])
        self.assertEqual(result, 0); self.assertTrue(json.loads(output.getvalue())["passed"])
    def test_current_byte_tamper_is_rejected(self):
        root = self.source(); target = root/"agent/entra_contract.py"
        target.write_bytes(target.read_bytes()+b"\n# changed\n")
        with self.assertRaisesRegex(AssertionError, "source hash mismatch"): check_current_source(root)
    def test_omitted_manifest_file_is_rejected_even_if_inventory_has_it(self):
        root = self.source(); value = self.current(root); del value["files"]["agent/entra_contract.py"]
        self.write_current(root, value)
        with self.assertRaisesRegex(AssertionError, "coverage differs"): check_current_source(root)
    def test_unlisted_new_public_file_is_rejected(self):
        root = self.source(); (root/"docs/unlisted.txt").write_text("unlisted source\n")
        with self.assertRaisesRegex(ValueError, "inventory differs"): check_current_source(root)
    def test_inventory_omission_cannot_hide_existing_file(self):
        root = self.source(); p = root/"PUBLIC_FILES.json"; value = json.loads(p.read_text())
        value["files"].remove("tests/test_entra_u2a_loopback.py"); p.write_text(json.dumps(value))
        self.update_current_hash(root, "PUBLIC_FILES.json")
        with self.assertRaisesRegex(ValueError, "inventory differs"): check_current_source(root)
    def test_rehashed_predecessor_archive_tamper_is_still_rejected(self):
        root = self.source(); relative = "evaluation/upgrade/u2a-source-1/dev.py"
        p = root/relative; p.write_bytes(p.read_bytes()+b"\n# archive tamper\n")
        self.update_current_hash(root, relative)
        with self.assertRaisesRegex(AssertionError, "source hash mismatch"): check_current_source(root)
    def test_rehashed_original_manifest_cannot_replace_pinned_predecessor(self):
        root = self.source(); relative, _ = ANCHORS["u2b-evaluation-source-1"]
        p = root/relative; value = json.loads(p.read_text()); value["files"].pop("agent/entra_contract.py")
        p.write_text(json.dumps(value)); self.update_current_hash(root, relative)
        current = self.current(root); current["prior_manifest"]["sha256"] = sha(p); self.write_current(root, current)
        with self.assertRaisesRegex(AssertionError, "predecessor manifest changed"): check_current_source(root)
    def test_omitted_snapshot_mapping_does_not_skip_old_hash(self):
        root = self.source(); value = self.current(root); del value["prior_source_archives"]["dev.py"]
        self.write_current(root, value)
        with self.assertRaisesRegex(AssertionError, "u2b-evaluation-source-1:dev.py"): check_current_source(root)
    def test_archive_escape_is_rejected_before_read(self):
        root = self.source(); value = self.current(root); value["prior_source_archives"]["dev.py"] = "../outside.py"
        self.write_current(root, value)
        with self.assertRaisesRegex(AssertionError, "invalid source path"): check_current_source(root)
    def test_rehashed_old_lineage_and_main_receipt_tamper_cannot_pass(self):
        for relative in (ANCHORS["u1-source-2"][0], "evaluation/upgrade/history/u1-source-3-main-review.json",
                         "evaluation/heldout/manifest.json"):
            with self.subTest(relative=relative):
                root = self.source(); p = root/relative; original = p.read_bytes()
                p.write_bytes(original+b"\n"); self.update_current_hash(root, relative)
                with self.assertRaisesRegex(AssertionError, "source hash mismatch"): check_current_source(root)
                p.write_bytes(original); self.update_current_hash(root, relative)
    def test_current_public_copy_passes_static_checker_without_git_child(self):
        result = check_public(self.source())
        self.assertEqual(result["public_files"], len(public_files())); self.assertTrue(result["passed"])
    def test_suite_plans_keep_every_original_domain_provider_pattern(self):
        retained = {"test_unit.py", "test_m2_unit.py", "test_audit_unit.py", "test_integration.py",
                    "test_m2_integration.py", "test_provider_unit.py", "test_gateway_u1_unit.py",
                    "test_metrics_unit.py", "test_public_unit.py", "test_provider_http.py"}
        patterns = dev.test_patterns("all")
        self.assertTrue(retained <= set(patterns)); self.assertEqual(len(patterns), len(set(patterns)))
        self.assertIn("test_entra_u2a_unit.py", patterns); self.assertIn("test_entra_u2a_loopback.py", patterns)
        self.assertIn("test_current_source_unit.py", patterns)
        self.assertIn("test_u2b_unit.py", patterns)
        self.assertIn("test_u2b_catalog_unit.py", patterns)
        self.assertEqual(dev.test_patterns("u1-integration"), ["test_gateway_u1_integration.py"])
        self.assertEqual(dev.test_patterns("entra-unit"), ["test_entra_u2a_unit.py"])
        self.assertEqual(dev.test_patterns("entra-loopback"), ["test_entra_u2a_loopback.py"])
    def test_copy_command_plan_retains_original_journeys_and_verifiers(self):
        predecessor = ast.parse((ROOT/"evaluation/upgrade/u2a-source-1/tools/fresh_copy.py").read_text())
        assignment = next(n for n in ast.walk(predecessor) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "commands" for t in n.targets))
        retained = ast.literal_eval(assignment.value)
        retained = [["dev.py", "source-check"] if x == ["dev.py", "u1-source-check"] else x for x in retained]
        commands = quickstart_commands()
        self.assertEqual(commands[:len(retained)], retained)
        self.assertEqual(commands.count(["dev.py", "source-check"]), 1)
        self.assertNotIn(["dev.py", "u1-source-check"], commands)
        self.assertIn(["dev.py", "test", "--suite", "u1-integration"], commands)
        self.assertIn(["dev.py", "test", "--suite", "entra-loopback"], commands)
        self.assertEqual(len(commands), 12)
        self.assertIn("test_entra_u2a_unit.py", dev.test_patterns("unit"))
    def test_ci_replaces_only_gate_and_keeps_original_offline_coverage(self):
        previous = (ROOT/"evaluation/upgrade/u2a-source-1/.github/workflows/ci.yml").read_text()
        current = (ROOT/".github/workflows/ci.yml").read_text()
        commands = [line.strip() for line in previous.splitlines() if line.strip().startswith("python ")]
        for command in commands:
            self.assertIn(command.replace("dev.py u1-source-check", "dev.py source-check"), current)
        self.assertNotIn("python dev.py u1-source-check", current)
        self.assertIn("test_entra_u2a_unit.py", dev.test_patterns("all"))
        self.assertIn("test_entra_u2a_loopback.py", dev.test_patterns("all"))
        self.assertIn("python dev.py test --suite u1-integration", current)
        self.assertIn("python dev.py fresh-copy --out .build/ci-fresh-copy", current)

if __name__ == "__main__": unittest.main()
