"""Check frozen authored heldout membership, labels and acting/scoring source hashes."""
import hashlib
from collections import Counter
from pathlib import Path
from agent.bridge import ROOT
from agent.protocol import strict_json


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_freeze(manifest_path=None):
    path = Path(manifest_path or ROOT / "evaluation/heldout/manifest.json")
    manifest = strict_json(path.read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        target = (ROOT / relative).resolve()
        if not target.is_relative_to(ROOT):
            raise AssertionError("freeze path outside repository")
        if sha256(target) != expected:
            raise AssertionError("frozen file changed: " + relative)
    inputs = (ROOT / "evaluation/heldout/inputs.jsonl").read_text(encoding="utf-8").splitlines()
    labels = (ROOT / "evaluation/heldout/labels.jsonl").read_text(encoding="utf-8").splitlines()
    input_ids, label_ids = [strict_json(x)["id"] for x in inputs], [strict_json(x)["id"] for x in labels]
    if len(inputs) != 36 or len(set(input_ids)) != 36 or input_ids != label_ids:
        raise AssertionError("heldout denominator/membership differs")
    cases = manifest["cases"]
    if [c["id"] for c in cases] != input_ids:
        raise AssertionError("manifest membership differs")
    for c, raw_input, raw_label in zip(cases, inputs, labels):
        for key, raw in (("input_sha256", raw_input), ("label_sha256", raw_label)):
            if hashlib.sha256(raw.encode("utf-8")).hexdigest() != c[key]:
                raise AssertionError("frozen case changed: " + c["id"])
    actual_groups = dict(Counter(strict_json(x)["group"] for x in inputs))
    if actual_groups != manifest["groups"] or sorted(actual_groups.values()) != [6] * 6:
        raise AssertionError("frozen group denominator differs")
    for relative, expected_hash in manifest.get("previous_manifests", {}).items():
        archive = (ROOT / relative).resolve()
        if not archive.is_relative_to(ROOT / "evaluation/heldout/history") or sha256(archive) != expected_hash:
            raise AssertionError("previous frozen manifest changed")
        prior = strict_json(archive.read_text(encoding="utf-8"))
        if prior["cases"] != cases or any(prior["files"][name] != manifest["files"][name]
                                         for name in ("evaluation/heldout/inputs.jsonl", "evaluation/heldout/labels.jsonl")):
            raise AssertionError("previous data/gold not preserved")
        if prior["version"] == manifest.get("unchanged_verifier_from") \
                and prior["files"]["evaluation/verifier.py"] != manifest["files"]["evaluation/verifier.py"]:
            raise AssertionError("accepted M2 oracle changed")
    return {"passed": True, "version": manifest["version"], "cases": 36,
            "groups": manifest["groups"], "hashed_files": len(manifest["files"]), "scored_case_runs": 0,
            "score_count_scope": "this read/hash-only check; no historical scoring claim",
            "prior_manifests_checked": len(manifest.get("previous_manifests", {})),
            "provenance": "authored synthetic holdout, inspectable by implementer" }

