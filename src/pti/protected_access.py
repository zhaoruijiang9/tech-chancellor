"""Task-scoped, path-scoped read-only authorization validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class AuthorizationDenied(ValueError):
    pass


def validate_authorization(
    authorization_path: str | Path,
    *,
    capability: str,
    target_path: str | Path,
    purpose: str,
    output_path: str | Path,
) -> dict[str, str]:
    path = Path(authorization_path).resolve()
    if not path.is_file():
        raise AuthorizationDenied("authorization receipt is missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationDenied("authorization receipt is unreadable") from exc
    required = ("capability", "target_path", "access_mode", "purpose", "output_boundary", "task_id", "expires_at", "nonce", "authorization_source")
    if any(not str(data.get(key, "")).strip() for key in required):
        raise AuthorizationDenied("authorization receipt is incomplete")
    target = Path(target_path).resolve()
    authorized_target = Path(str(data["target_path"])).resolve()
    output = Path(output_path).resolve()
    if str(data["capability"]) != capability or target != authorized_target:
        raise AuthorizationDenied("authorization is not scoped to this capability and path")
    if data["access_mode"] != "READ_ONLY" or data["purpose"] != purpose:
        raise AuthorizationDenied("authorization is not read-only architecture analysis")
    if data["output_boundary"] != "OUTSIDE_TARGET_PROJECT" or output == target or str(output).lower().startswith(str(target).lower() + "\\"):
        raise AuthorizationDenied("output must remain outside the protected project")
    if data["authorization_source"] != "DIRECT_USER_TASK_AUTHORIZATION":
        raise AuthorizationDenied("authorization source is not a direct current-task authorization")
    try:
        expires = datetime.fromisoformat(str(data["expires_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorizationDenied("authorization expiry is invalid") from exc
    if expires <= datetime.now(timezone.utc):
        raise AuthorizationDenied("authorization has expired")
    if len(str(data["nonce"])) < 16:
        raise AuthorizationDenied("authorization nonce is too short")
    return {key: str(data[key]) for key in required}
