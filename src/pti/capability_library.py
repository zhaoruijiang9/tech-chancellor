import json
import sqlite3
from pathlib import Path
from typing import Any

from .activation_policy import classify_activation_tier


def _read_rows(db_path: str | Path) -> list[dict[str, Any]]:
    usage_path = Path(db_path).resolve().parents[1] / "config" / "human_capability_usage.json"
    usage = json.loads(usage_path.read_text(encoding="utf-8")) if usage_path.exists() else {}
    connection = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        has_activation = connection.execute("""select 1 from sqlite_master
            where type='table' and name='activation_records'""").fetchone() is not None
        activation_join = "left join activation_records a on a.github_repository_id=r.github_repository_id" if has_activation else ""
        activation_columns = ",a.activation_tier,a.activation_state,a.pinned_version,a.static_analysis_status,a.isolated_test_status,a.trial_status,a.rollback_status,a.evidence_maturity" if has_activation else ""
        rows = connection.execute(f"""select r.github_repository_id,r.canonical_owner_repo,r.url,r.description,r.stars,r.topics,
            d.decision_json,d.packet_name,d.imported_at{activation_columns} from repositories r join chancellor_decisions d
            on d.github_repository_id=r.github_repository_id {activation_join} order by r.canonical_owner_repo""").fetchall()
        return [{**dict(row), "human_usage": usage.get(dict(row)["canonical_owner_repo"], {})} for row in rows]
    finally:
        connection.close()


def _card(row: dict[str, Any]) -> dict[str, Any]:
    decision = json.loads(row["decision_json"])
    action = decision.get("ACTION", "NOT_EVALUATED")
    form = "KNOWLEDGE" if action == "REFERENCE_ONLY" else "PATTERN" if action == "WATCH" else "TOOL"
    authorization = "AUTO_READ" if form in {"KNOWLEDGE", "PATTERN"} else "USER_APPROVAL_REQUIRED"
    reason = "USER_REQUESTED" if "user-requested" in str(row.get("packet_name", "")) else "SEMANTIC_REVIEWED"
    tier = row.get("activation_tier") or classify_activation_tier(form, decision.get("BEST_ROUTE", "GENERAL"), row["canonical_owner_repo"])
    state = row.get("activation_state") or ("NOT_ELIGIBLE" if form in {"KNOWLEDGE", "PATTERN"} else "QUARANTINE_READY")
    availability = "GLOBAL_CODEX_CONTROLLED" if state == "TRIAL_ENABLED" else "REFERENCE_ONLY" if tier == "TIER_0_KNOWLEDGE_PATTERN" else "NOT_AVAILABLE"
    safe_invocation = state == "TRIAL_ENABLED" and tier in {"TIER_1_DECLARATIVE_SKILL", "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL"}
    return {"repository": row["canonical_owner_repo"], "url": row["url"], "review_reason": reason,
            "capability_name": decision.get("WHAT_IS_IT", row["description"] or row["canonical_owner_repo"]),
            "problem_solved": decision.get("WHAT_PROBLEM_DOES_IT_SOLVE", "UNKNOWN"),
            "why_user_might_care": decision.get("WHY_USER_MIGHT_CARE", "UNKNOWN"),
            "existing_user_capability": decision.get("WHAT_USER_ALREADY_HAS", "UNKNOWN"),
            "capability_delta": decision.get("CAPABILITY_DELTA", "UNKNOWN"),
            "evidence_maturity": row.get("evidence_maturity") or "REVIEWED", "consumption_form": form,
            "authorization_boundary": authorization, "semantic_action": action,
            "activation_tier": tier, "activation_state": state,
            "availability": availability, "safe_invocation_available": safe_invocation,
            "authorization": "CURRENT_TASK_ALLOWED" if safe_invocation else authorization,
            "pinned_version": row.get("pinned_version"),
            "static_analysis_status": row.get("static_analysis_status") or "NOT_RUN",
            "isolated_test_status": row.get("isolated_test_status") or "NOT_RUN",
            "trial_status": row.get("trial_status") or "NOT_ENABLED",
            "rollback_status": row.get("rollback_status") or "UNKNOWN",
            "best_route": decision.get("BEST_ROUTE", "GENERAL"),
            "human_summary": row.get("human_usage", {}).get("human_summary", decision.get("WHAT_IS_IT", "UNKNOWN")),
            "when_to_use": row.get("human_usage", {}).get("when_to_use", []),
            "how_to_ask_codex": row.get("human_usage", {}).get("how_to_ask_codex", []),
            "expected_outputs": row.get("human_usage", {}).get("expected_outputs", []),
            "user_entrypoint": row.get("human_usage", {}).get("user_entrypoint", "直接描述你的目标，Codex 会判断是否相关。"),
            "automatic_use_policy": row.get("human_usage", {}).get("automatic_use_policy", "由 Codex 按任务相关性判断。"),
            "main_limitations": row.get("human_usage", {}).get("main_limitations", []),
            "limitations": {key: decision.get(key, "UNKNOWN") for key in
                            ("DUPLICATION", "INTEGRATION_COST", "SECURITY_RISK", "MAINTENANCE_RISK", "IS_IT_ACTUALLY_BETTER")},
            "evidence_timestamp": row["imported_at"], "reviewed_at": row["imported_at"],
            "stars": row["stars"], "topics": json.loads(row["topics"] or "[]")}


