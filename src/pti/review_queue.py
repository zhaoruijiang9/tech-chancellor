import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .models import RepositoryRecord

REVIEW_REASONS = ("USER_REQUESTED", "FIRST_REVIEW", "MATERIAL_EVIDENCE_CHANGED", "WATCH_DUE")


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


def material_evidence_projection(record: RepositoryRecord, capability_sections: list[str] | None = None,
                                 major_release_capability_change: str = "",
                                 lifecycle_state: str = "ACTIVE") -> dict[str, Any]:
    return {"description": _clean(record.description),
            "topics": sorted({_clean(topic) for topic in record.topics if _clean(topic)}),
            "capability_readme_sections": sorted({_clean(section) for section in (capability_sections or []) if _clean(section)}),
            "major_release_capability_change": _clean(major_release_capability_change),
            "lifecycle_state": _clean(lifecycle_state) or "active"}


def fingerprint(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ReviewEligibility:
    reason: str | None
    observation_changed: bool
    material_changed: bool


def review_eligibility(current: RepositoryRecord, previous: RepositoryRecord | None,
                       *, user_requested: bool = False, material_changed: bool = False,
                       watch_due: bool = False) -> ReviewEligibility:
    current_material = current.material_evidence_fingerprint or fingerprint(material_evidence_projection(current))
    if previous is None or not previous.previous_decision:
        return ReviewEligibility("USER_REQUESTED" if user_requested else "FIRST_REVIEW", True, True)
    previous_material = previous.material_evidence_fingerprint or fingerprint(material_evidence_projection(previous))
    material_changed = material_changed or current_material != previous_material
    observation_changed = (current.description != previous.description or sorted(current.topics) != sorted(previous.topics)
                           or current.stars != previous.stars or current.pushed_at != previous.pushed_at
                           or current.release_state != previous.release_state)
    reason = "USER_REQUESTED" if user_requested else "MATERIAL_EVIDENCE_CHANGED" if material_changed else "WATCH_DUE" if watch_due else None
    return ReviewEligibility(reason, observation_changed, material_changed)


def should_enqueue(reason: str | None, existing_reason: str | None = None) -> bool:
    return reason in REVIEW_REASONS and existing_reason != reason


def allocate_review_slots(evaluations: list[Any], limit: int = 3) -> list[Any]:
    eligible = [item for item in evaluations if getattr(item, "review_reason", "") in REVIEW_REASONS
                and getattr(item, "semantic_review", None)]
    return sorted(eligible, key=lambda item: (
        0 if item.review_reason == "USER_REQUESTED" else 1,
        -int(getattr(item, "total", 0)),
        -int(getattr(item.candidate, "current_need", 0)),
        getattr(item.candidate, "name", "")))[:max(0, limit)]
