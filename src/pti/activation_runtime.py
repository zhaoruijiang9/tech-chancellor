"""Small activation post-processing path used after semantic decisions."""

from .activation_policy import (
    TIER_0,
    TIER_1,
    TIER_2,
    TIER_3,
    TIER_4,
    evaluate_validation_eligibility,
    classify_activation_tier,
)


def _capability(repository: dict, decision: dict) -> dict:
    text = " ".join(str(decision.get(key, "")) for key in
                    ("WHAT_IS_IT", "CAPABILITY_DELTA", "INTEGRATION_COST", "SECURITY_RISK", "BEST_ROUTE")).lower()
    route = str(decision.get("BEST_ROUTE", "GENERAL"))
    action = str(decision.get("ACTION", ""))
    form = "KNOWLEDGE" if action == "REFERENCE_ONLY" else "PATTERN" if action == "WATCH" else "TOOL"
    return {
        "repository": repository.get("canonical_owner_repo", ""),
        "consumption_form": form,
        "best_route": route,
        "activation_tier": classify_activation_tier(form, route, repository.get("canonical_owner_repo", "")),
        "requires_credential": any(word in text for word in ("credential", "token", "password", "secret", "api key")),
        "requires_service": any(word in text for word in ("daemon", "persistent service", "mcp server")),
        "trading_scope": route == "BUSINESS_MONEY" or any(word in text for word in ("broker", "order", "holding", "trading")),
        "rollback_available": False,
    }


def postprocess_semantic_decision(db, repository_id: int, decision: dict, packet: dict | None = None) -> dict:
    repository = db.get_repository(repository_id)
    if repository is None:
        return {"status": "ACTIVATION_NOT_EVALUATED", "reason": "REPOSITORY_NOT_FOUND"}
    action = decision.get("ACTION")
    no_delta = "NO_MEANINGFUL_DELTA" in str(decision.get("DUPLICATION", "")).upper()
    if action in {"IGNORE", "ARCHIVE"} or no_delta or action == "USER_REVIEW_RECOMMENDED":
        category = "HUMAN_GATE" if action == "USER_REVIEW_RECOMMENDED" else "NO_MEANINGFUL_DELTA" if no_delta else "NOT_WORTH_ACTIVATING"
        if packet is not None:
            _readiness(db, repository, category, decision.get("CAPABILITY_DELTA") or category)
            _mark_boundary(db, repository_id, "BLOCKED_HUMAN" if category == "HUMAN_GATE" else "KEEP_REFERENCE_ONLY", category)
        return {"status": "ACTIVATION_HUMAN_GATE" if category == "HUMAN_GATE" else "ACTIVATION_NOT_ELIGIBLE", "reason": category}
    capability = _capability(repository.to_dict(), decision)
    if packet is not None and action == "CANDIDATE_FOR_QUARANTINE":
        boundary = evaluate_validation_eligibility(capability)
        if not boundary.eligible or boundary.tier in {TIER_3, TIER_4}:
            reason = ";".join(boundary.reason_codes)
            _readiness(db, repository, "HUMAN_GATE", reason)
            _mark_boundary(db, repository_id, "BLOCKED_HUMAN", reason, boundary.tier)
            return {"status": "ACTIVATION_BLOCKED_HUMAN", "reason": "HUMAN_GATE", "tier": boundary.tier}
        with db._connect() as connection:
            safe_mapping = connection.execute("""SELECT 1 FROM implementation_capabilities m
                JOIN capability_implementations i USING(implementation_id)
                JOIN capability_sources s USING(source_id)
                WHERE s.github_repository_id=? AND m.capability_id='SKILL_ECOSYSTEM_DISCOVERY'""", (repository_id,)).fetchone()
        if not safe_mapping:
            _readiness(db, repository, "REQUIRES_OS_SANDBOX", "SECURE_THIRD_PARTY_EXECUTION_SANDBOX is missing; no executable adapter authorized")
            _mark_boundary(db, repository_id, "KEEP_REFERENCE_ONLY", "REQUIRES_OS_SANDBOX")
            return {"status": "ACTIVATION_NOT_ELIGIBLE", "reason": "REQUIRES_OS_SANDBOX"}
        capability["activation_tier"] = TIER_1
    policy_decision = evaluate_validation_eligibility(capability)
    existing = db.get_activation(repository_id)
    if existing and (existing["activation_state"] in {"TRIAL_ENABLED", "USED"}
                     or (existing["activation_state"] == "ACTIVE_PATTERN" and policy_decision.tier == TIER_0)):
        return {"status": "ACTIVATION_ALREADY_AVAILABLE", "tier": existing["activation_tier"]}

    if policy_decision.tier == TIER_0:
        db.upsert_activation({
            "github_repository_id": repository_id,
            "activation_tier": TIER_0,
            "activation_state": "ACTIVE_PATTERN",
            "evidence_maturity": "REVIEWED",
            "trial_status": "NOT_ENABLED",
            "rollback_status": "READY",
            "notes": "Automatically promoted reference/pattern; no code execution.",
        })
        return {"status": "ACTIVATION_PROMOTED_PATTERN", "tier": TIER_0}

    next_state = "QUARANTINE_READY"
    db.upsert_activation({
        "github_repository_id": repository_id,
        "activation_tier": policy_decision.tier,
        "activation_state": next_state,
        "evidence_maturity": "REVIEWED",
        "trial_status": "NOT_ENABLED",
        "rollback_status": "UNKNOWN",
        "notes": "Semantic decision completed; activation remains a separate bounded path.",
    })
    if policy_decision.tier in {TIER_1, TIER_2}:
        if not policy_decision.eligible:
            reason = ";".join(policy_decision.reason_codes)
            queue_id = db.enqueue_activation(repository_id, policy_decision.tier, "QUARANTINED", reason)
            db.complete_activation(queue_id, "BLOCKED_HUMAN", reason)
            db.upsert_activation({"github_repository_id": repository_id, "activation_tier": policy_decision.tier,
                                  "activation_state": "BLOCKED_HUMAN", "notes": reason})
            return {"status": "ACTIVATION_BLOCKED_HUMAN", "tier": policy_decision.tier, "queue_id": queue_id}
        queue_id = db.enqueue_activation(repository_id, policy_decision.tier, "QUARANTINED",
                                          ";".join(policy_decision.reason_codes))
        if packet is not None:
            _readiness(db, repository, "READY_WITH_EXISTING_ADAPTER", "Read-only Markdown index adapter; worker still validates pinned evidence")
        return {"status": "ACTIVATION_QUEUED", "tier": policy_decision.tier, "queue_id": queue_id}
    if policy_decision.tier in {TIER_3, TIER_4}:
        queue_id = db.enqueue_activation(repository_id, policy_decision.tier, "QUARANTINED", "HUMAN_APPROVAL_REQUIRED")
        db.complete_activation(queue_id, "BLOCKED_HUMAN", "HUMAN_APPROVAL_REQUIRED")
        return {"status": "ACTIVATION_BLOCKED_HUMAN", "tier": policy_decision.tier, "queue_id": queue_id}
    return {"status": "ACTIVATION_NOT_EVALUATED", "tier": policy_decision.tier}


