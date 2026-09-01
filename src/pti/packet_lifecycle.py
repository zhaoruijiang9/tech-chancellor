import json
import time
from pathlib import Path


def _is_packet(path: Path) -> bool:
    if path.suffix.lower() != ".json" or ".processed" in path.stem or ".processing" in path.stem:
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    identity = payload.get("repository_identity") if isinstance(payload, dict) else None
    return (payload.get("status") in {"PENDING_CODEX_REVIEW", "FAILED_RETRYABLE"}
            and isinstance(identity, dict) and identity.get("github_repository_id") is not None)


def recover_stale_processing(root: str | Path, max_age_seconds: int = 900) -> list[Path]:
    root = Path(root)
    recovered = []
    now = time.time()
    for path in root.glob("*.processing.json"):
        if now - path.stat().st_mtime < max_age_seconds:
            continue
        target = path.with_name(path.name.replace(".processing.json", ".json"))
        if not target.exists():
            path.rename(target)
            recovered.append(target)
    return recovered


def list_active_pending_packets(root: str | Path) -> list[Path]:
    root = Path(root)
    recover_stale_processing(root)
    return sorted(path for path in root.glob("*.json")
                  if _is_packet(path) and not path.with_name(path.stem + ".processed.json").exists())


def active_pending_count(root: str | Path) -> int:
    return len(list_active_pending_packets(root))


def claim_packet(path: str | Path) -> Path:
    path = Path(path)
    target = path.with_name(path.name.replace(".json", ".processing.json"))
    path.rename(target)
    return target


def complete_packet(path: str | Path) -> Path:
    path = Path(path)
    target = path.with_name(path.name.replace(".processing.json", ".processed.json"))
    if target.exists():
        path.unlink()
    else:
        path.rename(target)
    return target


def retry_packet(path: str | Path) -> Path:
    path = Path(path)
    target = path.with_name(path.name.replace(".processing.json", ".json"))
    if not target.exists():
        path.rename(target)
    return target
