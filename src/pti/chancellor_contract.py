from dataclasses import dataclass
from typing import Any

ALLOWED_ACTIONS = {"IGNORE", "ARCHIVE", "REFERENCE_ONLY", "WATCH", "CANDIDATE_FOR_QUARANTINE", "USER_REVIEW_RECOMMENDED"}
ALLOWED_ROUTES = {"AI_AGENT", "AI_EXPERIENCE", "QUANT_DATA", "PRODUCTIVITY", "BUSINESS_MONEY", "RESEARCH_LEARNING", "WATCHLIST", "CHANGE_SIGNAL", "GENERAL"}
REQUIRED_FIELDS = {"WHAT_IS_IT", "WHY_NOW", "WHY_USER_MIGHT_CARE", "WHAT_PROBLEM_DOES_IT_SOLVE", "WHAT_USER_ALREADY_HAS", "CAPABILITY_DELTA", "IS_IT_ACTUALLY_BETTER", "DUPLICATION", "CURRENT_NEED_MATCH", "INTEGRATION_COST", "SECURITY_RISK", "MATURITY", "MAINTENANCE_RISK", "BEST_ROUTE", "ACTION"}


@dataclass(frozen=True)
class Validation:
    valid: bool
    errors: list[str]


def validate_decision(value: Any) -> Validation:
    if not isinstance(value, dict):
        return Validation(False, ["decision must be an object"])
    errors = sorted(REQUIRED_FIELDS - set(value))
    if value.get("ACTION") not in ALLOWED_ACTIONS:
        errors.append("ACTION is not allowed")
    if value.get("BEST_ROUTE") not in ALLOWED_ROUTES:
        errors.append("BEST_ROUTE is not an allowed route")
    if any(not isinstance(value.get(field), str) for field in REQUIRED_FIELDS if field in value):
        errors.append("all decision fields must be strings")
    return Validation(not errors, errors)


def import_decision(value: Any) -> dict[str, str]:
    result = validate_decision(value)
    if not result.valid:
        raise ValueError("malformed Chancellor decision: " + "; ".join(result.errors))
    return {field: str(value[field]) for field in REQUIRED_FIELDS}
