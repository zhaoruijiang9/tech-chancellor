import json
from pathlib import Path


def analyze_tree(root: str | Path) -> dict[str, object]:
    root = Path(root)
    findings: set[str] = set()
    files: list[str] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            findings.add("symlink")
            continue
        if not path.is_file() or ".git" in path.parts:
            continue
        if len(files) >= 3000:
            raise ValueError("static review file limit exceeded")
        files.append(str(path.relative_to(root)))
        if path.stat().st_size > 2_000_000:
            findings.add("oversized_file")
            continue
        if path.name == "package.json":
            try:
                package = json.loads(path.read_text(encoding="utf-8", errors="replace"))
                scripts = package.get("scripts", {})
                if any(name in scripts for name in ("install", "postinstall", "prepare")):
                    findings.add("postinstall")
            except json.JSONDecodeError:
                findings.add("malformed_manifest")
        text = path.read_text(encoding="utf-8", errors="replace")[:200000]
        lower = text.lower()
        if path.suffix.lower() in {".ps1", ".bat", ".cmd", ".sh"} or "subprocess." in lower or "os.system(" in lower:
            findings.add("powershell_or_shell")
        if "pip install" in lower or "npm install" in lower:
            findings.add("dependency_install_command")
        if "subprocess" in lower or "child_process" in lower:
            findings.add("process_spawn")
        if path.suffix.lower() in {".py", ".js", ".ts", ".ps1", ".sh", ".cmd", ".bat"}:
            if any(marker in lower for marker in ("os.getenv(", "os.environ[", "process.env.", "get-credential")):
                findings.add("credential_access")
            if any(marker in lower for marker in ("new-service", "sc.exe create", "systemctl enable")):
                findings.add("service_install")
            if any(marker in lower for marker in ("start-process -verb runas", "sudo ", "runas.exe")):
                findings.add("privilege_escalation")
            if "d:\\money" in lower or "protected-project" in lower:
                findings.add("protected_path")
    return {"files": sorted(files), "findings": sorted(findings), "execution_performed": False}
