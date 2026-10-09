"""Bounded public-file inventory/syntax/path/credential/import/CI checks, not a security audit."""
import ast
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from agent.bridge import ROOT
from agent.protocol import strict_json

PUBLIC_ROOTS = ("agent", "evaluation", "fixtures", "java", "tests", "docs", "tools", ".github")
PUBLIC_TOP = {"dev.py", "README.md", "EVIDENCE.md", "ATTRIBUTION.md", "LICENSE", ".gitignore", ".gitattributes", "PUBLIC_FILES.json"}
ACTION_PINS = {"actions/checkout": "08c6903cd8c0fde910a37f88322edcfb5dd907a8",
               "actions/setup-python": "83679a892e2d95755f2dac6acb0bfd1e9ac5d548",
               "actions/setup-java": "0f481fcb613427c0f801b606911222b5b6f3083a"}


def discover_public(root=ROOT):
    root = Path(root)
    files = {name for name in PUBLIC_TOP if (root / name).is_file()}
    for folder in PUBLIC_ROOTS:
        for path in (root / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                files.add(path.relative_to(root).as_posix())
    return sorted(files)


def public_files(root=ROOT):
    root = Path(root).resolve()
    data = strict_json((root / "PUBLIC_FILES.json").read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "files"} or data["schema"] != 1 \
            or type(data["files"]) is not list or any(type(p) is not str for p in data["files"]):
        raise ValueError("invalid public inventory")
    files = data["files"]
    if files != sorted(set(files)) or files != discover_public(root):
        raise ValueError("public inventory differs from source; regenerate after intentional additions")
    for relative in files:
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative \
                or (len(path.parts) == 1 and relative not in PUBLIC_TOP) \
                or (len(path.parts) > 1 and path.parts[0] not in PUBLIC_ROOTS):
            raise ValueError("invalid public path: " + relative)
        target = root / relative
        if not target.resolve().is_relative_to(root) or any(p.is_symlink() for p in (target, *target.parents) if p.is_relative_to(root)):
            raise ValueError("public symlink or path escape: " + relative)
        if target.stat().st_size > 1_048_576 or target.suffix.lower() in {".class", ".jar", ".exe", ".dll", ".zip", ".pyc"}:
            raise ValueError("oversized/generated public file: " + relative)
    return files


def inspect_text(relative, text):
    problems = []
    personal = re.compile(r"(?i)(?:[A-Z]:[/\\](?:Users|Documents)[/\\]|/(?:Users|home)/[A-Za-z0-9_.-]+/)")
    credential = re.compile(r"(?:sk[-_](?:proj[-_])?[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,})")
    if personal.search(text) or ("Codex" + "Portfolios") in text:
        problems.append("personal path")
    if credential.search(text):
        problems.append("credential-shaped literal")
    if relative.endswith(".py"):
        tree = ast.parse(text, filename=relative)
        allowed = sys.stdlib_module_names | {"agent", "evaluation", "tests", "tools", "dev"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                modules = [node.module.split(".")[0]]
            else:
                continue
            if any(module not in allowed for module in modules):
                problems.append("undeclared runtime import")
    return problems


def check_public(root=ROOT):
    root = Path(root).resolve()
    files, issues = public_files(root), []
    if not PUBLIC_TOP <= set(files):
        raise ValueError("mandatory public documentation/license/build inventory missing")
    attributes = [line.strip() for line in (root / ".gitattributes").read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
    if attributes != ["* -text"]:
        raise ValueError("frozen bytes require the reviewed Git EOL policy")
    for relative in files:
        try:
            text = (root / relative).read_text(encoding="utf-8")
            issues.extend({"file": relative, "problem": p} for p in inspect_text(relative, text))
        except (UnicodeError, SyntaxError) as error:
            issues.append({"file": relative, "problem": type(error).__name__})
    if (root / ".git").exists():
        process = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                                 cwd=root, capture_output=True, text=True, timeout=5)
        if process.returncode:
            raise ValueError("Git public inventory command failed")
        extras = set(process.stdout.rstrip("\0").split("\0")) - set(files) - {""}
        issues.extend({"file": path, "problem": "not in public inventory"} for path in sorted(extras))
    ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    found = dict(re.findall(r"uses:\s*(actions/[\w-]+)@([0-9a-f]{40})", ci))
    if found != ACTION_PINS or len(re.findall(r"uses:", ci)) != len(ACTION_PINS):
        issues.append({"file": ".github/workflows/ci.yml", "problem": "actions require reviewed full pins"})
    if issues:
        raise ValueError(json.dumps({"public_check_failed": issues}, indent=2))
    return {"passed": True, "public_files": len(files), "python": sys.version.split()[0],
            "byte_preserving_git_attributes": True,
            "runtime_dependencies": "Python3.11 and Java17 only; no vendored libraries",
            "hosted_ci_executed": False,
            "limit": "Inventory and bounded pattern/syntax/import checks, not comprehensive secret detection or production security certification."}
