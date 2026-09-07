"""Minimal, conservative capability activation policy.

Activation state is persisted by :mod:`pti.storage`; the tier rules are loaded
from the checked-in JSON policy so decisions are auditable and not scattered
through runtime branches.
"""

import json
from dataclasses import dataclass
from pathlib import Path

TIER_0 = "TIER_0_KNOWLEDGE_PATTERN"
TIER_1 = "TIER_1_DECLARATIVE_SKILL"
TIER_2 = "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL"
TIER_3 = "TIER_3_SERVICE_OR_HIGH_INTEGRATION"
TIER_4 = "TIER_4_SENSITIVE_TRADING_OR_PRIVILEGED"

ACTIVATION_STATES = {
    "NOT_ELIGIBLE", "QUARANTINE_READY", "QUARANTINED", "STATIC_ANALYSIS_PASS",
    "STATIC_ANALYSIS_FAIL", "ISOLATED_TEST_PASS", "ISOLATED_TEST_FAIL",
    "TRIAL_ENABLED", "TRIAL_DISABLED", "ACTIVE_PATTERN", "USED", "ROLLED_BACK",
}
EVIDENCE_MATURITY = {"REVIEWED": "REVIEWED", "TESTED": "TESTED", "USED": "USED"}

STATE_TRANSITIONS = {
    "REVIEWED": {"QUARANTINE_READY", "ACTIVE_PATTERN"},
    "NOT_ELIGIBLE": {"ACTIVE_PATTERN"},
    "QUARANTINE_READY": {"QUARANTINED", "TRIAL_DISABLED"},
    "QUARANTINED": {"STATIC_ANALYSIS_PASS", "STATIC_ANALYSIS_FAIL", "ROLLED_BACK"},
    "STATIC_ANALYSIS_PASS": {"ISOLATED_TEST_PASS", "ISOLATED_TEST_FAIL", "ROLLED_BACK"},
    "ISOLATED_TEST_PASS": {"TRIAL_ENABLED", "ROLLED_BACK"},
    "ISOLATED_TEST_FAIL": {"QUARANTINED", "ROLLED_BACK"},
    "TRIAL_ENABLED": {"USED", "TRIAL_DISABLED", "ROLLED_BACK"},
    "TRIAL_DISABLED": {"TRIAL_ENABLED", "ROLLED_BACK"},
    "ACTIVE_PATTERN": {"USED", "ROLLED_BACK"},
    "ROLLED_BACK": {"QUARANTINE_READY", "TRIAL_DISABLED"},
}


def classify_activation_tier(consumption_form: str, route: str, repository: str = "") -> str:
    text = f"{consumption_form} {route} {repository}".upper()
    if any(marker in text for marker in ("TRADING", "BROKER", "POSITION", "MONEY")):
        return TIER_4
    if "ARCHIFY" in text or consumption_form.upper() == "DECLARATIVE_SKILL":
        return TIER_1
    if consumption_form.upper() in {"KNOWLEDGE", "PATTERN"}:
        return TIER_0
    if any(marker in text for marker in ("MCP", "SERVICE", "SERVER", "PROXY")):
        return TIER_3
    return TIER_2


def evidence_maturity_for_state(state: str, existing: str = "REVIEWED") -> str:
    if state == "ISOLATED_TEST_PASS":
        return "TESTED"
    if state == "TRIAL_ENABLED":
        return "TESTED"
    if state == "USED":
        return "USED"
    return existing if existing in EVIDENCE_MATURITY.values() else "REVIEWED"


def transition_activation(db, repository_id: int, next_state: str, real_use: bool = False) -> dict:
    record = db.get_activation(repository_id)
    if record is None:
        raise ValueError(f"activation record not found: {repository_id}")
    current = record["activation_state"]
    if next_state not in ACTIVATION_STATES:
        raise ValueError(f"unknown activation state: {next_state}")
    if next_state not in STATE_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid activation transition: {current} -> {next_state}")
    if next_state == "USED" and not real_use:
        raise ValueError("USED requires real task evidence")
    updated = dict(record)
    updated["activation_state"] = next_state
    updated["evidence_maturity"] = evidence_maturity_for_state(next_state, record.get("evidence_maturity", "REVIEWED"))
    db.upsert_activation(updated)
    return db.get_activation(repository_id)


