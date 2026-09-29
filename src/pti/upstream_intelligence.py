from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .capability_intelligence import CapabilityStore
from .github_api import GitHubClient, RequestBudget


CADENCE_DAYS = {
    "USED": 3,
    "AVAILABLE": 3,
    "METHOD_SOURCE": 7,
    "APPROVED_WAITING_VALIDATION": 7,
    "HUMAN_DECISION": 7,
    "VALIDATING": 7,
    "WATCHLIST": 14,
    "REJECTED": 30,
    "VALIDATION_FAILED": 30,
    "ARCHIVED": 90,
}
BLOCKER_TERMS = (
    "rollback", "pinning", "pinned", "isolation", "isolated",
    "credential", "sandbox", "offline", "self-host",
)
METHOD_TERMS = ("codex", "skill", "plugin", "workflow", "method", "process")


@dataclass(frozen=True)
class Fingerprint:
    head_sha: str | None
    release_tag: str | None
    release_published_at: str | None
    readme_sha: str | None
    repository_updated_at: str | None
    repository_pushed_at: str | None
    commit_message: str = ""
    release_notes: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Fingerprint":
        return cls(
            head_sha=row.get("current_head_sha"),
            release_tag=row.get("current_release_tag"),
            release_published_at=row.get("current_release_published_at"),
            readme_sha=row.get("current_readme_sha"),
            repository_updated_at=row.get("current_repository_updated_at"),
            repository_pushed_at=row.get("current_repository_pushed_at"),
        )


class MonitorFailure(Exception):
    def __init__(self, failure_class: str, code: str):
        super().__init__(code)
        self.failure_class = failure_class
        self.code = code


def classify_change(old: Fingerprint, new: Fingerprint, state: str) -> dict[str, Any]:
    changed_parts = []
    for part in ("head_sha", "release_tag", "readme_sha"):
        if getattr(old, part) != getattr(new, part):
            changed_parts.append(part.upper())
    if not changed_parts:
        return {"changed": False, "queue_review": False, "review_outcome": "REVIEW_STILL_VALID", "reason": "NO_CHANGE"}
    release_changed = "RELEASE_TAG" in changed_parts
    readme_changed = "README_SHA" in changed_parts
    text = (
        (new.commit_message if "HEAD_SHA" in changed_parts else "") + " " +
        (new.release_notes if release_changed else "")
    ).lower()
    relevant_failed = state == "VALIDATION_FAILED" and any(term in text for term in BLOCKER_TERMS)
    relevant_method = state == "METHOD_SOURCE" and any(term in text for term in METHOD_TERMS)
    queue_review = release_changed or (readme_changed and relevant_method) or relevant_failed
    if relevant_failed:
        outcome = "REVALIDATION_REQUIRED"
    elif relevant_method:
        outcome = "REVIEW_UPDATED"
    elif queue_review:
        outcome = "REVIEW_STILL_VALID"
    else:
        outcome = "NO_RELEVANT_CHANGE"
    return {
        "changed": True,
        "queue_review": queue_review,
        "review_outcome": outcome,
        "reason": ",".join(changed_parts),
    }


def _is_due(last_check: str | None, state: str, now: str) -> bool:
    if not last_check:
        return True
    try:
        last = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
        current = datetime.fromisoformat(now.replace("Z", "+00:00"))
        return (current - last).total_seconds() >= CADENCE_DAYS.get(state, 14) * 86400
    except ValueError:
        return True


