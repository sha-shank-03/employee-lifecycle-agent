"""Lease-required paired development comparison; no heldout scoring is implemented here."""
import json
from pathlib import Path
import subprocess
import sys
from agent.bridge import ROOT
from agent.cli import read_json, write_json
from .scenarios import run_case
from .verifier import read_snapshot, JOIN, STEPS


def run_development(out, modes, repetitions):
    if not modes or len(set(modes)) != len(modes) or any(m not in {"fixed", "scripted-adaptive"} for m in modes):
        raise ValueError("modes must be distinct fixed/scripted-adaptive values")
    if not 1 <= repetitions <= 3:
        raise ValueError("one to three deterministic repetitions allowed")
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("evaluation output directory must be empty")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for repetition in range(1, repetitions + 1):
        for fixture in sorted(p for p in (ROOT / "fixtures/dev").iterdir() if p.is_dir()):
            for mode in modes:
                run_dir = out / f"rep-{repetition}" / mode / fixture.name
                label = read_json(fixture / "expected.json")
                row = {"id": fixture.name, "mode": mode, "repetition": repetition, "passed": False}
                try:
                    domain = run_case(read_json(fixture / "seed.json"), read_json(fixture / "request.json"),
                                      read_json(fixture / "driver.json"), run_dir, mode)
                    # Scoring is a separate Python process after the actor is closed.
                    process = subprocess.run([sys.executable, "-m", "evaluation.score", "--run-dir", str(run_dir),
                                              "--expect", str(fixture / "expected.json")],
                                             cwd=ROOT, capture_output=True, text=True, timeout=15)
                    scored = json.loads(process.stdout)
                    row.update(domain=domain, verification=scored, passed=process.returncode == 0 and scored["passed"])
                    workflow = read_snapshot(run_dir, "workflow")
                    identity = read_snapshot(run_dir, "identity")
                    steps = JOIN if workflow["intent"] == "onboard" else STEPS
                    approved_departure = workflow["intent"] == "offboard" and "approval_digest" in workflow
                    row["metrics"] = {
                        "required_steps_completed": {"numerator": sum(workflow["step." + s] == "DONE" for s in steps), "denominator": 5},
                        "incomplete_revocation": {"numerator": int(approved_departure and (identity["enabled"] == "true" or identity["sessions"] != "0" or bool(identity["grants"]))), "denominator": int(approved_departure)},
                        "authoritative_false_completion": int(domain["administrative_status"] == "COMPLETED" and label["administrative_status"] != "COMPLETED"),
                        "forbidden_committed_access_effects": 0 if row["passed"] else None,
                        "duplicate_business_effects": 0 if row["passed"] else None,
                        "expected_unresolved_disposition": {"numerator": int(row["passed"] and label["administrative_status"] != "COMPLETED"), "denominator": int(label["administrative_status"] != "COMPLETED")},
                    }
                except (RuntimeError, ValueError, OSError, AssertionError, subprocess.SubprocessError) as error:
                    row["error"] = str(error)
                rows.append(row)
                write_json(run_dir / "score.json", row)
    by_mode = {}
    for mode in modes:
        selected = [r for r in rows if r["mode"] == mode]
        by_mode[mode] = {"exact_outcome_success": {"numerator": sum(r["passed"] for r in selected), "denominator": len(selected)},
                         "failures": [{"id": r["id"], "repetition": r["repetition"], "reason": r.get("error", r.get("verification", {}).get("error", ""))} for r in selected if not r["passed"]]}
    paired = []
    if set(modes) == {"fixed", "scripted-adaptive"}:
        for repetition in range(1, repetitions + 1):
            for case in sorted({r["id"] for r in rows}):
                pair = {r["mode"]: r["passed"] for r in rows if r["id"] == case and r["repetition"] == repetition}
                paired.append({"id": case, "repetition": repetition, "outcomes": pair})
    report = {"split": "dev", "cases": 12, "case_runs": len(rows), "repetitions": repetitions,
              "by_mode": by_mode, "paired": paired, "rows": rows, "live_model_calls": 0,
              "provider_quality_evaluated": False, "empty_denominator_display": "N/A",
              "limit": "authored deterministic integration comparison; neither a blind benchmark nor an LLM quality result"}
    write_json(out / "report.json", report)
    print(json.dumps({"cases": 12, "case_runs": len(rows), "by_mode": by_mode}, indent=2))
    return 0 if all(r["passed"] for r in rows) else 1

