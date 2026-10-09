"""LEASE/REVIEW REQUIRED: frozen 36-case fixed versus scripted-adaptive comparison.

Every planned row remains in the denominator, including harness/scorer failures.
Repetitions exercise deterministic persistence contracts, not stochastic model quality.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from agent.bridge import ROOT
from agent.cli import read_json, write_json
from agent.protocol import strict_json
from .freeze import check_freeze
from .metrics import SAFETY_GATES, rate
from .scenarios import run_case


def load_cases():
    manifest = check_freeze()
    folder = ROOT / "evaluation/heldout"
    inputs = [strict_json(line) for line in (folder / "inputs.jsonl").read_text(encoding="utf-8").splitlines()]
    labels = [strict_json(line) for line in (folder / "labels.jsonl").read_text(encoding="utf-8").splitlines()]
    rubric = read_json(ROOT / "evaluation/rubric.json")
    comparison = rubric["comparison"]
    if comparison["cases"] != len(inputs) or comparison["groups"] != manifest["groups"] \
            or comparison["modes"] != ["fixed", "scripted-adaptive"] \
            or comparison["repetitions"] != 3 or comparison["planned_case_runs"] != len(inputs) * 2 * 3 \
            or rubric["safety_gates"] != list(SAFETY_GATES):
        raise ValueError("frozen rubric differs from implemented comparison")
    if any(set(case) != {"id", "group", "seed", "request", "control"} for case in inputs):
        raise ValueError("unknown frozen case topology")
    for case in inputs:
        if Path(case["id"]).name != case["id"] or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in case["id"]):
            raise ValueError("unsafe case ID")
    return inputs, {label["id"]: label["expected"] for label in labels}, manifest


def aggregate(rows, modes, repetitions):
    by_mode, paired = {}, []
    names = set().union(*(r.get("scoring", {}).get("measurement", {}).get("metrics", {})
                          for r in rows if r.get("scoring", {}).get("measurement")))
    for mode in modes:
        selected = [r for r in rows if r["mode"] == mode]
        counts = {}
        for name in sorted(names):
            observations = [r["scoring"]["measurement"]["metrics"][name] for r in selected
                            if r.get("scoring", {}).get("measurement") and name in r["scoring"]["measurement"]["metrics"]]
            counts[name] = {**rate(sum(o["numerator"] for o in observations), sum(o["denominator"] for o in observations)),
                            "measured_case_runs": len(observations), "missing_case_runs": len(selected) - len(observations)}
        groups = {}
        for group in sorted({r["group"] for r in selected}):
            group_rows = [r for r in selected if r["group"] == group]
            groups[group] = rate(sum(r["passed"] for r in group_rows), len(group_rows))
        by_mode[mode] = {"exact_outcome_and_safety": rate(sum(r["passed"] for r in selected), len(selected)),
                         "exact_outcome_only": rate(sum(bool(r.get("scoring", {}).get("verification", {}).get("passed")) for r in selected), len(selected)),
                         "metrics": counts, "groups": groups,
                         "dispositions": dict(Counter(r.get("scoring", {}).get("measurement", {}).get("disposition", "UNMEASURED")
                                                      if r.get("scoring", {}).get("measurement") else "UNMEASURED" for r in selected)),
                         "failures": [{"id": r["id"], "repetition": r["repetition"], "error": r.get("error"),
                                       "scoring": r.get("scoring")} for r in selected if not r["passed"]]}
    if set(modes) == {"fixed", "scripted-adaptive"}:
        for repetition in range(1, repetitions + 1):
            for case in sorted({r["id"] for r in rows}):
                pair = {r["mode"]: r["passed"] for r in rows if r["id"] == case and r["repetition"] == repetition}
                winner = "tie" if pair["fixed"] == pair["scripted-adaptive"] else next(k for k, v in pair.items() if v)
                paired.append({"id": case, "repetition": repetition, "outcomes": pair, "winner": winner})
    return {"by_mode": by_mode, "paired": paired, "paired_counts": dict(Counter(p["winner"] for p in paired))}


def run_heldout(out, modes, repetitions):
    if set(modes) != {"fixed", "scripted-adaptive"} or len(modes) != 2:
        raise ValueError("heldout requires both distinct fixed,scripted-adaptive modes")
    if type(repetitions) is not int or not 1 <= repetitions <= 3:
        raise ValueError("one to three deterministic repetitions allowed")
    cases, labels, freeze = load_cases()
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("evaluation output directory must be empty")
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "evaluation/heldout/manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    write_json(out / "execution-plan.json", {"split": "heldout", "cases": len(cases), "modes": modes,
               "repetitions": repetitions, "planned_case_runs": len(cases) * len(modes) * repetitions,
               "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(), "freeze": freeze,
               "started_at": datetime.now(timezone.utc).isoformat(), "live_model_calls": 0})
    rows = []
    for repetition in range(1, repetitions + 1):
        for case in cases:
            for mode in modes:
                folder = out / f"rep-{repetition}" / mode / case["id"]
                row = {"id": case["id"], "group": case["group"], "mode": mode, "repetition": repetition,
                       "passed": False, "run_dir": str(folder.relative_to(out)), "started_at": datetime.now(timezone.utc).isoformat()}
                row["shared_boundary_controls"] = [key for key in ("proposal_extra", "request_rejection", "adversarial_provider") if key in case["control"]]
                started = time.monotonic()
                try:
                    # Only seed/request/control enter the operator-owned driver. Labels never enter a provider.
                    row["domain_report"] = run_case(case["seed"], case["request"], case["control"], folder, mode)
                except (RuntimeError, ValueError, OSError, AssertionError, KeyError) as error:
                    row["error"] = str(error)
                # Score remaining committed evidence even if the harness failed. Never drop this row.
                write_json(folder / "expected-for-scorer.json", labels[case["id"]])
                write_json(folder / "control-for-scorer.json", case["control"])
                try:
                    process = subprocess.run([sys.executable, "-m", "evaluation.score_m3", "--run-dir", str(folder),
                        "--expect", str(folder / "expected-for-scorer.json"), "--control", str(folder / "control-for-scorer.json")],
                        cwd=ROOT, capture_output=True, text=True, timeout=15)
                    row["scorer_exit_code"] = process.returncode
                    row["scoring"] = strict_json(process.stdout)
                    row["passed"] = "error" not in row and process.returncode == 0 and row["scoring"]["passed"]
                except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
                    row["scorer_error"] = str(error)
                row["elapsed_seconds"] = round(time.monotonic() - started, 3)
                rows.append(row)
                write_json(folder / "score.json", row)
                with (out / "rows.jsonl").open("a", encoding="utf-8") as log:
                    log.write(json.dumps(row, sort_keys=True) + "\n")
                print(json.dumps({"id": row["id"], "mode": mode, "repetition": repetition, "passed": row["passed"],
                                  "case_run": len(rows), "planned": len(cases) * len(modes) * repetitions}), flush=True)
    unchanged = manifest_bytes == manifest_path.read_bytes()
    final_freeze = check_freeze()
    report = {"split": "heldout", "cases": len(cases), "case_runs": len(rows), "repetitions": repetitions,
              "modes": modes, **aggregate(rows, modes, repetitions), "rows": rows, "freeze": final_freeze,
              "manifest_unchanged": unchanged, "live_model_calls": 0, "provider_quality_evaluated": False,
              "safety_gates": list(SAFETY_GATES), "empty_denominator_display": "N/A (JSON null)",
              "limit": "Authored inspectable deterministic holdout. Expected blocks are not completed journeys; remaining departure access is reported even for an expected outage. Repetitions are not independent statistical samples."}
    write_json(out / "report.json", report)
    print(json.dumps({"case_runs": len(rows), "paired_counts": report["paired_counts"],
                      "by_mode": {m: r["exact_outcome_and_safety"] for m, r in report["by_mode"].items()}}, indent=2))
    return 0 if unchanged and all(r["passed"] for r in rows) else 1
