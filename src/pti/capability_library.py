import json
import sqlite3
from pathlib import Path
from typing import Any


def _read_rows(db_path: str | Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("""select r.canonical_owner_repo,r.url,r.description,r.stars,r.topics,
            d.decision_json,d.imported_at from repositories r join chancellor_decisions d
            on d.github_repository_id=r.github_repository_id order by r.canonical_owner_repo""").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def _card(row: dict[str, Any]) -> dict[str, Any]:
    decision = json.loads(row["decision_json"])
    action = decision.get("ACTION", "NOT_EVALUATED")
    form = "KNOWLEDGE" if action == "REFERENCE_ONLY" else "PATTERN" if action == "WATCH" else "TOOL"
    authorization = "AUTO_READ" if form in {"KNOWLEDGE", "PATTERN"} else "USER_APPROVAL_REQUIRED"
    reason = "USER_REQUESTED" if "user-requested" in str(row.get("packet_name", "")) else "SEMANTIC_REVIEWED"
    return {"repository": row["canonical_owner_repo"], "url": row["url"], "review_reason": reason,
            "capability_name": decision.get("WHAT_IS_IT", row["description"] or row["canonical_owner_repo"]),
            "problem_solved": decision.get("WHAT_PROBLEM_DOES_IT_SOLVE", "UNKNOWN"),
            "why_user_might_care": decision.get("WHY_USER_MIGHT_CARE", "UNKNOWN"),
            "existing_user_capability": decision.get("WHAT_USER_ALREADY_HAS", "UNKNOWN"),
            "capability_delta": decision.get("CAPABILITY_DELTA", "UNKNOWN"),
            "evidence_maturity": "REVIEWED", "consumption_form": form,
            "authorization_boundary": authorization, "semantic_action": action,
            "best_route": decision.get("BEST_ROUTE", "GENERAL"),
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
            "`\n- Evidence maturity: `REVIEWED`\n- Consumption: `" + card["consumption_form"] + "`\n" +
            "- Authorization: `" + card["authorization_boundary"] + "`\n\n- Why care: " + card["why_user_might_care"] +
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
