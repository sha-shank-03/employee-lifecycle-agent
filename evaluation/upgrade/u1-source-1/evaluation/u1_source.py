"""Read/hash-only U1 manifest; preserves original v1 freeze through exact source archives."""
import hashlib
from pathlib import Path, PurePosixPath
from agent.bridge import ROOT
from agent.gateway import strict

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_u1_source(root=ROOT):
    root = Path(root).resolve()
    manifest = strict((root/"evaluation/upgrade/u1-manifest.json").read_bytes())
    if manifest["schema"] != 1 or manifest["version"] != "u1-source-1" or manifest["status"] != "source-ready-integration-unexecuted":
        raise AssertionError("unknown U1 source manifest")
    def target(relative):
        p = PurePosixPath(relative)
        if p.is_absolute() or ".." in p.parts or "\\" in relative: raise AssertionError("invalid manifest path")
        path = root/relative
        if not path.resolve().is_relative_to(root): raise AssertionError("manifest path escape")
        return path
    original = target("evaluation/heldout/manifest.json")
    if sha(original) != manifest["v1_manifest_sha256"]: raise AssertionError("original freeze was changed")
    v1 = strict(original.read_bytes())
    archives = manifest["v1_source_archives"]
    for relative, expected in v1["files"].items():
        source = archives.get(relative, relative)
        if relative in archives and not source.startswith("evaluation/upgrade/v1-source/"):
            raise AssertionError("invalid v1 archive root")
        if sha(target(source)) != expected: raise AssertionError("v1 source/data not preserved: "+relative)
    for relative, expected in manifest["files"].items():
        if sha(target(relative)) != expected: raise AssertionError("U1 source changed after seal: "+relative)
    return {"passed": True, "version": manifest["version"], "v1_commit": manifest["v1_commit"],
            "original_frozen_files": len(v1["files"]), "exact_v1_source_archives": len(archives),
            "current_hashed_files": len(manifest["files"]), "integration_executed": False,
            "scored_case_runs": 0, "live_model_calls": 0}
