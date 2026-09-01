import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _write(root: Path, filename: str, payload: bytes, manifest: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / filename
    path.write_bytes(payload)
    manifest = {**manifest, "path": str(path), "sha256": hashlib.sha256(payload).hexdigest(),
                "download_time": datetime.now(timezone.utc).isoformat()}
    path.with_suffix(path.suffix + ".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def quarantine_text_asset(root: str | Path, source_url: str, text: str, repository: dict[str, Any], decision: str) -> dict[str, Any]:
    if decision not in {"WATCH", "REFERENCE_ONLY", "USER_REVIEW_RECOMMENDED", "CANDIDATE_FOR_QUARANTINE"}:
        raise ValueError("quarantine requires a reviewed non-executing decision")
    identity = re.sub(r"[^A-Za-z0-9._-]+", "-", str(repository.get("canonical_owner_repo") or "asset"))
    return _write(Path(root), identity + "--asset.md", text.encode("utf-8"), {
        "source_url": source_url, "github_repository_id": repository.get("github_repository_id"),
        "owner_repo": repository.get("canonical_owner_repo"), "asset_type": "NON_EXECUTABLE_AI_ASSET",
        "license": repository.get("license_spdx"), "reason": "static review candidate", "decision": decision,
    })


def quarantine_public_repo_archive(root: str | Path, source_url: str, repository_id: int, owner_repo: str, commit_sha: str, payload: bytes) -> dict[str, Any]:
    safe_name = owner_repo.replace("/", "--") + ".archive"
    return _write(Path(root), safe_name, payload, {
        "source_url": source_url, "github_repository_id": repository_id, "owner_repo": owner_repo,
        "commit_sha": commit_sha, "asset_type": "PUBLIC_REPOSITORY_ARCHIVE", "reason": "static review only",
        "decision": "CANDIDATE_FOR_QUARANTINE",
    })
