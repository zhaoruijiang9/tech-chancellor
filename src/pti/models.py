from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class EnrichmentEvidence:
    level: str
    readme: str = ""
    release: dict[str, Any] | None = None
    latest_commit: dict[str, Any] | None = None
    tree_paths: list[str] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "readme": self.readme, "release": self.release,
                "latest_commit": self.latest_commit, "tree_paths": self.tree_paths,
                "failures": self.failures}


@dataclass
class RepositoryRecord:
    github_repository_id: int
    canonical_owner_repo: str
    url: str
    first_seen: str = field(default_factory=utc_now)
    last_seen: str = field(default_factory=utc_now)
    stars: int = 0
    forks: int = 0
    pushed_at: str | None = None
    release_state: str | None = None
    license_spdx: str | None = None
    is_fork: bool = False
    parent_repository_id: int | None = None
    previous_score: float | None = None
    previous_decision: str | None = None
    previous_routes: list[str] = field(default_factory=list)
    rejection_reason: str | None = None
    review_after: str | None = None
    content_fingerprint: str | None = None
    description: str = ""
    topics: list[str] = field(default_factory=list)
    default_branch: str | None = None
    observation_fingerprint: str | None = None
    material_evidence_fingerprint: str | None = None
    material_evidence_projection: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "github_repository_id": self.github_repository_id,
            "canonical_owner_repo": self.canonical_owner_repo,
            "url": self.url,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "stars": self.stars,
            "forks": self.forks,
            "pushed_at": self.pushed_at,
            "release_state": self.release_state,
            "license_spdx": self.license_spdx,
            "is_fork": self.is_fork,
            "parent_repository_id": self.parent_repository_id,
            "previous_score": self.previous_score,
            "previous_decision": self.previous_decision,
            "previous_routes": self.previous_routes,
            "rejection_reason": self.rejection_reason,
            "review_after": self.review_after,
            "content_fingerprint": self.content_fingerprint,
            "description": self.description,
            "topics": self.topics,
            "default_branch": self.default_branch,
            "observation_fingerprint": self.observation_fingerprint,
            "material_evidence_fingerprint": self.material_evidence_fingerprint,
            "material_evidence_projection": self.material_evidence_projection,
        }
