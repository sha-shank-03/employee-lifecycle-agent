"""LEASE REQUIRED: copy only reviewed public repository files, then run offline quickstart."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from agent.bridge import ROOT
from agent.cli import write_json
from agent.gateway import _transport_environment
from .public import check_public, public_files


def fresh_copy_environment():
    """Reuse Windows runtime paths; add only explicit Java/tool resolution values."""
    environment = _transport_environment()
    names = ("PATH", "JAVA_HOME")
    if sys.platform == "win32":
        names += ("COMSPEC", "PATHEXT")
    for name in names:
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def copy_source(out, root=ROOT):
    root = Path(root).resolve()
    out = Path(out).resolve()
    if not any(out.is_relative_to(root / folder) and out != root / folder for folder in (".build", "work")):
        raise ValueError("fresh-copy output must be a child of this repository's .build or work directory")
    if out.exists() and any(out.iterdir()):
        raise ValueError("fresh-copy output must be empty")
    files = public_files(root)
    out.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for relative in files:
        source, target = root / relative, out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        hashes[relative] = hashlib.sha256(target.read_bytes()).hexdigest()
        if hashes[relative] != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError("fresh-copy source mismatch")
    return hashes


def fresh_copy(out):
    check_public()
    folder = Path(out).resolve()
    hashes = copy_source(folder)
    # Ignore Python startup env/user packages; retain only installed runtime/OS resolution.
    environment = fresh_copy_environment()
    commands = [
        ["dev.py", "check-public"], ["dev.py", "u1-source-check"], ["dev.py", "doctor"], ["dev.py", "build"],
        ["dev.py", "test", "--suite", "unit"],
        ["-m", "agent.cli", "demo", "--scenario", "offboard-success", "--provider", "scripted", "--run-dir", "runs/fresh-departure"],
        ["-m", "agent.cli", "demo", "--scenario", "onboard-compensation", "--provider", "scripted", "--run-dir", "runs/fresh-compensation"],
        ["dev.py", "verify", "--run-dir", "runs/fresh-departure", "--expect", "fixtures/dev/offboard-success/expected.json"],
        ["dev.py", "verify", "--run-dir", "runs/fresh-compensation", "--expect", "fixtures/dev/onboard-compensation/expected.json"],
        ["-m", "agent.u1_demo", "--out", "runs/fresh-u1-double"],
    ]
    results, evidence = [], ROOT / "work/fresh-copy-evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    report_path = evidence / (folder.name + ".json")
    for index, arguments in enumerate(commands, 1):
        started = time.monotonic()
        process = subprocess.run([sys.executable, "-E", "-s", *arguments], cwd=folder, env=environment,
                                 capture_output=True, text=True, timeout=180)
        log = evidence / f"{folder.name}-{index:02d}.log"
        log.write_text(process.stdout + process.stderr, encoding="utf-8")
        results.append({"arguments": arguments, "exit_code": process.returncode,
                        "elapsed_seconds": round(time.monotonic() - started, 3), "log": log.relative_to(ROOT).as_posix()})
        write_json(report_path, {"source_hashes": hashes, "copied_public_files": len(hashes), "commands": results,
                                "complete": len(results) == len(commands), "downloads": 0, "live_model_calls": 0})
        print(json.dumps(results[-1]), flush=True)
        if process.returncode:
            return 1
    print(json.dumps({"passed": True, "copied_public_files": len(hashes), "commands": len(results),
                      "report": report_path.relative_to(ROOT).as_posix()}))
    return 0