def build_library(root: str | Path, db_path: str | Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    db_path = db_path or root / "state" / "intelligence.db"
    output = root / "library" / "generated"
    repositories = output / "repositories"
    repositories.mkdir(parents=True, exist_ok=True)
    cards = [_card(row) for row in _read_rows(db_path)]
    for card in cards:
        stem = card["repository"].replace("/", "--")
        (repositories / f"{stem}.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        (repositories / f"{stem}.md").write_text("# " + card["repository"] + "\n\n" +
            "- Capability: " + card["capability_name"] + "\n- Problem: " + card["problem_solved"] +
            "\n- Action: `" + card["semantic_action"] + "`\n- Route: `" + card["best_route"] +
            "`\n- Evidence maturity: `" + card["evidence_maturity"] + "`\n- Activation: `" + card["activation_tier"] + "` / `" + card["activation_state"] + "`\n- Consumption: `" + card["consumption_form"] + "`\n" +
            "- Authorization boundary: `" + card["authorization_boundary"] + "`\n- Current task authorization: `" + card["authorization"] + "`\n- Availability: `" + card["availability"] + "`\n- Safe invocation: `" + str(card["safe_invocation_available"]).upper() + "`\n- Version: `" + str(card["pinned_version"] or "UNPINNED") + "`\n- Rollback: `" + card["rollback_status"] + "`\n\n- Why care: " + card["why_user_might_care"] +
            "\n- Capability delta: " + card["capability_delta"] + "\n", encoding="utf-8")
    (output / "index.json").write_text(json.dumps({"count": len(cards), "cards": cards}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "index.md").write_text("# Human Capability Library\n\n" + "\n".join(
        f"- [{card['repository']}]({card['url']}) - {card['capability_name']} - `{card['semantic_action']}`"
        for card in cards) + "\n", encoding="utf-8")
    connection = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        review_next = connection.execute("""select r.canonical_owner_repo,r.url,r.description,r.stars
            from repositories r left join chancellor_decisions d on d.github_repository_id=r.github_repository_id
            where d.github_repository_id is null order by r.last_seen desc""").fetchall()
    finally:
        connection.close()
    (output / "REVIEW_NEXT.md").write_text("# Review Next\n\nThese are prefilter candidates, not current recommendations.\n\n" + "\n".join(
        f"- {row['canonical_owner_repo']} - {row['description'] or 'No description'}" for row in review_next) + "\n", encoding="utf-8")
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    current = cards[:3]
    (reports / "current.json").write_text(json.dumps({"status": "CURRENT_SEMANTIC_VIEW", "items": current}, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports / "current.md").write_text("# Current Semantic Capability View\n\n" + "\n".join(
        f"- {card['repository']}: `{card['semantic_action']}` / `{card['consumption_form']}` - {card['capability_name']}"
        for card in current) + ("\n" if current else "- 本轮没有需要用户采取行动的新能力。\n"), encoding="utf-8")
    return {"status": "LIBRARY_BUILT", "count": len(cards), "output": str(output)}
