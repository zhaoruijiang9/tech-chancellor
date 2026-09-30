from dataclasses import dataclass, field
from typing import Any

from .github_api import ApiResult
from .models import RepositoryRecord
from .policy import Candidate, Evaluation, decide_candidate, score_candidate
from .chancellor import LocalSemanticChancellor, build_review_packet
from .storage import Database
from .review_queue import fingerprint, material_evidence_projection, review_eligibility
from .capability_invocation import active_bindings, invoke_index, relevant_to_intent


@dataclass
class DiscoveryRun:
    decisions: list[Evaluation] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    request_count: int = 0
    capability_invocations: list[dict[str, Any]] = field(default_factory=list)


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
                  run_id: str | None = None, *, capability_root=None,
                  consumer_bindings: list[dict] | None = None) -> DiscoveryRun:
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

    invoked: list[dict[str, Any]] = []
    if run_id and capability_root is not None and consumer_bindings:
        radar_queries = [query for group in query_groups for query in group.get("queries", [])]
        known_names = {hit["record"].canonical_owner_repo.lower() for hit in hits.values()}
        for binding in active_bindings(db, capability_root, consumer_bindings, "RADAR_DISCOVERY"):
            summary = {"raw_count": 0, "normalized_count": 0, "new_count": 0,
                       "rejected_irrelevant_count": 0,
                       "semantic_reviewed_count": 0}
            new_ids: set[int] = set()
            metadata_lookups = 0
            failure_code = None
            intent = []
            try:
                output = invoke_index(capability_root, binding, radar_queries)
                intent = output["intents"]
                summary["raw_count"] = output["raw_count"]
                summary["normalized_count"] = len(output["normalized"])
                for item in output["normalized"]:
                    if metadata_lookups >= min(max(int(binding.get("max_metadata_lookups", 3)), 1), 3):
                        break
                    name = item["owner_repo"]
                    if name.lower() in known_names:
                        continue
                    owner, repository = name.split("/", 1)
                    if db.get_repository_by_name(name) is not None:
                        continue
                    response = client.get_repository(owner, repository)
                    metadata_lookups += 1
                    result.request_count += 1
                    if response.failure or not response.items:
                        failure_code = "GITHUB_LINK_LOOKUP_FAILED"
                        continue
                    record = response.items[0]
                    if not relevant_to_intent(binding, item["intent"], item["name"], record):
                        summary["rejected_irrelevant_count"] += 1
                        continue
                    if record.github_repository_id in hits or db.get_repository(record.github_repository_id):
                        continue
                    known_names.add(name.lower())
                    hit = hits.setdefault(record.github_repository_id, {"record": record, "hits": []})
                    intent_rule = (binding.get("intent_rules") or {}).get(item["intent"], {})
                    hit["hits"].append((intent_rule.get("domain", binding.get("discovery_domain", "AI_AGENT")),
                                        f"capability:{binding['capability_id']}:{item['intent']}"))
                    new_ids.add(record.github_repository_id)
                    if len(new_ids) >= min(max(int(binding["max_new_candidates"]), 1), 3):
                        break
                summary["new_count"] = len(new_ids)
                summary["metadata_lookups"] = metadata_lookups
            except Exception:
                failure_code = "CAPABILITY_INVOCATION_FAILED"
            invoked.append({"binding": binding, "summary": summary, "new_ids": new_ids,
                            "failure_code": failure_code, "intent": intent})

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
    new_source_ids = {repository_id for invocation in invoked for repository_id in invocation["new_ids"]}
    eligible_source = [item for item in prepared if item["record"].github_repository_id in new_source_ids
                       and item["evaluation"].priority == "HIGH_PRIORITY"]
    if total_cap > 0 and eligible_source and not any(item in selected for item in eligible_source):
        selected = selected[:-1] + eligible_source[:1]
        selected.sort(key=lambda item: (-item["evaluation"].total, -item["record"].stars,
                                        item["record"].canonical_owner_repo, item["record"].github_repository_id))
    selected_ids = {item["record"].github_repository_id for item in selected}
    enrich_eligible = [item for item in selected if item["evaluation"].priority in {"HIGH_PRIORITY", "SECONDARY"}]
    source_enrich = [item for item in enrich_eligible if item["record"].github_repository_id in new_source_ids][:1]
    enrich_order = source_enrich + [item for item in enrich_eligible if item not in source_enrich]
    enrich_ids = {item["record"].github_repository_id for item in enrich_order[:enrichment_cap]}
    for item in selected:
        record = item["record"]
        evaluation = item["evaluation"]
        historical = item["historical"]
        eligibility = item["eligibility"]
        if record.github_repository_id in enrich_ids and hasattr(client, "enrich_repository"):
            owner, repo = record.canonical_owner_repo.split("/", 1)
            evidence = client.enrich_repository(owner, repo, level=enrichment_level)
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
        if any(record.github_repository_id in invocation["new_ids"] for invocation in invoked):
            evaluation.evidence.append("untrusted_capability_index_link=true")
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
        for invocation in invoked:
            binding = invocation["binding"]
            invocation["summary"]["selected_new_count"] = len(invocation["new_ids"] & selected_ids)
            reviewed = [item for item in selected if item["record"].github_repository_id in invocation["new_ids"]
                        and item["evaluation"].semantic_review]
            invocation["summary"]["semantic_reviewed_count"] = len(reviewed)
            material_reviewed = [item for item in reviewed if item["evaluation"].candidate.readme.strip()
                                 and item["evaluation"].semantic_review.get("ACTION") == "USER_REVIEW_RECOMMENDED"]
            material = bool(material_reviewed)
            downstream = {"new_candidate_ids": sorted(invocation["new_ids"]),
                          "semantic_reviewed_ids": sorted(item["record"].github_repository_id for item in reviewed),
                          "material_reviewed_ids": sorted(item["record"].github_repository_id for item in material_reviewed)}
            db.record_capability_invocation(
                capability_id=binding["capability_id"], implementation_id=binding["implementation_id"],
                adapter_type=binding["adapter_type"], consumer="RADAR_DISCOVERY", task_run_id=run_id,
                input_intent=invocation["intent"], output_summary=invocation["summary"],
                downstream_effect=downstream, success=invocation["failure_code"] is None,
                material_use=material, failure_code=invocation["failure_code"])
            if material:
                db.record_real_use(binding["repository_id"], "TechChancellor Radar", "capability-source-discovery",
                                   f"{len(material_reviewed)} new candidate(s) semantically reviewed with source evidence",
                                   f"scan:{run_id};repo_ids:{','.join(str(item['record'].github_repository_id) for item in material_reviewed)}",
                                   real_task_evidence=True)
            result.capability_invocations.append({"capability_id": binding["capability_id"],
                "implementation_id": binding["implementation_id"], "consumer": "RADAR_DISCOVERY",
                "material_use": material, "failure_code": invocation["failure_code"], **invocation["summary"]})
    if hasattr(client, "budget") and hasattr(client.budget, "used"):
        result.request_count = client.budget.used
    return result
