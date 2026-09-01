import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .capability_library import _card


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9_]{3,}", value or "")}


def search_capabilities(db_path: str | Path, *, problem: str, task_context: str,
                        project_context: str, current_capabilities: list[str],
                        constraints: list[str], limit: int = 3, project_label: str = "") -> dict[str, Any]:
    limit = max(0, min(3, int(limit)))
    connection = sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("""select r.canonical_owner_repo,r.url,r.description,r.stars,r.topics,
            d.decision_json,d.imported_at from repositories r join chancellor_decisions d
            on d.github_repository_id=r.github_repository_id order by r.canonical_owner_repo""").fetchall()
    finally:
        connection.close()
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
