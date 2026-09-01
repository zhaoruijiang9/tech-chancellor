from dataclasses import dataclass, field
from typing import Any


DOMAINS = {
    "AI_AGENT", "AI_EXPERIENCE", "QUANT_DATA", "PRODUCTIVITY", "BUSINESS_MONEY",
    "RESEARCH_LEARNING", "WATCHLIST", "CHANGE_SIGNAL", "GENERAL",
}
DECISIONS = {
    "IGNORE", "ARCHIVE", "REFERENCE_ONLY", "REVIEW_LATER",
    "CANDIDATE_FOR_QUARANTINE", "USER_REVIEW_RECOMMENDED",
}


@dataclass
class Candidate:
    name: str
    description: str
    domains: list[str]
    stars: int
    duplication: int
    current_need: int
    expected_value: int
    security_risk: int
    readme: str = ""
    url: str = ""
    github_repository_id: int | None = None


@dataclass
class Evaluation:
    candidate: Candidate
    score_components: dict[str, int]
    total: int
    decision: str = "REVIEW_LATER"
    priority: str = "SECONDARY"
    primary_route: str = "GENERAL"
    secondary_routes: list[str] = field(default_factory=list)
    capability_delta: dict[str, str] = field(default_factory=dict)
    incremental_value: str = ""
    evidence: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    reason_code: str = ""
    review_after: str | None = None
    recommended_next_action: str = "reference"
    system_instruction_effect: str = "IGNORED_AS_UNTRUSTED_INPUT"
    semantic_review: dict[str, Any] = field(default_factory=dict)
    source_query: str = ""
    source_group: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository": {
                "name": self.candidate.name,
                "url": self.candidate.url,
                "description": self.candidate.description,
                "github_repository_id": self.candidate.github_repository_id,
            },
            "decision": self.decision,
            "primary_route": self.primary_route,
            "secondary_routes": self.secondary_routes,
            "score_components": self.score_components,
            "score_total": self.total,
            "priority": self.priority,
            "capability_delta": self.capability_delta,
            "incremental_value": self.incremental_value,
            "evidence": self.evidence,
            "risk_flags": self.risk_flags,
            "confidence": self.confidence,
            "reason_code": self.reason_code,
            "review_after": self.review_after,
            "recommended_next_action": self.recommended_next_action,
            "semantic_review": self.semantic_review,
            "source_query": self.source_query,
            "source_group": self.source_group,
        }


def _relevance(candidate: Candidate) -> int:
    return 5 if any(domain in {"AI_AGENT", "AI_EXPERIENCE", "QUANT_DATA"} for domain in candidate.domains) else 3


def score_candidate(candidate: Candidate, capability_profile: dict[str, Any]) -> Evaluation:
    maturity = 5 if candidate.stars >= 10000 else 3 if candidate.stars >= 1000 else 2
    novelty = 5 if candidate.stars < 1000 else 3
    interest = 5 if any(domain in {"AI_AGENT", "AI_EXPERIENCE", "QUANT_DATA", "BUSINESS_MONEY"} for domain in candidate.domains) else 3
    components = {
        "RELEVANCE": _relevance(candidate),
        "NOVELTY": novelty,
        "CURRENT_NEED_MATCH": candidate.current_need,
        "EXPECTED_VALUE": candidate.expected_value,
        "MATURITY": maturity,
        "MAINTENANCE": 3,
        "USER_INTEREST": interest,
        "INTEGRATION_COST": 2,
        "SECURITY_RISK": candidate.security_risk,
        "DUPLICATION": candidate.duplication,
    }
    total = (
        2 * components["RELEVANCE"] + components["NOVELTY"] + 2 * components["CURRENT_NEED_MATCH"]
        + 2 * components["EXPECTED_VALUE"] + components["MATURITY"] + components["MAINTENANCE"]
        + components["USER_INTEREST"] - components["INTEGRATION_COST"]
        - 2 * components["SECURITY_RISK"] - 2 * components["DUPLICATION"]
    )
    existing = capability_profile.get(candidate.domains[0], "UNKNOWN") if candidate.domains else "UNKNOWN"
    addition = candidate.description[:240] or "UNKNOWN"
    return Evaluation(
        candidate=candidate,
        score_components=components,
        total=total,
        primary_route=next((domain for domain in candidate.domains if domain in DOMAINS), "GENERAL"),
        capability_delta={"existing_capability": str(existing), "candidate_addition": addition,
                          "replacement_potential": "UNKNOWN", "incremental_value": "PENDING_REVIEW"},
        incremental_value="Requires comparison with the local capability profile.",
        evidence=[f"stars={candidate.stars}", f"domains={','.join(candidate.domains)}"],
        risk_flags=["UNTRUSTED_EXTERNAL_INPUT"],
    )


def decide_candidate(evaluation: Evaluation) -> Evaluation:
    candidate = evaluation.candidate
    if candidate.security_risk >= 4:
        evaluation.decision = "USER_REVIEW_RECOMMENDED"
        evaluation.priority = "SECONDARY"
        evaluation.reason_code = "HIGH_SECURITY_RISK"
        evaluation.recommended_next_action = "manual_security_review"
    elif candidate.duplication >= 4 and candidate.current_need <= 2:
        evaluation.decision = "IGNORE"
        evaluation.priority = "ARCHIVE"
        evaluation.reason_code = "LOW_INCREMENTAL_VALUE"
        evaluation.recommended_next_action = "archive"
    elif evaluation.total >= 35:
        evaluation.decision = "USER_REVIEW_RECOMMENDED"
        evaluation.priority = "HIGH_PRIORITY"
        evaluation.reason_code = "HIGH_EVIDENCE_VALUE"
        evaluation.recommended_next_action = "review_candidate"
    elif evaluation.total >= 24:
        evaluation.decision = "REVIEW_LATER"
        evaluation.priority = "SECONDARY"
        evaluation.reason_code = "PROMISING_BUT_NOT_URGENT"
    elif evaluation.total >= 14:
        evaluation.decision = "REFERENCE_ONLY"
        evaluation.priority = "ARCHIVE"
        evaluation.reason_code = "LOW_PRIORITY_REFERENCE"
    else:
        evaluation.decision = "ARCHIVE"
        evaluation.priority = "ARCHIVE"
        evaluation.reason_code = "LOW_SCORE"
    return evaluation
