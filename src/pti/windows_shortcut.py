from __future__ import annotations

import subprocess
from pathlib import Path


def install_desktop_shortcut(root: str | Path) -> dict[str, str]:
    project_root = Path(root).resolve()
    script = project_root / "scripts" / "install_shortcut.ps1"
    if not script.is_file():
        raise FileNotFoundError(f"shortcut installer not found: {script}")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-ProjectRoot",
            str(project_root),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    shortcut_path = completed.stdout.strip().splitlines()[-1]
    return {"status": "SHORTCUT_CREATED", "path": shortcut_path}