@dataclass(frozen=True)
class ActivationPolicyDecision:
    tier: str
    eligible: bool
    automatic_actions_allowed: list[str]
    human_approval_required_before: list[str]
    hard_prohibitions: list[str]
    max_activation_state: str
    reason_codes: list[str]

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "eligible": self.eligible,
            "automatic_actions_allowed": self.automatic_actions_allowed,
            "human_approval_required_before": self.human_approval_required_before,
            "hard_prohibitions": self.hard_prohibitions,
            "max_activation_state": self.max_activation_state,
            "reason_codes": self.reason_codes,
        }


def _default_policy_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "capability_activation_policy.json"


def _policy(path: str | Path | None = None) -> dict:
    return json.loads((_default_policy_path() if path is None else Path(path)).read_text(encoding="utf-8"))


def evaluate_activation_policy(capability: dict, evidence: dict, policy_path: str | Path | None = None) -> ActivationPolicyDecision:
    policy = _policy(policy_path)
    tier = capability.get("activation_tier") or classify_activation_tier(
        capability.get("consumption_form", "TOOL"), capability.get("best_route", "GENERAL"), capability.get("repository", "")
    )
    definition = policy["tiers"].get(tier, policy["tiers"][TIER_4])
    reasons: list[str] = []
    prohibitions: list[str] = list(definition.get("hard_prohibitions", []))
    human = list(definition.get("human_approval_required_before", []))
    automatic = list(definition.get("automatic_actions_allowed", []))
    hazards = {
        "requires_credential": "CREDENTIAL_REQUIRED",
        "requires_admin": "ADMIN_REQUIRED",
        "requires_service": "SERVICE_REQUIRED",
        "persistent_listener": "PERSISTENT_NETWORK_LISTENER",
        "system_modification": "SYSTEM_MODIFICATION_REQUIRED",
        "path_modification": "PATH_MODIFICATION_REQUIRED",
        "browser_extension": "BROWSER_EXTENSION_REQUIRED",
        "trading_scope": "TRADING_SCOPE",
    }
    for field, reason in hazards.items():
        if capability.get(field, False):
            reasons.append(reason)
            prohibitions.append(reason)
    if capability.get("pinned_version"):
        reasons.append("PINNED_VERSION_AVAILABLE")
    else:
        reasons.append("PINNED_VERSION_MISSING")
    if capability.get("rollback_available"):
        reasons.append("ROLLBACK_AVAILABLE")
    else:
        reasons.append("ROLLBACK_UNCLEAR")

    if tier == TIER_0:
        reasons.append("REFERENCE_ONLY_NO_EXECUTION")
        return ActivationPolicyDecision(tier, True, automatic, human, prohibitions, "ACTIVE_PATTERN", reasons)
    if tier in {TIER_1, TIER_2}:
        static = evidence.get("static_analysis_pass")
        isolated = evidence.get("isolated_test_pass")
        delta = evidence.get("capability_delta")
        if static is True:
            reasons.append("STATIC_ANALYSIS_PASS")
        else:
            reasons.append("ISOLATED_TEST_REQUIRED" if static is None else "STATIC_ANALYSIS_BLOCKED")
        if isolated is True:
            reasons.append("ISOLATED_TEST_PASS")
        else:
            reasons.append("ISOLATED_TEST_REQUIRED" if isolated is None else "TEST_FAILED")
        if delta is True:
            reasons.append("CAPABILITY_DELTA_CONFIRMED")
        else:
            reasons.append("NO_CAPABILITY_DELTA" if delta is False else "CAPABILITY_DELTA_REQUIRED")
        eligible = (
            not any(capability.get(field, False) for field in hazards)
            and bool(capability.get("pinned_version"))
            and bool(capability.get("rollback_available"))
            and static is True and isolated is True and delta is True
        )
        return ActivationPolicyDecision(tier, eligible, automatic if eligible else [], human, prohibitions,
                                        "TRIAL_ENABLED" if eligible else "QUARANTINED", reasons)
    reasons.append("HUMAN_APPROVAL_REQUIRED")
    return ActivationPolicyDecision(tier, False, automatic, human, prohibitions, "QUARANTINED", reasons)
