from dataclasses import dataclass, field
from typing import Any

from .github_api import ApiResult
from .models import RepositoryRecord
from .policy import Candidate, Evaluation, decide_candidate, score_candidate
from .chancellor import LocalSemanticChancellor, build_review_packet
from .storage import Database
from .review_queue import fingerprint, material_evidence_projection, review_eligibility


@dataclass
class DiscoveryRun:
    decisions: list[Evaluation] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    request_count: int = 0


def _candidate(record: RepositoryRecord, domain: str, historical: RepositoryRecord | None) -> Candidate:
    duplication = 5 if historical and historical.previous_decision in {"IGNORE", "ARCHIVE"} else 0
    return Candidate(
        name=record.canonical_owner_repo,
        description=record.description,
        domains=[domain],
        stars=record.stars,
        duplication=duplication,
        current_need=4 if domain in {"AI_AGENT", "AI_EXPERIENCE", "QUANT_DATA"} else 3,
        expected_value=4,
        security_risk=1,
        url=record.url,
        github_repository_id=record.github_repository_id,
    )


def run_discovery(config: dict[str, Any], client: Any, db: Database, capability_profile: dict[str, Any],
                  run_id: str | None = None) -> DiscoveryRun:
    result = DiscoveryRun()
    seen: set[int] = set()
    query_groups = config.get("query_groups", [])
    per_query_cap = int(config.get("per_query_cap", 5))
    total_cap = int(config.get("total_candidate_cap", 20))
    enrichment_level = str(config.get("enrichment_level", "STANDARD")).upper()
    enrichment_cap = int(config.get("enrichment_candidate_cap", 3))
    enriched = 0
    for group in query_groups:
        domain = group.get("domain", "GENERAL")
        for query in group.get("queries", []):
            if len(seen) >= total_cap:
                return result
            api_result: ApiResult = client.search_repositories(query, page=1, per_page=per_query_cap)
            result.request_count += 1
            if api_result.failure:
                result.failures.append({"code": "DISCOVERY_NOT_EVALUATED", "message": api_result.failure.message, "query": query})
                continue
            for record in api_result.items:
                if record.github_repository_id in seen:
                    continue
                seen.add(record.github_repository_id)
                historical = db.get_repository(record.github_repository_id)
                if historical and historical.previous_decision in {"IGNORE", "ARCHIVE"} and historical.pushed_at == record.pushed_at and historical.release_state == record.release_state:
                    continue
                evaluation = decide_candidate(score_candidate(_candidate(record, domain, historical), capability_profile))
                projection = material_evidence_projection(record)
                record.observation_fingerprint = fingerprint({"description": record.description, "topics": sorted(record.topics),
                                                               "stars": record.stars, "pushed_at": record.pushed_at,
                                                               "release_state": record.release_state})
                record.material_evidence_projection = projection
                record.material_evidence_fingerprint = fingerprint(projection)
                semantic_baseline = historical if historical and db.has_current_semantic_decision(record.github_repository_id) else None
                eligibility = review_eligibility(record, semantic_baseline)
                evaluation.review_reason = eligibility.reason if eligibility.reason else "OBSERVATION_CHANGED" if eligibility.observation_changed else "UNCHANGED"
                evaluation.source_query = query
                evaluation.source_group = domain
                enrichment_level_used = None
                enrichment_failures = []
                if enriched < enrichment_cap and evaluation.priority in {"HIGH_PRIORITY", "SECONDARY"} and hasattr(client, "enrich_repository"):
                    owner, repo = record.canonical_owner_repo.split("/", 1)
                    evidence = client.enrich_repository(owner, repo, level=enrichment_level)
                    enriched += 1
                    enrichment_level_used = evidence.level
                    enrichment_failures = evidence.failures
                    evaluation.evidence.append(f"enrichment_level={evidence.level}")
                    evaluation.evidence.extend(f"enrichment_failure={item['source']}:{item['code']}" for item in evidence.failures)
                    if evidence.readme:
                        evaluation.candidate.readme = evidence.readme
                    if eligibility.reason:
                        evaluation.semantic_review = LocalSemanticChancellor().review(build_review_packet(
                            evaluation.candidate.__dict__, {"score_total": evaluation.total, "priority": evaluation.priority},
                            capability_profile, [], evidence.to_dict()))
                if historical:
                    evaluation.evidence.append("historical_identity_match=true")
                db.upsert_repository(record)
                db.record_evaluation(
                    record.github_repository_id,
                    evaluation.total,
                    evaluation.decision,
                    [evaluation.primary_route, *evaluation.secondary_routes],
                    evaluation.reason_code if evaluation.decision in {"IGNORE", "ARCHIVE", "REFERENCE_ONLY"} else None,
                    evaluation.review_after,
                )
                if run_id:
                    db.record_candidate_observation(
                        run_id=run_id, record=record, discovery_domain=domain, source_query=query,
                        score=evaluation.total, decision=evaluation.decision, priority=evaluation.priority,
                        enrichment_level=enrichment_level_used, enrichment_failures=enrichment_failures,
                    )
                result.decisions.append(evaluation)
    return result
