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
    query_groups = config.get("query_groups", [])
    per_query_cap = int(config.get("per_query_cap", 5))
    total_cap = int(config.get("total_candidate_cap", 20))
    enrichment_level = str(config.get("enrichment_level", "STANDARD")).upper()
    enrichment_cap = int(config.get("enrichment_candidate_cap", 3))

    # Complete the configured search first. Candidate caps apply after the
    # first-pass observations have been merged and ranked.
    hits: dict[int, dict[str, Any]] = {}
    for group in query_groups:
        domain = group.get("domain", "GENERAL")
        for query in group.get("queries", []):
            api_result: ApiResult = client.search_repositories(query, page=1, per_page=per_query_cap)
            result.request_count += 1
            if api_result.failure:
                result.failures.append({"code": "DISCOVERY_NOT_EVALUATED", "message": api_result.failure.message, "query": query})
                continue
            for record in api_result.items:
                hit = hits.setdefault(record.github_repository_id, {"record": record, "hits": []})
                hit["hits"].append((domain, query))

    prepared: list[dict[str, Any]] = []
    for hit in hits.values():
        record = hit["record"]
        domain, query = hit["hits"][0]
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
        prepared.append({"record": record, "evaluation": evaluation, "historical": historical,
                         "eligibility": eligibility, "hits": hit["hits"],
                         "enrichment_level": None, "enrichment_failures": []})

    prepared.sort(key=lambda item: (-item["evaluation"].total, -item["record"].stars,
                                    item["record"].canonical_owner_repo, item["record"].github_repository_id))
    selected = prepared[:total_cap]
    selected_ids = {item["record"].github_repository_id for item in selected}
    enriched = 0
    for item in selected:
        record = item["record"]
        evaluation = item["evaluation"]
        historical = item["historical"]
        eligibility = item["eligibility"]
        if enriched < enrichment_cap and evaluation.priority in {"HIGH_PRIORITY", "SECONDARY"} and hasattr(client, "enrich_repository"):
            owner, repo = record.canonical_owner_repo.split("/", 1)
            evidence = client.enrich_repository(owner, repo, level=enrichment_level)
            enriched += 1
            item["enrichment_level"] = evidence.level
            item["enrichment_failures"] = evidence.failures
            evaluation.evidence.append(f"enrichment_level={evidence.level}")
            evaluation.evidence.extend(f"enrichment_failure={entry['source']}:{entry['code']}" for entry in evidence.failures)
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
        result.decisions.append(evaluation)

    if run_id:
        # Keep every source-query hit as auditable observation evidence, while
        # the scan's candidate_count remains bounded by the selected result set.
        for item in prepared:
            evaluation = item["evaluation"]
            for domain, query in item["hits"]:
                db.record_candidate_observation(
                    run_id=run_id, record=item["record"], discovery_domain=domain, source_query=query,
                    score=evaluation.total, decision=evaluation.decision, priority=evaluation.priority,
                    enrichment_level=item["enrichment_level"] if item["record"].github_repository_id in selected_ids else None,
                    enrichment_failures=item["enrichment_failures"] if item["record"].github_repository_id in selected_ids else [],
                )
    return result
