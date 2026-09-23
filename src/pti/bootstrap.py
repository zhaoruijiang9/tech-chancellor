import json
from pathlib import Path
from typing import Any

from .storage import Database


RUNTIME_DIRECTORIES = (
    "state",
    "inbox",
    "chancellor_pending",
    "reports",
    "library/generated",
    "quarantine",
    "user_artifacts",
)


def initialize_project(root: str | Path, config_path: str | Path, profile_path: str | Path) -> dict[str, Any]:
    """Create the local runtime shape and verify the shipped JSON inputs."""
    root = Path(root).resolve()
    config_path = Path(config_path).resolve()
    profile_path = Path(profile_path).resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"discovery config not found: {config_path}")
    if not profile_path.is_file():
        raise FileNotFoundError(f"capability profile not found: {profile_path}")
    json.loads(config_path.read_text(encoding="utf-8"))
    json.loads(profile_path.read_text(encoding="utf-8"))
    created = []
    for relative in RUNTIME_DIRECTORIES:
        directory = root / relative
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(relative)
    db_path = root / "state" / "intelligence.db"
    Database(db_path).initialize()
    return {
        "status": "INITIALIZED",
        "root": str(root),
        "database": str(db_path),
        "created_directories": created,
        "config": str(config_path),
        "capability_profile": str(profile_path),
    }
