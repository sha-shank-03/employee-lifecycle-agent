"""Read/hash-only U1 manifest; preserves original v1 freeze through exact source archives."""
import hashlib
from pathlib import Path, PurePosixPath
from agent.bridge import ROOT
from agent.gateway import strict

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_u1_source(root=ROOT):
    root = Path(root).resolve()
    manifest = strict((root/"evaluation/upgrade/u1-manifest.json").read_bytes())
    if manifest["schema"] != 1 or manifest["version"] != "u1-source-3" or manifest["status"] != "source-ready-packaging-unexecuted":
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
    cursor, resolved_sources, prior_counts, archive_counts = manifest, {}, {}, {}
    for version in ("u1-source-2", "u1-source-1"):
        prior = cursor["prior_manifest"]
        if prior["path"] != "evaluation/upgrade/history/"+version+".json" or prior["version"] != version \
                or sha(target(prior["path"])) != prior["sha256"]:
            raise AssertionError("prior U1 manifest not preserved")
        previous = strict(target(prior["path"]).read_bytes())
        prior_archives = cursor["prior_source_archives"]
        if previous["version"] != version or not set(prior_archives) <= set(previous["files"]):
            raise AssertionError("invalid prior U1 source provenance")
        if any(not source.startswith("evaluation/upgrade/"+version+"/") for source in prior_archives.values()):
            raise AssertionError("invalid prior U1 archive root")
        # Carry newer snapshots for files an older revision did not change;
        # that older revision's explicit archives take precedence when present.
        resolved_sources.update(prior_archives)
        for relative, expected in previous["files"].items():
            if sha(target(resolved_sources.get(relative, relative))) != expected:
                raise AssertionError("prior U1 source not preserved: "+version+":"+relative)
        prior_counts[version], archive_counts[version] = len(previous["files"]), len(prior_archives)
        cursor = previous
    review_meta = manifest["prior_main_review"]
    if review_meta["path"] != "evaluation/upgrade/history/u1-source-2-main-review.json" \
            or review_meta["source_version"] != "u1-source-2" or sha(target(review_meta["path"])) != review_meta["sha256"]:
        raise AssertionError("accepted prior U1 review not preserved")
    review = strict(target(review_meta["path"]).read_bytes())
    if review["source_manifest_sha256"] != manifest["prior_manifest"]["sha256"] \
            or review["original_main_review_sha256"] != review_meta["original_sha256"] \
            or review["decision"] != "passed" or review["independent_main"] is not True:
        raise AssertionError("prior U1 acceptance identity mismatch")
    return {"passed": True, "version": manifest["version"], "v1_commit": manifest["v1_commit"],
            "original_frozen_files": len(v1["files"]), "exact_v1_source_archives": len(archives),
            "current_hashed_files": len(manifest["files"]), "prior_u1_hashed_files": prior_counts,
            "exact_prior_u1_source_archives": archive_counts, "accepted_prior_u1_version": "u1-source-2",
            "current_packaging_executed": False, "integration_executed": False,
            "scored_case_runs": 0, "live_model_calls": 0}
