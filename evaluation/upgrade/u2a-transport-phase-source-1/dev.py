"""Java 17/Python 3.11 standard-library build and verification commands."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from agent.bridge import ROOT, java_executable


def doctor():
    versions = {}
    for name in ("java", "javac"):
        process = subprocess.run([java_executable(name), "-version"], capture_output=True, text=True, timeout=10)
        if process.returncode:
            raise RuntimeError(f"{name} version command failed: {process.returncode}")
        text = (process.stdout + process.stderr).strip()
        if not ("17." in text or "17 " in text):
            raise RuntimeError(f"Select a Java 17 JDK; found {text}")
        versions[name] = text.splitlines()[0]
    scratch = ROOT / ".build"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="doctor-", dir=scratch) as directory:
        command = [java_executable(), "-Xmx256m", "--source", "17", str(ROOT / "java/src/lifecycle/AtomicMoveDoctor.java"), directory]
        process = subprocess.run(command, capture_output=True, text=True, timeout=15)
        if process.returncode or "ATOMIC_MOVE_SUPPORTED" not in process.stdout:
            raise RuntimeError(f"Java atomic-move probe failed: {process.stderr.strip()}")
    print(json.dumps({"python": sys.version.split()[0], **versions,
                      "atomic_move": "supported on probed local filesystem", "downloads": 0}, indent=2))
    return 0


def build():
    classes = ROOT / ".build/classes"
    classes.mkdir(parents=True, exist_ok=True)
    sources = sorted((ROOT / "java/src").rglob("*.java"))
    command = [java_executable("javac"), "--release", "17", "-encoding", "UTF-8", "-d", str(classes), *map(str, sources)]
    result = subprocess.run(command, timeout=30)
    print(f"javac exit={result.returncode}; source files={len(sources)}")
    return result.returncode


def test_patterns(suite):
    """Inspectable offline suite plan; this function imports/runs no test module."""
    selected = {"u1-unit": ["test_gateway_u1_unit.py"], "u1-integration": ["test_gateway_u1_integration.py"],
                "entra-unit": ["test_entra_u2a_unit.py"], "entra-loopback": ["test_entra_u2a_loopback.py"],
                "packaging-unit": ["test_public_unit.py", "test_current_source_unit.py"]}
    if suite in selected: return selected[suite]
    if suite not in {"unit", "m1", "m2", "all", "provider-contract"}: raise ValueError("unknown test suite")
    patterns = []
    if suite != "provider-contract":
        patterns.append("test_unit.py")
    if suite in {"unit", "m2", "all"}:
        patterns.extend(("test_m2_unit.py", "test_audit_unit.py"))
    if suite in {"m1", "m2", "all"}:
        patterns.append("test_integration.py")
    if suite in {"m2", "all"}:
        patterns.append("test_m2_integration.py")
    if suite in {"unit", "all", "provider-contract"}:
        patterns.append("test_provider_unit.py")
    if suite in {"unit", "all"}:
        patterns.extend(("test_gateway_u1_unit.py", "test_metrics_unit.py", "test_public_unit.py",
                         "test_entra_u2a_unit.py", "test_current_source_unit.py"))
    if suite in {"all", "provider-contract"}:
        patterns.append("test_provider_http.py")
    if suite == "all": patterns.append("test_entra_u2a_loopback.py")
    return patterns


def test(suite):
    loader, tests = unittest.TestLoader(), unittest.TestSuite()
    for pattern in test_patterns(suite):
        tests.addTests(loader.discover(str(ROOT / "tests"), pattern=pattern, top_level_dir=str(ROOT)))
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    report = {"suite": suite, "tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "skipped": len(result.skipped), "live_model_calls": 0}
    if suite.startswith("u1-"): report["mode"] = "local-double"
    if suite.startswith("entra-"): report["mode"] = "injected-double"
    if suite == "packaging-unit": report["mode"] = "source-pure"
    print(json.dumps(report))
    return 0 if result.wasSuccessful() and not result.skipped else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor"); sub.add_parser("build")
    sub.add_parser("freeze-check")
    sub.add_parser("u1-source-check")
    sub.add_parser("source-check")
    sub.add_parser("check-public")
    fresh = sub.add_parser("fresh-copy")
    fresh.add_argument("--out", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--split", choices=["dev", "heldout"], required=True)
    evaluate.add_argument("--modes", default="fixed,scripted-adaptive")
    evaluate.add_argument("--repetitions", type=int, default=1)
    evaluate.add_argument("--out", required=True)
    check = sub.add_parser("test")
    check.add_argument("--suite", choices=["unit", "m1", "m2", "all", "provider-contract", "u1-unit", "u1-integration",
                                          "entra-unit", "entra-loopback", "packaging-unit"], default="unit")
    verifier = sub.add_parser("verify")
    verifier.add_argument("--run-dir", required=True); verifier.add_argument("--expect", required=True)
    args = parser.parse_args(argv)
    if sys.version_info[:2] != (3, 11):
        print("Use Python 3.11: py -3.11 dev.py ... on Windows", file=sys.stderr)
        return 1
    try:
        if args.command == "doctor": return doctor()
        if args.command == "build": return build()
        if args.command == "test": return test(args.suite)
        if args.command == "u1-source-check":
            from evaluation.u1_source import check_u1_source
            print(json.dumps(check_u1_source(), indent=2)); return 0
        if args.command == "source-check":
            from evaluation.current_source import check_current_source
            print(json.dumps(check_current_source(), indent=2)); return 0
        if args.command == "freeze-check":
            from evaluation.freeze import check_freeze
            print(json.dumps(check_freeze(), indent=2)); return 0
        if args.command == "check-public":
            from tools.public import check_public
            print(json.dumps(check_public(), indent=2)); return 0
        if args.command == "fresh-copy":
            from tools.fresh_copy import fresh_copy
            return fresh_copy(args.out)
        if args.command == "evaluate":
            if args.split == "heldout":
                from evaluation.run_heldout import run_heldout
                return run_heldout(args.out, args.modes.split(","), args.repetitions)
            from evaluation.run_dev import run_development
            return run_development(args.out, args.modes.split(","), args.repetitions)
        from evaluation.verifier import verify_run
        from agent.cli import read_json
        print(json.dumps(verify_run(args.run_dir, read_json(args.expect)), indent=2))
        return 0
    except (RuntimeError, ValueError, OSError, AssertionError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