def _readiness(db, repository, category: str, blocker: str) -> None:
    with db._connect() as connection:
        connection.execute("""INSERT INTO activation_readiness(implementation_id,category,blocker)
            VALUES (?,?,?) ON CONFLICT(implementation_id) DO UPDATE SET
            category=excluded.category,blocker=excluded.blocker,audited_at=CURRENT_TIMESTAMP""",
            (f"impl:{repository.canonical_owner_repo}", category, blocker[:1000]))
        lifecycle = {"HUMAN_GATE": "HUMAN_GATE", "NO_MEANINGFUL_DELTA": "NOT_ADOPTED",
                     "NOT_WORTH_ACTIVATING": "NOT_ADOPTED", "REQUIRES_OS_SANDBOX": "BLOCKED_PLATFORM"}.get(category)
        if lifecycle:
            connection.execute("""UPDATE capability_implementations SET lifecycle_state=?,updated_at=CURRENT_TIMESTAMP
                WHERE implementation_id=? AND lifecycle_state NOT IN ('AVAILABLE','USED')""",
                (lifecycle, f"impl:{repository.canonical_owner_repo}"))


def _mark_boundary(db, repository_id: int, state: str, reason: str, tier: str = TIER_2) -> None:
    existing = db.get_activation(repository_id)
    if existing and existing["activation_state"] in {"TRIAL_ENABLED", "USED"}:
        return
    db.upsert_activation({"github_repository_id": repository_id, "activation_tier": tier,
                          "activation_state": state, "evidence_maturity": "REVIEWED",
                          "trial_status": "NOT_ENABLED", "notes": reason})
