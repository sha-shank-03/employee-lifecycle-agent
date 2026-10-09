"""Separate-process domain scoring entry point, with no provider or Java invocation."""
import argparse
import json
import sys
from agent.cli import read_json
from .verifier import verify_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--expect", required=True)
    args = parser.parse_args()
    try:
        result = verify_run(args.run_dir, read_json(args.expect))
    except (AssertionError, ValueError, OSError) as error:
        print(json.dumps({"passed": False, "error": str(error)}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())

