"""Read/hash-only U2-A seal and accepted U1/v1 lineage. No sockets or child tools."""
import json
from pathlib import Path, PurePosixPath
from agent.bridge import ROOT
from agent.entra_contract import profile
from agent.gateway import strict
from evaluation.u1_source import sha
from tools.public import public_files

MANIFEST = "evaluation/upgrade/u2a-manifest.json"
SOURCE3_SHA = "934c13c0d1c5946c7bed9e20ce004ef68a50244cce12de448276986b88fb9730"
SOURCE3_REVIEW_SHA = "bc0924f9f69adadbd54df9807b046b764af8666f70640ff7af754234cf727392"
V1_SHA = "d16786aeaa27119ad086b2c9ff4943d63bb0ba7a6a2b74d00be14d594fd69431"

def check_u2a_source(root=ROOT):
    root = Path(root).resolve()
    def target(relative):
        if type(relative) is not str: raise AssertionError("invalid manifest path")
        p = PurePosixPath(relative)
        if p.is_absolute() or ".." in p.parts or "\\" in relative:
            raise AssertionError("invalid manifest path")
        path = root/relative
        if not path.resolve().is_relative_to(root): raise AssertionError("manifest path escape")
        return path
    manifest = strict(target(MANIFEST).read_bytes())
    if manifest["schema"] != 1 or manifest["version"] != "u2a-source-1" \
            or manifest["status"] != "source-ready-native-unexecuted" \
            or manifest["remote_dispatch_enabled"] is not False or manifest["self_accepted"] is not False:
        raise AssertionError("unknown U2-A source manifest")
    current = public_files(root)
    if set(manifest["files"]) != set(current)-{MANIFEST}:
        raise AssertionError("U2-A manifest coverage differs from public inventory")
    for relative, expected in manifest["files"].items():
        if sha(target(relative)) != expected: raise AssertionError("U2-A source changed after seal: "+relative)
    profile(strict(target(manifest["profile_path"]).read_bytes()))
    prior = manifest["prior_manifest"]
    if prior != {"version": "u1-source-3", "path": "evaluation/upgrade/history/u1-source-3.json", "sha256": SOURCE3_SHA} \
            or sha(target(prior["path"])) != SOURCE3_SHA \
            or sha(target("evaluation/upgrade/u1-manifest.json")) != SOURCE3_SHA:
        raise AssertionError("accepted source3 manifest changed")
    cursor = strict(target(prior["path"]).read_bytes())
    mapping = manifest["prior_source_archives"]
    if mapping != {"PUBLIC_FILES.json": "evaluation/upgrade/u1-source-3/PUBLIC_FILES.json"}:
        raise AssertionError("unexpected source3 source change")
    counts, archive_counts = {}, {}
    for version in ("u1-source-3", "u1-source-2", "u1-source-1"):
        if cursor["version"] != version: raise AssertionError("prior source version drift")
        for relative, expected in cursor["files"].items():
            if sha(target(mapping.get(relative, relative))) != expected:
                raise AssertionError("prior U1 source not preserved: "+version+":"+relative)
        counts[version] = len(cursor["files"])
        if version == "u1-source-1": break
        meta, archives = cursor["prior_manifest"], cursor["prior_source_archives"]
        next_version = "u1-source-2" if version == "u1-source-3" else "u1-source-1"
        if meta["version"] != next_version or meta["path"] != "evaluation/upgrade/history/"+next_version+".json" \
                or sha(target(meta["path"])) != meta["sha256"]:
            raise AssertionError("prior U1 manifest not preserved")
        previous = strict(target(meta["path"]).read_bytes())
        if not set(archives) <= set(previous["files"]) \
                or any(not p.startswith("evaluation/upgrade/"+next_version+"/") for p in archives.values()):
            raise AssertionError("invalid prior U1 archive root")
        archive_counts[next_version] = len(archives)
        mapping.update(archives)
        cursor = previous
    source3 = strict(target(prior["path"]).read_bytes())
    if source3["v1_manifest_sha256"] != V1_SHA or sha(target("evaluation/heldout/manifest.json")) != V1_SHA:
        raise AssertionError("original freeze changed")
    original = strict(target("evaluation/heldout/manifest.json").read_bytes())
    for relative, expected in original["files"].items():
        source = source3["v1_source_archives"].get(relative, relative)
        if relative in source3["v1_source_archives"] and not source.startswith("evaluation/upgrade/v1-source/"):
            raise AssertionError("invalid v1 archive root")
        if sha(target(source)) != expected: raise AssertionError("v1 source/data not preserved: "+relative)
    review_meta = manifest["prior_main_review"]
    if review_meta["path"] != "evaluation/upgrade/history/u1-source-3-main-review.json" \
            or review_meta["original_sha256"] != SOURCE3_REVIEW_SHA \
            or sha(target(review_meta["path"])) != review_meta["sha256"]:
        raise AssertionError("source3 acceptance not preserved")
    review = strict(target(review_meta["path"]).read_bytes())
    if review["decision"] != "passed" or review["reviewer"] != "main" \
            or review["source_manifest_sha256"] != SOURCE3_SHA \
            or review["original_main_review_sha256"] != SOURCE3_REVIEW_SHA:
        raise AssertionError("source3 acceptance identity mismatch")
    source2_review_meta = source3["prior_main_review"]
    if sha(target(source2_review_meta["path"])) != source2_review_meta["sha256"]:
        raise AssertionError("source2 acceptance changed")
    source2_review = strict(target(source2_review_meta["path"]).read_bytes())
    if source2_review["decision"] != "passed" or source2_review["independent_main"] is not True \
            or source2_review["source_manifest_sha256"] != source3["prior_manifest"]["sha256"] \
            or source2_review["original_main_review_sha256"] != source2_review_meta["original_sha256"]:
        raise AssertionError("source2 acceptance identity mismatch")
    return {"passed": True, "version": manifest["version"], "public_files": len(current),
            "current_hashed_files": len(manifest["files"]), "prior_u1_hashed_files": counts,
            "source3_exact_source_archives": 1, "earlier_exact_source_archives": archive_counts,
            "original_frozen_files": len(original["files"]), "v1_source_archives": len(source3["v1_source_archives"]),
            "accepted_prior_u1_versions": ["u1-source-2", "u1-source-3"],
            "u2a_self_accepted": False, "native_contract_execution": False,
            "remote_dispatch_enabled": False, "external_sandbox_calls": 0, "live_model_calls": 0,
            "limit": "Hash/schema preservation only; runtime evidence lives in separate execution records."}

if __name__ == "__main__": print(json.dumps(check_u2a_source(), indent=2, sort_keys=True))
