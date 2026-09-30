"""Data-only capability invocation and production-consumer binding."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from .activation_worker import SHA, search_active_index


REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]+$")
SUPPORTED_ADAPTERS = {"READ_ONLY_MARKDOWN_INDEX": "pti.capability_invocation.invoke_index"}


def normalize_github_link(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com" or parsed.port or parsed.username:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or not all(REPOSITORY_PART.fullmatch(part) for part in parts[:2]):
        return None
    return f"{parts[0]}/{parts[1]}"


def relevant_to_intent(binding: dict, intent: str, link_name: str, record) -> bool:
    rules = binding.get("intent_rules") or {}
    required = rules.get(intent, {}).get("required_any") or []
    if not required:
        return True
    text = " ".join((link_name, record.canonical_owner_repo, record.description,
                     " ".join(record.topics))).lower()
    return any(str(signal).lower() in text for signal in required)


def active_bindings(db, root: str | Path, contracts: list[dict], consumer: str) -> list[dict]:
    root = Path(root).resolve()
    bound = []
    for contract in contracts:
        if contract.get("consumer") != consumer or contract.get("adapter_type") not in SUPPORTED_ADAPTERS:
            continue
        if contract.get("invoke_entrypoint") != SUPPORTED_ADAPTERS[contract["adapter_type"]]:
            continue
        if not contract.get("capability_id") or not contract.get("implementation_id") or not contract.get("intent_terms"):
            continue
        try:
            timeout = int(contract.get("timeout_seconds", 0))
            budgets = [int(contract[key]) for key in
                       ("max_raw_results", "max_normalized_candidates", "max_new_candidates")]
        except (KeyError, TypeError, ValueError):
            continue
        if not 1 <= timeout <= 15 or any(value < 1 for value in budgets):
            continue
        with db._connect() as connection:
            rows = connection.execute("""SELECT i.implementation_id,s.github_repository_id,a.activation_state
                FROM implementation_capabilities m JOIN capability_implementations i USING(implementation_id)
                JOIN capability_sources s USING(source_id)
                JOIN activation_records a ON a.github_repository_id=s.github_repository_id
                WHERE m.capability_id=? AND i.implementation_id=? AND EXISTS (
                    SELECT 1 FROM personal_states p WHERE p.subject_type='IMPLEMENTATION'
                    AND p.subject_id=i.implementation_id AND p.state IN ('AVAILABLE','USED'))
                AND a.activation_state IN ('TRIAL_ENABLED','USED')
                AND a.isolated_test_status='PASS' AND a.rollback_status='READY'
                ORDER BY i.implementation_id""", (contract["capability_id"], contract["implementation_id"])).fetchall()
        for row in rows:
            repository_id = int(row["github_repository_id"])
            pointer = root / "managed_capabilities" / f"repo-{repository_id}" / "active.json"
            try:
                sha = json.loads(pointer.read_text(encoding="utf-8"))["sha"]
                readme = pointer.parent / "versions" / sha / "README.md"
                if not SHA.fullmatch(sha) or not readme.is_file():
                    continue
            except (OSError, KeyError, ValueError, TypeError):
                continue
            bound.append({**contract, "implementation_id": row["implementation_id"],
                          "repository_id": repository_id, "pinned_sha": sha})
    return bound


def invoke_index(root: str | Path, binding: dict, radar_queries: list[str]) -> dict:
    deadline = time.monotonic() + int(binding["timeout_seconds"])
    terms = [term for term in binding["intent_terms"] if any(term.lower() in query.lower() for query in radar_queries)]
    raw_limit = min(max(int(binding["max_raw_results"]), 1), 20)
    raw = []
    seen_urls = set()
    for term in terms[:5]:
        if time.monotonic() > deadline:
            raise TimeoutError("CAPABILITY_INVOCATION_TIMEOUT")
        matches = search_active_index(root, term, binding["repository_id"])
        if time.monotonic() > deadline:
            raise TimeoutError("CAPABILITY_INVOCATION_TIMEOUT")
        for item in matches:
            if item["url"] not in seen_urls:
                raw.append({**item, "intent": term})
                seen_urls.add(item["url"])
            if len(raw) >= raw_limit:
                break
        if len(raw) >= raw_limit:
            break
    normalized = []
    seen_repos = set()
    for item in raw:
        owner_repo = normalize_github_link(item["url"])
        if owner_repo and owner_repo.lower() not in seen_repos:
            normalized.append({"owner_repo": owner_repo, "name": item["name"], "intent": item["intent"]})
            seen_repos.add(owner_repo.lower())
        if len(normalized) >= min(max(int(binding["max_normalized_candidates"]), 1), 10):
            break
    return {"raw_count": len(raw), "normalized": normalized, "intents": terms[:5]}


def invocation_health(db, implementation_id: str) -> dict:
    with db._connect() as connection:
        rows = connection.execute("""SELECT success,invoked_at FROM capability_invocations
            WHERE implementation_id=? ORDER BY id DESC""", (implementation_id,)).fetchall()
    consecutive = 0
    for row in rows:
        if row["success"]:
            break
        consecutive += 1
    return {
        "last_successful_invocation": next((row["invoked_at"] for row in rows if row["success"]), None),
        "last_failed_invocation": next((row["invoked_at"] for row in rows if not row["success"]), None),
        "consecutive_failures": consecutive,
    }
