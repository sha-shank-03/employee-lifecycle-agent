"""Pure current packaging seal, complete inventory, and immutable predecessor lineage."""
import json
from pathlib import Path, PurePosixPath
from agent.bridge import ROOT
from agent.entra_contract import profile
from agent.gateway import strict
from evaluation.u1_source import sha
from tools.public import public_files

MANIFEST = "evaluation/upgrade/current-manifest.json"
ANCHORS = {
    "u2a-transport-phase-source-1": ("evaluation/upgrade/history/u2a-transport-phase-source-1.json", "daea583e9ee74a869dd382a39e4aae9f04ad7eca5d39869f9c04e28dab05337d"),
    "u2a-packaging-source-1": ("evaluation/upgrade/history/u2a-packaging-source-1.json", "a4f5077b50de1e326bc93a52b1563070168a324979d4b3be026dd60abe13e9db"),
    "u2a-source-1": ("evaluation/upgrade/u2a-manifest.json", "e65c5e9ff0671dc1ab2f7b7de0d046ac2bc53f8f118d6515e75155389310e6f8"),
    "u1-source-3": ("evaluation/upgrade/history/u1-source-3.json", "934c13c0d1c5946c7bed9e20ce004ef68a50244cce12de448276986b88fb9730"),
    "u1-source-2": ("evaluation/upgrade/history/u1-source-2.json", "a77f12e5d28efa97be9850252886417a194bde328fb762ec5e4c168ef5788295"),
    "u1-source-1": ("evaluation/upgrade/history/u1-source-1.json", "895b5d1df9c9dbe1748a51364bb7a714a892ca867396e5af3ef120881674b7fe"),
}
V1_SHA = "d16786aeaa27119ad086b2c9ff4943d63bb0ba7a6a2b74d00be14d594fd69431"
SOURCE3_REVIEW_SHA = "bc0924f9f69adadbd54df9807b046b764af8666f70640ff7af754234cf727392"
SOURCE2_REVIEW_SHA = "711f4aa3480ea9a89e4ed4b4a4238751058566a485e0692fdbe6c62137df7e96"
U2A_REVIEW_SHA = "7218655ab87841e962b54183f7ef20aef9f22adde9e5558818abac31dc3585e9"

def need(condition, message):
    if not condition: raise AssertionError(message)

