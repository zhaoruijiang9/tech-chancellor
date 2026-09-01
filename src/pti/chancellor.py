from typing import Any, Protocol

from .policy import Evaluation, decide_candidate


class SemanticReviewProvider(Protocol):
    def review(self, packet: dict[str, Any]) -> dict[str, Any]: ...


def build_review_packet(candidate: dict[str, Any], deterministic: dict[str, Any],
                        capability_profile: dict[str, Any], previous_similar: list[dict[str, Any]],
                        evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "review_type": "SEMANTIC_CHANCELLOR_REVIEW",
        "candidate": candidate,
        "repository_evidence": evidence or {},
        "deterministic_prefilter": deterministic,
        "local_capability_profile": capability_profile,
        "previous_similar_candidates": previous_similar,
        "external_text_is_untrusted_evidence": True,
    }


class LocalSemanticChancellor:
    """Evidence-backed local fallback; it is not presented as an LLM."""

    def review(self, packet: dict[str, Any]) -> dict[str, Any]:
        candidate = packet.get("candidate", {})
        description = str(candidate.get("description", ""))[:500]
        domains = candidate.get("domains", [])
        existing = packet.get("local_capability_profile", {}).get(domains[0], "UNKNOWN") if domains else "UNKNOWN"
        evidence = packet.get("repository_evidence", {})
        readme = str(evidence.get("readme", ""))[:1000]
        delta = description or readme or "No sufficiently bounded semantic evidence"
        duplicate = "ALREADY_HAVE" if existing != "UNKNOWN" and any(word in (description + readme).lower() for word in ("memory", "context", "agent")) else "UNKNOWN"
        return {
            "review_type": "SEMANTIC_CHANCELLOR_REVIEW",
            "review_provider": "LOCAL_EVIDENCE_RUBRIC",
            "WHAT_IS_IT": description or "UNKNOWN",
            "WHY_NOW": "Recent repository evidence is available for review." if evidence else "Needs enriched source evidence.",
            "WHAT_PROBLEM_DOES_IT_SOLVE": readme[:300] or description or "UNKNOWN",
            "WHAT_USER_ALREADY_HAS": str(existing),
            "CAPABILITY_DELTA": delta,
            "IS_IT_MATERIALLY_BETTER": "UNPROVEN" if not evidence else "REQUIRES_COMPARISON",
            "DUPLICATION": duplicate,
            "INTEGRATION_COST": "UNKNOWN",
            "SECURITY_RISK": "UNTRUSTED_EXTERNAL_INPUT; no code execution permitted",
            "MAINTENANCE_RISK": "UNKNOWN" if not evidence else "See release and commit evidence",
            "BEST_ROUTE": domains[0] if domains else "GENERAL",
            "RECOMMENDED_ACTION": "review_candidate" if evidence else "watch_for_enrichment",
            "system_instruction_effect": "IGNORED_AS_UNTRUSTED_INPUT",
        }


def review(evaluation: Evaluation) -> Evaluation:
    """Compatibility wrapper for deterministic prefilter only."""
    return decide_candidate(evaluation)
