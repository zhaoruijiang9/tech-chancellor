"""Generic guidance plus optional, ignored user-specific overrides."""

import json
from pathlib import Path


def load_usage(root: str | Path) -> dict:
    root = Path(root)
    result = {}
    for name in ("capability_usage_defaults.json", "human_capability_usage.json"):
        path = root / "config" / name
        if path.is_file():
            for repository, fields in json.loads(path.read_text(encoding="utf-8")).items():
                result[repository] = {**result.get(repository, {}), **fields}
    return result
