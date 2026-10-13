"""LEASE REQUIRED: one authored U1 loopback journey; operator approval is SCRIPTED."""
import argparse
from pathlib import Path
from .bridge import ROOT
from .cli import approve_review, create_review, initialize, read_json
from .gateway import canonical
from .u1 import configure, run, save_json
from .u1_double import LocalDouble
from evaluation.verifier import verify_run

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True); args = parser.parse_args(argv)
    directory = Path(args.out)
    fixture, config = ROOT/"fixtures/dev/offboard-success", ROOT/"fixtures/providers/gateway-u1-config.json"
    workflow = initialize(fixture, directory)["workflow_id"]; configure(directory, config)
    with LocalDouble() as double:
        before = run(directory, config, double.endpoint)
        if before["stop"] != "APPROVAL_PAUSE": raise AssertionError("approval gate not reached")
        _, review = create_review(directory, workflow)
        approve_review(directory, workflow, review, "hr-reviewer")
        after = run(directory, config, double.endpoint)
    verification = verify_run(directory, read_json(fixture/"expected.json"))
    result = {"mode": "local-double", "live_model": False, "external_integration": False,
        "operator_approval": "SCRIPTED fictional fixture", "before": before, "after": after,
        "verification": verification, "http_attempts": len(double.requests), "server_cleanup": double.cleanup}
    save_json(directory/"u1-demo.json", result)
    print(canonical(result).decode())
    return 0 if after["guarded"]["completed"] and verification["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
