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


def write_chancellor_pending(root: str | Path, decisions: list[Evaluation], run_id: str | None = None) -> list[Path]:
    root = Path(root).resolve() / "chancellor_pending"
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for decision in allocate_review_slots(decisions, 3):
        if not decision.semantic_review:
            continue
        packet_id = run_id or uuid.uuid4().hex[:10]
        name = decision.candidate.name.replace("/", "--") + "--" + packet_id + ".json"
        path = root / name
        payload = {
            "repository_identity": {"github_repository_id": decision.candidate.github_repository_id,
                                    "canonical_owner_repo": decision.candidate.name, "url": decision.candidate.url},
            "discovery_domain": decision.primary_route,
            "metadata": {"description": decision.candidate.description, "stars": decision.candidate.stars},
            "semantic_review": decision.semantic_review,
            "deterministic_score": {"total": decision.total, "components": decision.score_components},
            "capability_overlap_hints": decision.capability_delta,
            "security_signals": decision.risk_flags,
            "source_failures": [item for item in decision.evidence if item.startswith("enrichment_failure=")],
            "status": "PENDING_CODEX_REVIEW",
            "scan_run_id": run_id,
            "review_reason": decision.review_reason,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
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
