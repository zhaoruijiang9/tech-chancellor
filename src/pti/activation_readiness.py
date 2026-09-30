"""Evidence-bounded, independent readiness audit for known library implementations."""

from __future__ import annotations

from collections import Counter

from .capability_intelligence import CapabilityStore


READINESS_CATEGORIES = {
    "READY_WITH_EXISTING_ADAPTER", "NEEDS_SAFE_ADAPTER", "REQUIRES_OS_SANDBOX",
    "HUMAN_GATE", "NO_MEANINGFUL_DELTA", "WAITING_UPSTREAM_CHANGE",
    "NOT_WORTH_ACTIVATING",
}


def audit_current_library(db, classifications: dict[str, dict] | None = None) -> dict:
    with db._connect() as connection:
        rows = connection.execute("""SELECT i.implementation_id,s.canonical_name,
            COALESCE(a.activation_state,'') activation_state
            FROM capability_implementations i JOIN capability_sources s USING(source_id)
            LEFT JOIN activation_records a ON a.github_repository_id=s.github_repository_id
            WHERE NOT EXISTS (SELECT 1 FROM personal_states p WHERE p.subject_type='IMPLEMENTATION'
                              AND p.subject_id=i.implementation_id AND p.state='USED')
            ORDER BY i.implementation_id""").fetchall()
        active_ids = {row["implementation_id"] for row in rows}
        if classifications is None:
            classifications = {row["implementation_id"]: dict(row) for row in
                               connection.execute("SELECT * FROM activation_readiness")}
        for stale in connection.execute("SELECT implementation_id FROM activation_readiness").fetchall():
            if stale[0] not in active_ids:
                connection.execute("DELETE FROM activation_readiness WHERE implementation_id=?", (stale[0],))
    unclassified = []
    counts = Counter()
    for row in rows:
        implementation_id = row["implementation_id"]
        decision = classifications.get(implementation_id)
        if decision is None:
            unclassified.append(implementation_id)
            continue
        category = decision.get("category")
        blocker = str(decision.get("blocker") or "").strip()
        if category not in READINESS_CATEGORIES or not blocker:
            raise ValueError(f"invalid readiness evidence for {implementation_id}")
        with db._connect() as connection:
            connection.execute("""INSERT INTO activation_readiness(implementation_id,category,blocker)
                VALUES (?,?,?) ON CONFLICT(implementation_id) DO UPDATE SET
                category=excluded.category,blocker=excluded.blocker,audited_at=CURRENT_TIMESTAMP""",
                (implementation_id, category, blocker[:1000]))
        counts[category] += 1
    if counts["REQUIRES_OS_SANDBOX"] >= 2:
        store = CapabilityStore(db.path)
        store.upsert_capability("SECURE_THIRD_PARTY_EXECUTION_SANDBOX", "安全第三方执行沙箱",
                                "隔离执行第三方代码所需的 OS 级能力；当前缺失")
        store.set_personal_state("CAPABILITY", "SECURE_THIRD_PARTY_EXECUTION_SANDBOX",
                                 "MISSING_CAPABILITY", "activation-readiness-audit")
    return {"audited": sum(counts.values()), "unclassified": unclassified, "counts": dict(counts)}


def second_pilot_candidates(db) -> list[str]:
    with db._connect() as connection:
        rows = connection.execute("""SELECT r.implementation_id FROM activation_readiness r
            JOIN capability_implementations i USING(implementation_id)
            JOIN capability_sources s USING(source_id)
            LEFT JOIN activation_records a ON a.github_repository_id=s.github_repository_id
            WHERE r.category='READY_WITH_EXISTING_ADAPTER'
            AND COALESCE(a.activation_state,'') NOT IN ('TRIAL_ENABLED','USED','BLOCKED_HUMAN')
            AND EXISTS (SELECT 1 FROM personal_states p WHERE p.subject_type='IMPLEMENTATION'
                        AND p.subject_id=i.implementation_id AND p.state='WATCHLIST')
            ORDER BY r.implementation_id""").fetchall()
    return [row[0] for row in rows]
