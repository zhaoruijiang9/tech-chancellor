"""Small activation post-processing path used after semantic decisions."""

from .activation_policy import (
    TIER_0,
    TIER_1,
    TIER_2,
    TIER_3,
    TIER_4,
    evaluate_activation_policy,
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


def postprocess_semantic_decision(db, repository_id: int, decision: dict) -> dict:
    repository = db.get_repository(repository_id)
    if repository is None:
        return {"status": "ACTIVATION_NOT_EVALUATED", "reason": "REPOSITORY_NOT_FOUND"}
    capability = _capability(repository.to_dict(), decision)
    policy_decision = evaluate_activation_policy(capability, {})
    existing = db.get_activation(repository_id)
    if existing and existing["activation_state"] in {"TRIAL_ENABLED", "USED", "ACTIVE_PATTERN"}:
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
        queue_id = db.enqueue_activation(repository_id, policy_decision.tier, "QUARANTINED",
                                          ";".join(policy_decision.reason_codes))
        return {"status": "ACTIVATION_QUEUED", "tier": policy_decision.tier, "queue_id": queue_id}
    if policy_decision.tier in {TIER_3, TIER_4}:
        queue_id = db.enqueue_activation(repository_id, policy_decision.tier, "QUARANTINED", "HUMAN_APPROVAL_REQUIRED")
        db.complete_activation(queue_id, "BLOCKED_HUMAN", "HUMAN_APPROVAL_REQUIRED")
        return {"status": "ACTIVATION_BLOCKED_HUMAN", "tier": policy_decision.tier, "queue_id": queue_id}
    return {"status": "ACTIVATION_NOT_EVALUATED", "tier": policy_decision.tier}


def process_activation_queue(db, *, limit: int = 5) -> list[dict]:
    """Resolve bounded backlog items without claiming unperformed tests."""
    results: list[dict] = []
    # Reconcile terminal queue decisions created by earlier runtime versions.
    for item in db.list_activation_queue():
        if item["status"] not in {"BLOCKED_HUMAN", "FAILED_TERMINAL"}:
            continue
        current = db.get_activation(item["repository_id"])
        target = "BLOCKED_HUMAN" if item["status"] == "BLOCKED_HUMAN" else "FAILED_WITH_EXPLAINED_REASON"
        if current and current["activation_state"] == "QUARANTINE_READY":
            db.upsert_activation({**current, "activation_state": target,
                                  "static_analysis_status": current.get("static_analysis_status", "NOT_RUN"),
                                  "isolated_test_status": current.get("isolated_test_status", "NOT_RUN"),
                                  "notes": "Terminal activation decision reconciled from the activation queue."})
    for item in db.list_activation_queue("PENDING")[:max(0, limit)]:
        claimed = db.claim_activation(item["id"])
        if not claimed or claimed["status"] != "PROCESSING":
            continue
        reason = str(item.get("reason", ""))
        sensitive = any(marker in reason for marker in ("CREDENTIAL_REQUIRED", "TRADING_SCOPE", "ADMIN_REQUIRED"))
        if sensitive:
            state = "BLOCKED_HUMAN"
            queue_status = "BLOCKED_HUMAN"
            failure = "HUMAN_APPROVAL_REQUIRED"
            note = "Static review found a credential, trading, or privileged boundary; no execution was attempted."
        else:
            state = "FAILED_WITH_EXPLAINED_REASON"
            queue_status = "FAILED_TERMINAL"
            failure = "SAFE_REPRODUCIBLE_ACTIVATION_NOT_AVAILABLE"
            note = "Pinned version, rollback, or isolated execution evidence is missing; no unsafe installation was attempted."
        db.upsert_activation({
            "github_repository_id": item["repository_id"],
            "activation_tier": item["activation_tier"],
            "activation_state": state,
            "evidence_maturity": "REVIEWED",
            "static_analysis_status": "BOUNDARY_REVIEWED",
            "isolated_test_status": "NOT_RUN",
            "trial_status": "NOT_ENABLED",
            "rollback_status": "UNKNOWN",
            "notes": note,
        })
        db.complete_activation(item["id"], queue_status, failure)
        results.append({"repository_id": item["repository_id"], "activation_state": state, "queue_status": queue_status, "reason": failure})
    return results
