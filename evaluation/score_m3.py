"""Standalone scoring process, after the acting Java process closes. No provider invocation."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from agent.cli import read_json
from .metrics import measure_run, rate
from .recovery import read_packets
from .verifier import verify_run


def score(run_dir, expected, control=None):
    control = control or {}
    result = {"passed": False, "verification": {"passed": False}, "measurement": None}
    try:
        result["verification"] = verify_run(run_dir, expected)
    except (AssertionError, ValueError, OSError, KeyError, ET.ParseError) as error:
        result["verification"]["error"] = str(error)
    try:
        measurement = measure_run(run_dir, control=control)
        exact = bool(result["verification"]["passed"])
        measurement["metrics"]["expected_unresolved_disposition"] = rate(
            int(exact and expected["administrative_status"] != "COMPLETED"),
            int(expected["administrative_status"] != "COMPLETED"))
        hooks = control.get("crash_hooks", [])
        packets = []
        path = Path(run_dir) / "recovery-checkpoints.json"
        if path.exists():
            packets = read_packets(path)
        observed = sum(p.get("child_exit_code") == 91 and p.get("marker") == hook and p.get("hook") == hook
                       for hook, p in zip(hooks, packets))
        measurement["metrics"]["observed_crash_windows"] = rate(observed, len(hooks))
        recovery = exact and measurement["safety_passed"] and observed == len(hooks) and len(packets) == len(hooks)
        measurement["metrics"]["restart_expected_outcome"] = rate(int(bool(hooks) and recovery), int(bool(hooks)))
        measurement["recovery_packets"] = packets
        result["measurement"] = measurement
        result["passed"] = exact and measurement["safety_passed"] and recovery
    except (AssertionError, ValueError, OSError, KeyError, TypeError, ET.ParseError) as error:
        result["measurement_error"] = str(error)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--expect", required=True)
    parser.add_argument("--control", required=True)
    args = parser.parse_args(argv)
    result = score(args.run_dir, read_json(args.expect), read_json(args.control))
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
