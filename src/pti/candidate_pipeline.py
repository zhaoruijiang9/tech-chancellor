"""Shared candidate admission, durable review handoff, and bounded recovery."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .capability_invocation import normalize_github_link, relevant_to_intent
from .models import utc_now
from .policy import Candidate, Evaluation, decide_candidate, score_candidate
from .review_queue import REVIEW_REASONS, fingerprint


STAGE_LABELS = {
    "DISCOVERED": "已发现", "EVIDENCE_READY": "取证已完成",
    "LOCALLY_SCREENED": "初步语义筛选已完成", "WAITING_CHANCELLOR": "等待 Chancellor 最终评审",
    "CHANCELLOR_DECIDED": "Chancellor 已作最终决定", "ADMISSION_REJECTED": "未通过候选准入",
}


def candidate_admission(item: Evaluation) -> dict:
    candidate = item.candidate
    reasons = []
    name = normalize_github_link(candidate.url)
    if not isinstance(candidate.github_repository_id, int) or candidate.github_repository_id <= 0 or name != candidate.name:
        reasons.append("IDENTITY_NOT_RESOLVED")
    if not item.intent_relevant:
        reasons.append("INTENT_MISMATCH")
    if not candidate.readme.strip():
        reasons.append("MISSING_README")
    if item.total < 24 or item.priority not in {"HIGH_PRIORITY", "SECONDARY"} or item.decision in {"IGNORE", "ARCHIVE", "REFERENCE_ONLY"}:
        reasons.append("BELOW_QUALITY_THRESHOLD")
    if not item.semantic_review:
        reasons.append("LOCAL_SCREENING_MISSING")
    if item.review_reason not in REVIEW_REASONS:
        reasons.append("NO_FINAL_REVIEW_DUE")
    return {"admitted": not reasons, "reasons": reasons, "dedup_key": candidate.github_repository_id,
            "risk_review_required": candidate.security_risk >= 4}


def _event(db, repository_id: int, event: str, reference: str, detail: str) -> None:
    with db._connect() as connection:
        connection.execute("""INSERT OR IGNORE INTO candidate_pipeline_events
            (github_repository_id,event,reference,detail,created_at) VALUES (?,?,?,?,?)""",
            (repository_id, event, reference, detail[:1000], utc_now()))


def persist_candidate(db, item: Evaluation, scan_run_id: str | None) -> dict:
    admission = candidate_admission(item)
    repository_id = item.candidate.github_repository_id
    if repository_id is None:
        return admission
    payload = asdict(item)
    payload["candidate"]["readme"] = item.candidate.readme[:6000]
    payload["repository_evidence"] = {**item.repository_evidence, "readme": item.candidate.readme[:6000],
        "tree_paths": item.repository_evidence.get("tree_paths", [])[:100]}
    review_hash = fingerprint({"identity": repository_id, "description": item.candidate.description,
                               "readme": payload["candidate"]["readme"]})
    now = utc_now()
    with db._connect() as connection:
        old = connection.execute("SELECT * FROM canonical_candidates WHERE github_repository_id=?", (repository_id,)).fetchone()
        sources = (json.loads(old["provenance_json"]) if old else []) + item.source_provenance
        merged = {}
        for source in sources:
            key = tuple(str(source.get(name, "")) for name in
                        ("source_type", "source_id", "scan_id", "source_query"))
            merged[key] = source
        provenance = list(merged.values())[-32:]
        payload["source_provenance"] = provenance
        rereview = old and old["stage"] == "CHANCELLOR_DECIDED" and item.review_reason in {"USER_REQUESTED", "MATERIAL_EVIDENCE_CHANGED", "WATCH_DUE"}
        if old and (old["stage"] == "WAITING_CHANCELLOR" or
                    (old["review_fingerprint"] == review_hash and old["stage"] != "ADMISSION_REJECTED" and not rereview)):
            connection.execute("UPDATE canonical_candidates SET provenance_json=? WHERE github_repository_id=?",
                               (json.dumps(provenance, ensure_ascii=False), repository_id))
            return json.loads(old["admission_json"])
        if old and old["stage"] == "CHANCELLOR_DECIDED" and item.review_reason not in {"USER_REQUESTED", "MATERIAL_EVIDENCE_CHANGED", "WATCH_DUE"}:
            return json.loads(old["admission_json"])
        if rereview:
            final = connection.execute("SELECT imported_at FROM chancellor_decisions WHERE github_repository_id=?", (repository_id,)).fetchone()
            review_hash = fingerprint({"evidence": review_hash, "review_reason": item.review_reason,
                                       "previous_final_at": final[0] if final else old["updated_at"]})
        stage = "LOCALLY_SCREENED" if admission["admitted"] else "ADMISSION_REJECTED"
        connection.execute("""INSERT INTO canonical_candidates
            (github_repository_id,scan_run_id,evaluation_json,provenance_json,admission_json,
             review_fingerprint,stage,screened_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(github_repository_id) DO UPDATE SET scan_run_id=excluded.scan_run_id,
            evaluation_json=excluded.evaluation_json,provenance_json=excluded.provenance_json,
            admission_json=excluded.admission_json,review_fingerprint=excluded.review_fingerprint,
            stage=excluded.stage,packet_name=NULL,screened_at=excluded.screened_at,updated_at=excluded.updated_at""",
            (repository_id, scan_run_id, json.dumps(payload, ensure_ascii=False), json.dumps(provenance, ensure_ascii=False),
             json.dumps(admission), review_hash, stage, now, now))
    if item.semantic_review:
        _event(db, repository_id, "LOCALLY_SCREENED", scan_run_id or review_hash, "初步语义筛选；尚非最终决定")
    if admission["admitted"]:
        _event(db, repository_id, "ADMITTED", scan_run_id or review_hash, "身份、意图、README 和质量门槛已核对")
    return admission


def restore_evaluation(row) -> Evaluation:
    payload = json.loads(row["evaluation_json"])
    payload["candidate"] = Candidate(**payload["candidate"])
    payload["source_provenance"] = json.loads(row["provenance_json"])
    return Evaluation(**payload)


def review_backlog(db) -> list[Evaluation]:
    with db._connect() as connection:
        rows = connection.execute("SELECT * FROM canonical_candidates WHERE stage='LOCALLY_SCREENED' ORDER BY screened_at,github_repository_id").fetchall()
    return [restore_evaluation(row) for row in rows]


def find_existing_packet(root: Path, repository_id: int, *, active_only: bool = False) -> Path | None:
    for path in sorted((root / "chancellor_pending").glob("*.json")):
        if active_only and ".processed" in path.stem:
            continue
        try:
            packet = json.loads(path.read_text(encoding="utf-8"))
            if int(packet.get("repository_identity", {}).get("github_repository_id", -1)) == repository_id:
                return path
        except (OSError, ValueError, TypeError):
            continue
    return None


def record_handoff(db, repository_id: int, packet_name: str) -> None:
    with db._connect() as connection:
        connection.execute("UPDATE canonical_candidates SET stage='WAITING_CHANCELLOR',packet_name=?,updated_at=? WHERE github_repository_id=?",
                           (packet_name, utc_now(), repository_id))
    _event(db, repository_id, "WAITING_CHANCELLOR", packet_name, "已进入正式 Chancellor 待评审队列")


def candidate_hypotheses(item: Evaluation, db) -> list[dict]:
    text = (item.candidate.description + " " + item.candidate.readme[:3000]).lower()
    terms = {"SKILL_ECOSYSTEM_DISCOVERY": ("skill index", "skills catalog", "awesome skills"),
             "AGENT_WORKFLOW_ORCHESTRATION": ("workflow", "multi-agent"),
             "CONTEXT_COMPRESSION": ("compression", "compress"),
             "REPOSITORY_CONTEXT_MAPPING": ("codebase", "repository map"),
             "STRUCTURED_DEVELOPMENT_WORKFLOW": ("development workflow", "code review")}
    with db._connect() as connection:
        known = {row[0] for row in connection.execute("SELECT capability_id FROM capabilities")}
    return [{"capability_id": key, "status": "UNVERIFIED_HYPOTHESIS", "evidence": "bounded README/description term match"}
            for key, signals in terms.items() if key in known and any(word in text for word in signals)]


def build_stage_b_packet(item: Evaluation, db, scan_run_id: str | None) -> dict:
    root = db.path.parent.parent
    profile_path = root / "config/local_capability_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.is_file() else {}
    hypotheses = candidate_hypotheses(item, db)
    ids = {entry["capability_id"] for entry in hypotheses}
    with db._connect() as connection:
        relations = [dict(row) for row in connection.execute("SELECT * FROM capability_relations")
                     if row["from_capability_id"] in ids or row["to_capability_id"] in ids][:12]
    return {
        "repository_identity": {"github_repository_id": item.candidate.github_repository_id,
                                "canonical_owner_repo": item.candidate.name, "url": item.candidate.url},
        "discovery_domain": item.primary_route,
        "metadata": {"description": item.candidate.description[:1000], "stars": item.candidate.stars},
        "source_provenance": item.source_provenance,
        "repository_evidence": {**item.repository_evidence, "readme": item.candidate.readme[:6000],
                                "tree_paths": item.repository_evidence.get("tree_paths", [])[:100]},
        "semantic_review": item.semantic_review, "local_review_stage": "PRELIMINARY_EVIDENCE_SCREENING",
        "deterministic_score": {"total": item.total, "components": item.score_components},
        "capability_hypotheses": hypotheses, "capability_overlap_hints": item.capability_delta,
        "existing_capability_relations": relations, "local_capability_profile": profile,
        "security_signals": item.risk_flags, "external_text_is_untrusted_evidence": True,
        "source_failures": [value for value in item.evidence if value.startswith("enrichment_failure=")],
        "status": "PENDING_CODEX_REVIEW", "scan_run_id": scan_run_id, "review_reason": item.review_reason,
        "candidate_admission": candidate_admission(item),
    }


def stranded_candidate_summary(root: str | Path) -> dict:
    root = Path(root)
    path = root / "state/intelligence.db"
    if not path.exists():
        return {"count": 0, "records": []}
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("""SELECT r.github_repository_id,r.canonical_owner_repo,
            o.scan_run_id,o.observed_at,o.enrichment_level
            FROM repositories r JOIN candidate_observations o USING(github_repository_id)
            WHERE o.id=(SELECT max(o2.id) FROM candidate_observations o2 WHERE o2.github_repository_id=r.github_repository_id)
            AND o.enrichment_level IS NOT NULL AND o.priority IN ('HIGH_PRIORITY','SECONDARY')
            AND NOT EXISTS(SELECT 1 FROM chancellor_decisions d WHERE d.github_repository_id=r.github_repository_id)""").fetchall()
        records = []
        for row in rows:
            if find_existing_packet(root, row["github_repository_id"]) is None:
                records.append(dict(row))
        return {"count": len(records), "records": records, "interpretation": "Evidence-ready historical observations; admission must be reverified individually"}
    finally:
        connection.close()


def repair_stranded_candidates(root: str | Path, repository_name: str, *, dry_run: bool = True, client=None) -> dict:
    from .chancellor import LocalSemanticChancellor, build_review_packet
    from .storage import Database
    from .reporting import write_chancellor_pending
    root = Path(root).resolve()
    db = Database(root / "state/intelligence.db")
    record = db.get_repository_by_name(repository_name)
    if record is None:
        return {"status": "NOT_FOUND"}
    repository_id = record.github_repository_id
    if db.has_current_semantic_decision(repository_id):
        return {"status": "ALREADY_DECIDED", "repository": repository_name}
    packet = find_existing_packet(root, repository_id)
    if packet:
        return {"status": "ALREADY_PENDING", "packet": str(packet)}
    with db._connect() as connection:
        row = connection.execute("SELECT * FROM canonical_candidates WHERE github_repository_id=?", (repository_id,)).fetchone()
        observations = connection.execute("SELECT * FROM candidate_observations WHERE github_repository_id=? ORDER BY id DESC", (repository_id,)).fetchall()
        invocations = connection.execute("SELECT * FROM capability_invocations ORDER BY id DESC").fetchall()
    item = restore_evaluation(row) if row else None
    if item and not item.candidate.readme.strip():
        item = None
    if item is None:
        observation = next((entry for entry in observations if entry["enrichment_level"]), None)
        if observation is None or observation["priority"] not in {"HIGH_PRIORITY", "SECONDARY"}:
            return {"status": "NOT_ELIGIBLE", "reason": "NO_PRIOR_EVIDENCE_READY_OBSERVATION"}
        if dry_run:
            return {"status": "REPAIR_NEEDS_EVIDENCE_REFRESH", "repository": repository_name,
                    "scan_id": observation["scan_run_id"], "reason": "Legacy path did not persist bounded README/local screening"}
        if client is None:
            raise ValueError("legacy repair requires a bounded evidence client")
        owner, repo = record.canonical_owner_repo.split("/", 1)
        evidence = client.enrich_repository(owner, repo, level="STANDARD", text_limit=6000)
        profile_path = root / "config/local_capability_profile.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8")) if profile_path.is_file() else {}
        domain = observation["discovery_domain"]
        item = decide_candidate(score_candidate(Candidate(record.canonical_owner_repo, record.description, [domain],
            record.stars, 0, 4, 4, 1, evidence.readme, record.url, repository_id), profile))
        item.review_reason = "FIRST_REVIEW"
        item.repository_evidence = evidence.to_dict()
        item.semantic_review = LocalSemanticChancellor().review(build_review_packet(asdict(item.candidate),
            {"score_total": item.total}, profile, [], evidence.to_dict()))
        item.source_provenance = []
        for observation_entry in observations[:16]:
            query = observation_entry["source_query"]
            invocation = next((entry for entry in invocations if entry["task_run_id"] == observation_entry["scan_run_id"]
                and repository_id in json.loads(entry["downstream_effect_json"]).get("new_candidate_ids", [])), None)
            if invocation and query.startswith("capability:"):
                binding_path = root / "config/capability_consumers.json"
                bindings = json.loads(binding_path.read_text(encoding="utf-8"))["bindings"] if binding_path.exists() else []
                binding = next((value for value in bindings if value["implementation_id"] == invocation["implementation_id"]), None)
                intent = query.rsplit(":", 1)[-1]
                item.intent_relevant = item.intent_relevant and bool(binding and relevant_to_intent(binding, intent, record.canonical_owner_repo, record))
                item.source_provenance.append({"source_type": "CAPABILITY", "source_id": invocation["implementation_id"],
                    "capability_id": invocation["capability_id"], "implementation_id": invocation["implementation_id"],
                    "consumer": invocation["consumer"], "scan_id": observation_entry["scan_run_id"], "source_query": query,
                    "index_source": "https://github.com/" + invocation["implementation_id"].removeprefix("impl:"),
                    "evidence_refresh": "CURRENT_BOUNDED_REFRESH_NOT_HISTORICAL_README", "refreshed_at": utc_now()})
            else:
                item.source_provenance.append({"source_type": "GITHUB_RADAR", "source_id": "GITHUB_RADAR",
                    "scan_id": observation_entry["scan_run_id"], "source_query": query})
        persist_candidate(db, item, observation["scan_run_id"])
    admission = candidate_admission(item)
    if not admission["admitted"]:
        return {"status": "NOT_ELIGIBLE", "admission": admission}
    if dry_run:
        return {"status": "REPAIR_READY", "repository": repository_name, "admission": admission}
    paths = write_chancellor_pending(root, [item], row["scan_run_id"] if row else observation["scan_run_id"], limit=1, include_backlog=False)
    if not paths:
        return {"status": "NOT_RESUMED"}
    _event(db, repository_id, "REPAIR_APPLIED", paths[0].name, "单候选恢复；复用正式包构建器；没有重写或新增发现观测")
    return {"status": "RESUMED", "repository": repository_name, "admission": admission, "packet": str(paths[0])}


def project_final_decision(db, repository_id: int, decision: dict, packet: dict) -> dict:
    """Project reviewed identities without claiming installation or real use."""
    from .capability_intelligence import CapabilityStore
    record = db.get_repository(repository_id)
    if record is None:
        raise ValueError("REPOSITORY_NOT_FOUND")
    store = CapabilityStore(db.path)
    source_id = f"github:{repository_id}"
    implementation_id = f"impl:{record.canonical_owner_repo}"
    action = decision["ACTION"]
    lifecycle = {"WATCH": "WATCH", "REFERENCE_ONLY": "REFERENCE_ONLY", "IGNORE": "REJECTED",
                 "ARCHIVE": "ARCHIVED", "USER_REVIEW_RECOMMENDED": "HUMAN_GATE"}.get(action, "WAITING_VALIDATION")
    with db._connect() as connection:
        existing = connection.execute("SELECT lifecycle_state FROM capability_implementations WHERE implementation_id=?", (implementation_id,)).fetchone()
    if existing and existing[0] in {"AVAILABLE", "USED"}:
        lifecycle = existing[0]
    store.upsert_source(source_id, "GITHUB_REPOSITORY", record.canonical_owner_repo, record.url, repository_id)
    store.upsert_implementation(implementation_id, source_id, record.canonical_owner_repo.rsplit("/", 1)[-1],
                                "TOOL_OR_WORKFLOW", lifecycle)
    evidence = f"chancellor:{packet.get('scan_run_id', '')}:{repository_id}:{action}"
    with db._connect() as connection:
        known = {row[0] for row in connection.execute("SELECT capability_id FROM capabilities")}
    for hypothesis in packet.get("capability_hypotheses", [])[:12]:
        capability_id = hypothesis.get("capability_id")
        if capability_id in known:
            store.link_implementation_capability(implementation_id, capability_id, "OVERLAP",
                evidence + ":UNVERIFIED_CAPABILITY_HYPOTHESIS;" + decision.get("CAPABILITY_DELTA", "")[:500])
    state = "WATCHLIST" if action in {"WATCH", "CANDIDATE_FOR_QUARANTINE"} else "KNOWLEDGE_REFERENCE" if action == "REFERENCE_ONLY" else "HUMAN_GATE" if action == "USER_REVIEW_RECOMMENDED" else "NOT_ADOPTED"
    store.set_personal_state("IMPLEMENTATION", implementation_id, state, evidence)
    return {"source_id": source_id, "implementation_id": implementation_id, "lifecycle": lifecycle}


def stalled_candidates(root: str | Path, max_age_seconds: int = 86400) -> list[dict]:
    root = Path(root)
    path = root / "state/intelligence.db"
    if not path.exists():
        return []
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='canonical_candidates'").fetchone():
            return []
        rows = connection.execute("""SELECT c.*,r.canonical_owner_repo FROM canonical_candidates c
            JOIN repositories r USING(github_repository_id)
            WHERE c.stage IN ('LOCALLY_SCREENED','WAITING_CHANCELLOR')
            AND NOT EXISTS(SELECT 1 FROM chancellor_decisions d WHERE d.github_repository_id=c.github_repository_id)""").fetchall()
        now = datetime.now(timezone.utc)
        stalled = []
        for row in rows:
            age = (now - datetime.fromisoformat(row["screened_at"].replace("Z", "+00:00"))).total_seconds()
            if age > max_age_seconds and find_existing_packet(root, row["github_repository_id"]) is None:
                stalled.append({"repository": row["canonical_owner_repo"], "age_seconds": int(age)})
        return stalled
    finally:
        connection.close()
