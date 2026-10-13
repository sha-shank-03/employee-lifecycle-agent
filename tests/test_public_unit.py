"""Pure inventory/path/import checks and source-only copies; no quickstart child is run."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from agent.bridge import ROOT
from tools.fresh_copy import copy_source, fresh_copy_environment
from tools.public import inspect_text, public_files


class PublicUnitTests(unittest.TestCase):
    def setUp(self):
        no_child = patch("subprocess.Popen", side_effect=AssertionError("pure packaging suite spawned child"))
        no_socket = patch("socket.socket", side_effect=AssertionError("pure packaging suite opened socket"))
        no_child.start(); no_socket.start()
        self.addCleanup(no_child.stop); self.addCleanup(no_socket.stop)

    def test_windows_copy_environment_keeps_runtime_and_java_only(self):
        expected = {"SystemRoot": r"C:\Windows", "SystemDrive": "C:", "WINDIR": r"C:\Windows",
            "ProgramData": r"C:\ProgramData", "LOCALAPPDATA": r"C:\SyntheticProfile\Local",
            "USERPROFILE": r"C:\SyntheticProfile", "APPDATA": r"C:\SyntheticProfile\Roaming",
            "TEMP": r"C:\SyntheticTemp", "TMP": r"C:\SyntheticTemp", "PATH": r"C:\SyntheticBin",
            "JAVA_HOME": r"C:\SyntheticJdk", "COMSPEC": r"C:\Windows\System32\cmd.exe", "PATHEXT": ".EXE;.CMD"}
        sentinel = "sk-" + "x" * 24
        rejected = {name: sentinel for name in ("AI_GATEWAY_API_KEY", "SYNTHETIC_TOKEN", "AUTHORIZATION",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "PYTHONPATH", "PYTHONHOME",
            "PYTHONSTARTUP", "PYTHONUSERBASE", "UNRELATED_SETTING")}
        with patch("tools.fresh_copy.sys.platform", "win32"), patch("tools.fresh_copy.os.environ", {**expected, **rejected}):
            actual = fresh_copy_environment()
        self.assertEqual(actual, expected)
        self.assertTrue(set(actual).isdisjoint(rejected)); self.assertNotIn(sentinel, repr(actual))

    def test_minimal_windows_copy_environment_derives_absolute_os_defaults(self):
        supplied = {"SystemRoot": r"D:\Windows", "PATH": r"D:\SyntheticBin", "JAVA_HOME": r"D:\SyntheticJdk"}
        with patch("tools.fresh_copy.sys.platform", "win32"), patch("tools.fresh_copy.os.environ", supplied):
            actual = fresh_copy_environment()
        self.assertEqual(actual, {**supplied, "SystemDrive": "D:", "WINDIR": r"D:\Windows", "ProgramData": r"D:\ProgramData"})
        self.assertFalse(any("%" in value for value in actual.values()))

    def test_nonwindows_copy_environment_is_explicit_and_portable(self):
        for supplied, expected in (({}, {}), ({"PATH": "/synthetic/bin", "JAVA_HOME": "/synthetic/jdk",
            "SystemRoot": r"C:\Windows", "COMSPEC": "synthetic", "PATHEXT": "synthetic",
            "HTTP_PROXY": "synthetic", "PYTHONPATH": "synthetic"},
            {"PATH": "/synthetic/bin", "JAVA_HOME": "/synthetic/jdk"})):
            with self.subTest(supplied=supplied), patch("tools.fresh_copy.sys.platform", "linux"), patch("tools.fresh_copy.os.environ", supplied):
                self.assertEqual(fresh_copy_environment(), expected)

    def test_copy_environment_rejects_invalid_windows_root_or_drive(self):
        for supplied in ({}, {"SystemRoot": "relative"}, {"SystemRoot": r"C:\Windows", "SystemDrive": "%SystemDrive%"}):
            with self.subTest(supplied=supplied), patch("tools.fresh_copy.sys.platform", "win32"), patch("tools.fresh_copy.os.environ", supplied):
                with self.assertRaisesRegex(ValueError, "TRANSPORT_RUNTIME_ENV_INVALID"):
                    fresh_copy_environment()

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
