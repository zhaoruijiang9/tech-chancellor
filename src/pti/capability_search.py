import re
from pathlib import Path
from typing import Any

from .capability_library import _card, _read_rows


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_]{3,}", value or "")}


def _is_local_maintenance_request(problem: str, task_context: str) -> bool:
    text = " ".join((problem, task_context)).lower()
    markers = (
        "typo", "spelling", "rename", "formatting", "format a ", "git status",
        "simple local maintenance", "known file", "deterministic calculation",
        "arithmetic", "local formatting",
    )
    return any(marker in text for marker in markers)


def search_capabilities(db_path: str | Path, *, problem: str, task_context: str,
                        project_context: str, current_capabilities: list[str],
                        constraints: list[str], limit: int = 3, project_label: str = "") -> dict[str, Any]:
    limit = max(0, min(3, int(limit)))
    if _is_local_maintenance_request(problem, task_context):
        return {"status": "NO_MATCH", "project_label": project_label, "results": []}
    rows = _read_rows(db_path)
    query_tokens = _tokens(" ".join([problem, task_context, project_context]))
    current_tokens = _tokens(" ".join(current_capabilities))
    constraint_tokens = _tokens(" ".join(constraints))
    ranked = []
    for row in rows:
        card = _card(dict(row))
        if card["semantic_action"] in {"IGNORE", "NOT_EVALUATED"}:
            continue
        text = " ".join(str(card[field]) for field in ("capability_name", "problem_solved", "capability_delta", "best_route"))
        terms = _tokens(text)
        overlap = len(query_tokens & terms)
        duplication = len(current_tokens & terms)
        conflict = len(constraint_tokens & _tokens(str(card["limitations"])))
        score = overlap * 10 - duplication * 4 - conflict * 8
        if overlap or not query_tokens:
            card["matched_problem"] = problem
            card["relation_to_current_capabilities"] = "OVERLAP_REQUIRES_COMPARISON" if duplication else "POTENTIAL_INCREMENT"
            card["incremental_value"] = card["capability_delta"]
            card["constraint_fit"] = "CONFLICT" if conflict else "NO_KNOWN_CONFLICT"
            card["why_ranked"] = f"token_overlap={overlap}; current_overlap={duplication}; constraint_conflict={conflict}"
            ranked.append((score, card))
    ranked.sort(key=lambda item: (-item[0], item[1]["repository"]))
    results = [card for _, card in ranked[:limit]]
    return {"status": "MATCH" if results else "NO_MATCH", "project_label": project_label,
            "results": results}