def check_upstream(
    store: CapabilityStore,
    provider: Any,
    now: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc).isoformat()
    result = {
        "run_id": uuid.uuid4().hex[:16],
        "started_at": now,
        "completed_at": now,
        "status": "NO_CHANGE",
        "checked": 0,
        "skipped_not_due": 0,
        "baseline_captured": 0,
        "no_change": 0,
        "changes_detected": 0,
        "reviews_queued": 0,
        "failures": 0,
        "request_count": 0,
        "failure_class": None,
    }
    for source in store.list_monitor_sources():
        old_row = store.get_source_freshness(source["source_id"])
        if not force and old_row and old_row["last_check_status"] != "CHECK_FAILED" and not _is_due(
            old_row["last_upstream_check"], source["monitoring_state"], now
        ):
            result["skipped_not_due"] += 1
            continue
        old = Fingerprint.from_row(old_row) if old_row and old_row.get("current_head_sha") else None
        try:
            current = provider.fetch(source, old)
            if not isinstance(current, Fingerprint) or not current.head_sha:
                raise MonitorFailure("SYSTEM", "INVALID_FINGERPRINT")
            result["checked"] += 1
            if old is None:
                store.record_source_baseline(source["source_id"], current, now)
                result["baseline_captured"] += 1
            else:
                change = classify_change(old, current, source["monitoring_state"])
                if change["changed"]:
                    result["changes_detected"] += 1
                else:
                    result["no_change"] += 1
                if store.record_source_check(
                    source["source_id"], current, now,
                    change["changed"], change["queue_review"],
                    change["review_outcome"], change["reason"],
                    (current.commit_message + "\n" + current.release_notes).strip(),
                ):
                    result["reviews_queued"] += 1
        except MonitorFailure as error:
            result["failures"] += 1
            result["failure_class"] = error.failure_class
            store.record_source_failure(source["source_id"], now, error.failure_class, error.code)
        except Exception as error:
            result["failures"] += 1
            result["failure_class"] = "SYSTEM"
            store.record_source_failure(source["source_id"], now, "SYSTEM", type(error).__name__)
    result["request_count"] = int(getattr(provider, "request_count", 0))
    result["status"] = (
        "FAILED" if result["failures"] and not result["checked"]
        else "PARTIAL_FAILURE" if result["failures"]
        else "CHANGE_DETECTED" if result["changes_detected"]
        else "BASELINE_CAPTURED" if result["baseline_captured"]
        else "NO_CHANGE"
    )
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    store.record_upstream_run(result)
    return result


class GitHubFingerprintProvider:
    def __init__(self, budget: int = 55, client: GitHubClient | None = None):
        self.client = client or GitHubClient(budget=RequestBudget(budget))

    @property
    def request_count(self) -> int:
        return self.client.budget.used

    @staticmethod
    def _unwrap(result: Any, optional_missing: bool = False) -> Any:
        failure = result.failure
        if failure is None:
            return result.raw
        if optional_missing and failure.code == "HTTP_404":
            return None
        if failure.code in {"HTTP_403", "HTTP_429", "REQUEST_BUDGET_EXCEEDED"}:
            failure_class = "RATE_LIMIT"
        elif failure.code in {"NETWORK_ERROR", "HTTP_502", "HTTP_503", "HTTP_504"}:
            failure_class = "NETWORK"
        elif failure.code in {"HTTP_401", "HTTP_404"}:
            failure_class = "UNAVAILABLE"
        else:
            failure_class = "SYSTEM"
        raise MonitorFailure(failure_class, failure.code)

    def fetch(self, source: dict[str, Any], previous: Fingerprint | None) -> Fingerprint:
        owner, repo = source["canonical_name"].split("/", 1)
        repository_result = self.client.get_repository(owner, repo)
        repository = self._unwrap(repository_result)
        if not repository or int(repository.get("id", -1)) != source["github_repository_id"]:
            raise MonitorFailure("SYSTEM", "REPOSITORY_ID_MISMATCH")
        updated_at = repository.get("updated_at")
        pushed_at = repository.get("pushed_at")
        if previous and updated_at == previous.repository_updated_at and pushed_at == previous.repository_pushed_at:
            return previous
        commits = self._unwrap(self.client.get_latest_commit(owner, repo))
        if not isinstance(commits, list) or not commits:
            raise MonitorFailure("UNAVAILABLE", "HEAD_MISSING")
        head = commits[0]
        release = self._unwrap(self.client.get_latest_release(owner, repo), optional_missing=True)
        readme_sha = previous.readme_sha if previous else None
        if source["monitoring_state"] in {"METHOD_SOURCE", "VALIDATION_FAILED"}:
            readme = self._unwrap(self.client.get_readme(owner, repo), optional_missing=True)
            readme_sha = readme.get("sha") if isinstance(readme, dict) else None
        return Fingerprint(
            head_sha=head.get("sha"),
            release_tag=release.get("tag_name") if isinstance(release, dict) else None,
            release_published_at=release.get("published_at") if isinstance(release, dict) else None,
            readme_sha=readme_sha,
            repository_updated_at=updated_at,
            repository_pushed_at=pushed_at,
            commit_message=(head.get("commit") or {}).get("message", "")[:1200],
            release_notes=(release.get("body") or "")[:4000] if isinstance(release, dict) else "",
        )
