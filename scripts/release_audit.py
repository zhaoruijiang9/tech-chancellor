"""Bounded publication checks; reports locations, never matched secret values."""

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


SECRET_PATTERNS = {
    "GITHUB_TOKEN": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})"),
    "API_TOKEN": re.compile(r"(?:sk-(?:proj-|ant-)?[A-Za-z0-9_-]{28,}|AKIA[A-Z0-9]{16}|npm_[A-Za-z0-9]{30,})"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AUTHORIZATION_VALUE": re.compile(r"(?i)(?:bearer\s+|(?:api[_-]?key|password|access[_-]?token|refresh[_-]?token)[\"']?\s*[:=]\s*[\"'])[A-Za-z0-9_./+\-=]{24,}"),
}
LOCAL_CONFIGS = {
    "config/activation_readiness_audit.json", "config/human_capability_usage.json",
    "config/stage_b.json", "config/local_capability_profile.json",
}
RUNTIME_PREFIXES = ("state/", "quarantine/", "managed_capabilities/", "user_artifacts/",
                    "chancellor_pending/", "inbox/", "library/generated/")
RUNTIME_KEYS = {"activation_state", "enabled", "real_use_at", "owner_approval",
                "audited_at", "managed_install_path", "usage_receipt", "approved_by"}


def classify(path):
    if path in {"config/stage_b.json", "config/local_capability_profile.json"}:
        return "MACHINE_SPECIFIC_CONFIG"
    if Path(path).name.lower() in {"auth.json", ".env", "credentials.json", "cookies.txt"}:
        return "SECRET_CREDENTIAL"
    if path in LOCAL_CONFIGS or path.startswith(RUNTIME_PREFIXES) or path.endswith(".local.json"):
        return "PERSONAL_RUNTIME"
    if path.endswith((".example.json", ".schema.json")) or path.startswith(("tests/fixtures/", "templates/")):
        return "PUBLIC_TEMPLATE_EXAMPLE"
    if path.startswith("docs/images/") or path.endswith((".png", ".jpg", ".webp")):
        return "GENERATED_PUBLIC_ASSET"
    if path.endswith(".md") or path == "LICENSE":
        return "PUBLIC_DOCUMENTATION"
    return "PRODUCT_SOURCE"


def scan_text(text):
    return [{"kind": kind, "line": text.count("\n", 0, match.start()) + 1}
            for kind, pattern in SECRET_PATTERNS.items() for match in pattern.finditer(text)]


def config_leaks(path, text):
    if not path.startswith("config/") or path.endswith(".example.json"):
        return []
    try:
        data = json.loads(text)
    except ValueError:
        return []
    found = []
    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in RUNTIME_KEYS:
                    found.append(key)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and any(word in value for word in ("已获", "已批准", "原有人工决策", "GLOBAL_CODEX_CONTROLLED")):
            found.append("OWNER_STATE_TEXT")
    walk(data)
    return sorted(set(found))


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def audit(root, history_base="v0.1.0", revision=None):
    root = Path(root)
    entries = git(root, "ls-tree", "-rz", revision).split(b"\0") if revision else git(root, "ls-files", "-sz").split(b"\0")
    files = []
    for entry in entries:
        if not entry:
            continue
        header, path = entry.split(b"\t", 1)
        files.append((path.decode("utf-8"), header.split()[2 if revision else 1].decode()))
    findings, privacy = [], []
    categories = Counter({name: 0 for name in ("PRODUCT_SOURCE", "PUBLIC_TEMPLATE_EXAMPLE",
        "PUBLIC_DOCUMENTATION", "GENERATED_PUBLIC_ASSET", "PERSONAL_RUNTIME",
        "MACHINE_SPECIFIC_CONFIG", "SECRET_CREDENTIAL")})
    for path, blob in files:
        category = classify(path)
        categories[category] += 1
        if category in {"PERSONAL_RUNTIME", "MACHINE_SPECIFIC_CONFIG", "SECRET_CREDENTIAL"}:
            privacy.append({"path": path, "kind": category})
        content = git(root, "cat-file", "blob", blob)
        if b"\0" in content[:8000]:
            continue
        text = content.decode("utf-8", errors="replace")
        findings.extend({"path": path, **item} for item in scan_text(text))
        privacy.extend({"path": path, "kind": key} for key in config_leaks(path, text))
    objects = git(root, "rev-list", "--objects", f"{history_base}..{revision or 'HEAD'}").decode("utf-8").splitlines()
    historical = []
    for entry in objects:
        blob, _, path = entry.partition(" ")
        if git(root, "cat-file", "-t", blob).strip() != b"blob":
            continue
        content = git(root, "cat-file", "blob", blob)
        if b"\0" in content[:8000]:
            continue
        historical.extend({"path": path, "blob": blob, **item}
                          for item in scan_text(content.decode("utf-8", errors="replace")))
    return {"status": "PASS" if not findings and not historical and not privacy else "BLOCKED",
            "tracked_count": len(files), "categories": dict(categories),
            "tree_secret_findings": findings, "history_secret_findings": historical,
            "runtime_findings": privacy, "history_object_count": len(objects),
            "classification": [{"path": path, "category": classify(path)} for path, _ in files]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--revision")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.root, revision=args.revision)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(serialized, encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "classification"}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