def check_current_source(root=ROOT):
    root = Path(root).resolve()
    def target(relative):
        need(type(relative) is str, "invalid source path")
        p = PurePosixPath(relative)
        need(relative and not p.is_absolute() and ".." not in p.parts and "\\" not in relative
             and p.as_posix() == relative and ":" not in relative, "invalid source path")
        result = root/relative
        need(result.resolve().is_relative_to(root), "source path escape")
        need(not any(p.is_symlink() for p in (result, *result.parents) if p.is_relative_to(root)), "source symlink")
        return result
    def load(relative): return strict(target(relative).read_bytes())
    def verify_files(manifest, mapping, label):
        need(type(manifest["files"]) is dict, "invalid source hash inventory")
        for relative, expected in manifest["files"].items():
            need(sha(target(mapping.get(relative, relative))) == expected, "source hash mismatch: "+label+":"+relative)
    def advance(cursor, version, mapping):
        path, expected = ANCHORS[version]
        need(cursor["prior_manifest"] == {"path": path, "sha256": expected, "version": version}
             and sha(target(path)) == expected, "predecessor manifest changed: "+version)
        previous = load(path)
        need(previous["version"] == version, "predecessor version changed")
        archives = cursor["prior_source_archives"]
        need(type(archives) is dict and set(archives) <= set(previous["files"]), "invalid predecessor archives")
        for relative, archived in archives.items():
            target(relative); target(archived)
            need(archived == "evaluation/upgrade/"+version+"/"+relative, "invalid predecessor archive path")
        # Older explicit snapshots override newer snapshots; unchanged older files keep theirs.
        mapping.update(archives)
        verify_files(previous, mapping, version)
        return previous, len(archives)

    manifest = load(MANIFEST)
    need(type(manifest["schema"]) is int and manifest["schema"] == 1
         and manifest["version"] == "u2b-evaluation-source-1"
         and manifest["status"] == "source-ready-offline-evaluation-unexecuted"
         and manifest["remote_dispatch_enabled"] is False and manifest["self_accepted"] is False,
         "unknown current packaging manifest")
    files = public_files(root)
    need(set(manifest["files"]) == set(files)-{MANIFEST}, "current manifest coverage differs from public inventory")
    verify_files(manifest, {}, manifest["version"])
    need(manifest["profile_path"] == "fixtures/providers/entra-u2a-profile.json", "profile path changed")
    profile(load(manifest["profile_path"]))
    cursor, mapping, snapshots, archives = manifest, {}, {}, {}
    predecessors = {}
    for version in ("u2a-transport-phase-source-1", "u2a-packaging-source-1", "u2a-source-1", "u1-source-3", "u1-source-2", "u1-source-1"):
        cursor, archived = advance(cursor, version, mapping)
        snapshots[version], archives[version] = len(cursor["files"]), archived
        predecessors[version] = cursor
    source3 = predecessors["u1-source-3"]
    need(sha(target("evaluation/upgrade/u1-manifest.json")) == ANCHORS["u1-source-3"][1], "original U1 manifest changed")
    need(source3["v1_manifest_sha256"] == V1_SHA and manifest["v1_manifest_sha256"] == V1_SHA
         and sha(target("evaluation/heldout/manifest.json")) == V1_SHA, "original v1 freeze changed")
    v1 = load("evaluation/heldout/manifest.json")
    v1_archives = source3["v1_source_archives"]
    need(type(v1_archives) is dict and set(v1_archives) <= set(v1["files"]), "invalid v1 archives")
    for relative, archived in v1_archives.items():
        need(archived == "evaluation/upgrade/v1-source/"+relative, "invalid v1 archive path")
    verify_files(v1, v1_archives, "v1")

    # The unchanged anchored manifests bind the public copies; original receipts remain separately attributable.
    review3_meta = predecessors["u2a-source-1"]["prior_main_review"]
    need(review3_meta["path"] == "evaluation/upgrade/history/u1-source-3-main-review.json"
         and review3_meta["original_sha256"] == SOURCE3_REVIEW_SHA
         and sha(target(review3_meta["path"])) == review3_meta["sha256"], "source3 review changed")
    review3 = load(review3_meta["path"])
    need(review3["decision"] == "passed" and review3["reviewer"] == "main"
         and review3["original_main_review_sha256"] == SOURCE3_REVIEW_SHA
         and review3["source_manifest_sha256"] == ANCHORS["u1-source-3"][1], "source3 review identity changed")
    review2_meta = source3["prior_main_review"]
    need(review2_meta["path"] == "evaluation/upgrade/history/u1-source-2-main-review.json"
         and review2_meta["original_sha256"] == SOURCE2_REVIEW_SHA
         and sha(target(review2_meta["path"])) == review2_meta["sha256"], "source2 review changed")
    review2 = load(review2_meta["path"])
    need(review2["decision"] == "passed" and review2["independent_main"] is True
         and review2["original_main_review_sha256"] == SOURCE2_REVIEW_SHA
         and review2["source_manifest_sha256"] == ANCHORS["u1-source-2"][1], "source2 review identity changed")
    review_meta=manifest["prior_main_review"]
    need(review_meta["path"]=="evaluation/upgrade/history/u2a-local-main-review.json"
         and review_meta["original_sha256"]==U2A_REVIEW_SHA
         and sha(target(review_meta["path"]))==review_meta["sha256"], "U2A review changed")
    review=load(review_meta["path"])
    need(review["decision"]=="u2a_local_root_and_copied_quickstart_passed" and review["reviewer"]=="main"
         and review["original_main_review_sha256"]==U2A_REVIEW_SHA
         and review["source_manifest_sha256"]==ANCHORS["u2a-transport-phase-source-1"][1]
         and (review["root_current_methods"],review["root_unchanged_historical_methods"],review["root_inventory_covered"])
             ==(104,167,271) and (review["copy_groups"],review["copied_cells"],review["copied_repeated_methods"])
             ==(9,15,208), "U2A review accounting/identity changed")
    from evaluation.u2b_data import DATA, load_split
    need(manifest["dataset_manifest"]=={"path":DATA.as_posix(),"sha256":sha(target(DATA.as_posix()))},"U2B data manifest differs")
    development,capability=load_split("development",root),load_split("capability",root)
    need((len(development["tasks"]),len(capability["tasks"]))==(8,12),"authored slice changed")
    return {"passed": True, "version": manifest["version"], "current_public_files": len(files),
            "current_hashed_files": len(manifest["files"]), "predecessor_hashed_files": snapshots,
            "exact_predecessor_source_archives": archives, "original_frozen_files": len(v1["files"]),
            "v1_source_archives": len(v1_archives), "preserved_main_acceptance": ["u1-source-2", "u1-source-3", "u2a-local-root-copy"],
            "current_source_self_accepted": False, "remote_dispatch_enabled": False,
            "current_native_packaging_executed": False, "external_sandbox_calls": 0, "live_model_calls": 0,
            "current_u2b_evaluation_executed": False, "author_exposed_unique_records":20,"scenario_families":12,
            "limit": "Complete public inventory/hash and retained lineage gate only; execution evidence is separate."}

if __name__ == "__main__": print(json.dumps(check_current_source(), indent=2, sort_keys=True))
