"""Pure inventory/path/import checks and source-only copies; no quickstart child is run."""
import json
from pathlib import Path
import tempfile
import unittest
from agent.bridge import ROOT
from tools.fresh_copy import copy_source
from tools.public import inspect_text, public_files


class PublicUnitTests(unittest.TestCase):
    def test_personal_path_pattern_is_detected(self):
        sample = "C:" + "/" + "Users" + "/fictional/project.py"
        self.assertIn("personal path", inspect_text("sample.txt", sample))

    def test_secret_shape_is_detected_without_shipping_a_literal_key(self):
        sample = "sk-" + "x" * 24
        self.assertIn("credential-shaped literal", inspect_text("sample.txt", sample))

    def test_external_python_dependency_is_detected(self):
        self.assertIn("undeclared runtime import", inspect_text("sample.py", "import unavailable_library\n"))

    def test_copy_uses_only_inventory_and_preserves_source(self):
        (ROOT / "work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "work", prefix="copy-unit-") as temporary:
            source = Path(temporary)
            (source / "work").mkdir()
            (source / "work/private.txt").write_text("synthetic nonpublic note")
            (source / "dev.py").write_text("print('synthetic source')\n")
            (source / "PUBLIC_FILES.json").write_text(json.dumps({"schema": 1, "files": ["PUBLIC_FILES.json", "dev.py"]}))
            destination = source / "work/copied"
            hashes = copy_source(destination, source)
            self.assertEqual(set(hashes), {"PUBLIC_FILES.json", "dev.py"})
            self.assertFalse((destination / "work/private.txt").exists())
            self.assertEqual(public_files(destination), ["PUBLIC_FILES.json", "dev.py"])

    def test_copy_rejects_output_outside_its_root(self):
        with self.assertRaisesRegex(ValueError, "child"):
            copy_source(ROOT)


if __name__ == "__main__":
    unittest.main()
