import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from .policy import Evaluation
from .review_queue import allocate_review_slots


@dataclass
class Report:
    high_priority: list[Evaluation]
    secondary: list[Evaluation]
    archived: list[Evaluation]
    failures: list[dict]


def build_report(decisions: list[Evaluation], failures: list[dict]) -> Report:
    high_candidates = [item for item in decisions if item.priority == "HIGH_PRIORITY"]
    high: list[Evaluation] = []
    routes_seen: set[str] = set()
    for item in high_candidates:
        if item.primary_route not in routes_seen and len(high) < 5:
            high.append(item)
            routes_seen.add(item.primary_route)
    for item in high_candidates:
        if len(high) >= 5:
            break
        if not any(existing is item for existing in high):
            high.append(item)
    secondary = [item for item in decisions if item.priority == "SECONDARY"][:10]
    archived = [item for item in decisions if item.priority == "ARCHIVE"]
    return Report(high, secondary, archived, failures)


def _markdown(decision: Evaluation) -> str:
    item = decision.candidate
    lines = [f"# {item.name}", "", f"- Decision: `{decision.decision}`", f"- Priority: `{decision.priority}`",
             f"- Route: `{decision.primary_route}`", f"- Score: `{decision.total}`", "",
             f"## Why now\n{item.description or 'No description provided.'}", "",
             "## Capability Delta", f"- Existing: {decision.capability_delta.get('existing_capability', 'UNKNOWN')}",
             f"- Addition: {decision.capability_delta.get('candidate_addition', 'UNKNOWN')}",
             f"- Incremental value: {decision.incremental_value}", "",
             "## Risk", "- " + "\n- ".join(decision.risk_flags), "",
             "## Next Action", decision.recommended_next_action, "", "## Evidence",
             "- " + "\n- ".join(decision.evidence)]
    if decision.semantic_review:
        lines.extend(["", "## Chancellor Review", "- What is it: " + decision.semantic_review.get("WHAT_IS_IT", "UNKNOWN"),
                      "- Capability delta: " + decision.semantic_review.get("CAPABILITY_DELTA", "UNKNOWN"),
                      "- Recommended action: " + decision.semantic_review.get("RECOMMENDED_ACTION", "UNKNOWN")])
    return "\n".join(lines) + "\n"


def write_inbox_artifacts(root: str | Path, decisions: list[Evaluation], run_id: str | None = None) -> list[Path]:
    root = Path(root).resolve()
    run_id = run_id or uuid.uuid4().hex[:10]
    paths: list[Path] = []
    for index, decision in enumerate(decisions, start=1):
        route = decision.primary_route if decision.primary_route.replace("_", "").isalnum() else "GENERAL"
        directory = root / "inbox" / route
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"candidate-{run_id}-{index:03d}"
        json_path = directory / f"{stem}.json"
        markdown_path = directory / f"{stem}.md"
        json_path.write_text(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(_markdown(decision), encoding="utf-8")
        paths.extend([json_path, markdown_path])
    return paths


def write_chancellor_pending(root: str | Path, decisions: list[Evaluation], run_id: str | None = None,
                             *, limit: int = 3, include_backlog: bool = True) -> list[Path]:
    from .candidate_pipeline import (build_stage_b_packet, candidate_admission, find_existing_packet,
                                    persist_candidate, record_handoff, restore_evaluation, review_backlog)
    from .storage import Database
    root = Path(root).resolve()
    db = Database(root / "state/intelligence.db")
    db.initialize()
    ids = set()
    for item in decisions:
        if candidate_admission(item)["admitted"]:
            persist_candidate(db, item, run_id)
            ids.add(item.candidate.github_repository_id)
    if include_backlog:
        ids.update(item.candidate.github_repository_id for item in review_backlog(db))
    candidates = []
    paths = []
    for repository_id in sorted(ids):
        with db._connect() as connection:
            row = connection.execute("SELECT * FROM canonical_candidates WHERE github_repository_id=?", (repository_id,)).fetchone()
        if not row or row["stage"] == "CHANCELLOR_DECIDED":
            continue
        existing = find_existing_packet(root, repository_id, active_only=True)
        if existing:
            if row["stage"] != "WAITING_CHANCELLOR":
                record_handoff(db, repository_id, existing.name)
            if ".processing" not in existing.stem:
                packet = json.loads(existing.read_text(encoding="utf-8"))
                provenance = json.loads(row["provenance_json"])
                if packet.get("source_provenance") != provenance:
                    packet["source_provenance"] = provenance
                    temporary = existing.with_suffix(".tmp")
                    temporary.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
                    temporary.replace(existing)
            paths.append(existing)
            continue
        candidates.append((restore_evaluation(row), row))
    selected = allocate_review_slots([item for item, _ in candidates], max(0, limit))
    for item in selected:
        row = next(row for value, row in candidates if value is item)
        directory = root / "chancellor_pending"
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{item.candidate.github_repository_id}--{row['review_fingerprint'][:16]}.json"
        path = directory / name
        if path.with_name(path.stem + ".processed.json").exists():
            continue
        payload = build_stage_b_packet(item, db, row["scan_run_id"])
        payload["review_fingerprint"] = row["review_fingerprint"]
        if not path.exists():
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(path)
        record_handoff(db, item.candidate.github_repository_id, path.name)
        paths.append(path)
    return paths


def write_run_report(root: str | Path, report: Report) -> Path:
    root = Path(root).resolve()
    root.joinpath("reports").mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "PREFILTER_ONLY_NOT_FINAL",
        "high_priority": [item.to_dict() for item in report.high_priority],
        "secondary": [item.to_dict() for item in report.secondary],
        "archived_count": len(report.archived),
        "failures": report.failures,
    }
    path = root / "reports" / "prefilter_latest.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "reports" / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = root / "reports" / "prefilter_latest.md"
    lines = ["# Deterministic Prefilter View", "", "PREFILTER_ONLY_NOT_FINAL", "", f"High priority: {len(report.high_priority)}", f"Secondary: {len(report.secondary)}", ""]
    for item in report.high_priority + report.secondary:
        lines.extend([f"## {item.candidate.name}", f"- Decision: `{item.decision}`", f"- Route: `{item.primary_route}`", f"- Score: `{item.total}`", f"- Why: {item.incremental_value}", ""])
    if report.failures:
        lines.extend(["## Run Status", "- `DISCOVERY_NOT_EVALUATED` occurred for at least one query."])
    markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "reports" / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
