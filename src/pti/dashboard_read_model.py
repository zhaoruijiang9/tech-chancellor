import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .capability_library import _card, _read_rows
from .health import health_report
from .human_library import load_human_library_evidence, project_human_library_item
from .human_toolbox import _with_usage


LIFECYCLE_LABELS = {
    "DISCOVERED": "最近发现",
    "REVIEW": "待判断",
    "WAITING_VALIDATION": "已批准，等待验证",
    "VALIDATING": "正在验证",
    "QUARANTINE_READY": "正在验证",
    "TRIAL_ENABLED": "已安装，可使用",
    "USED": "已经实际使用",
    "ACTIVE_PATTERN": "知识库 / 方法参考",
    "REFERENCE_ONLY": "知识库 / 方法参考",
    "KEEP_REFERENCE_ONLY": "已研究，暂不采用",
    "TESTED_NOT_ADOPTED": "已研究，暂不采用",
    "BLOCKED_HUMAN": "需要人工决定",
    "FAILED_WITH_EXPLAINED_REASON": "验证失败 / 暂不采用",
    "FAILED_TERMINAL": "验证失败 / 暂不采用",
}

DOC_ROOTS = {"docs", "reports", "library/generated"}
ROOT_DOCUMENTS = {
    "README.md",
    "README.zh-CN.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "MY_CAPABILITIES.md",
}
HUMAN_DECISION_LABELS = {"APPROVE_FOR_REVIEW", "WATCH", "NOT_USEFUL", "TOO_RISKY"}
ACTIVATION_PHASE_LABELS = {
    "QUEUED": "候选已选中", "PLAN_READY": "准备隔离验证", "SOURCE_PINNED": "来源版本已固定",
    "QUARANTINED": "静态检查", "STATIC_ANALYSIS_PASS": "建立隔离环境",
    "ISOLATED_INSTALL_PASS": "安装测试", "FUNCTIONAL_TEST_PASS": "能力评估",
    "EVALUATION_PASS": "准备启用", "AVAILABLE": "已验证可用",
    "EVALUATION_NO_DELTA": "无明确增益",
}


def _parse_time(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("+00:00", "Z")


def _json(value: Any, default: Any = None) -> Any:
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default


def _safe_date_sort(value: str | None) -> str:
    return value or ""


def _human_activity_status(value: str | None) -> str:
    mapping = {
        "SCAN_SUCCESS": "扫描完成",
        "SCAN_NOT_EVALUATED": "扫描需要注意",
        "SCAN_SUCCESS_NO_HIGH_SIGNAL": "扫描完成，无高信号结果",
        "REFERENCE_ONLY": "知识库 / 方法参考",
        "CANDIDATE_FOR_QUARANTINE": "进入验证",
        "ACTIVE_PATTERN": "已启用的方法",
        "USED": "已经实际使用",
        "BLOCKED_HUMAN": "需要人工决定",
        "FAILED_WITH_EXPLAINED_REASON": "验证失败 / 暂不采用",
        "FAILED_TERMINAL": "验证失败 / 暂不采用",
    }
    return mapping.get(value or "", LIFECYCLE_LABELS.get(value or "", value or "暂无"))


class DashboardReadModel:
    """Read-only projection over the existing PTI SQLite state."""

    def __init__(self, root: str | Path, db_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.db_path = Path(db_path or self.root / "state" / "intelligence.db").resolve()

    def _connection(self) -> sqlite3.Connection | None:
        if not self.db_path.is_file():
            return None
        try:
            connection = sqlite3.connect(f"file:{self.db_path.as_posix()}?mode=ro", uri=True)
            connection.row_factory = sqlite3.Row
            return connection
        except sqlite3.Error:
            return None

    def _table_exists(self, connection: sqlite3.Connection, name: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone() is not None

    def _source_intelligence(self, connection: sqlite3.Connection, repository_id: int) -> dict[str, Any]:
        if not self._table_exists(connection, "capability_sources"):
            return {}
        source = connection.execute(
            "SELECT * FROM capability_sources WHERE github_repository_id=?", (repository_id,)
        ).fetchone()
        if source is None:
            return {}
        source_id = source["source_id"]
        mappings = [dict(row) for row in connection.execute("""
            SELECT c.capability_id,c.name,m.delta_kind,m.evidence_ref,
                   i.implementation_id,i.name implementation_name
            FROM capability_implementations i
            JOIN implementation_capabilities m USING(implementation_id)
            JOIN capabilities c USING(capability_id)
            WHERE i.source_id=? ORDER BY c.capability_id
        """, (source_id,))]
        freshness = connection.execute(
            "SELECT * FROM source_freshness WHERE source_id=?", (source_id,)
        ).fetchone()
        review = connection.execute(
            """SELECT review_outcome,review_evidence,reviewed_at FROM delta_review_queue
            WHERE source_id=? AND status='REVIEWED' ORDER BY id DESC LIMIT 1""", (source_id,)
        ).fetchone()
        return {
            "source_id": source_id,
            "source_type": source["source_type"],
            "capability_mappings": mappings,
            "source_freshness": dict(freshness) if freshness else None,
            "latest_delta_review": dict(review) if review else None,
        }

    def _entity_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        connection = self._connection()
        if connection is None:
            return {"capability_entities": [], "method_entities": [], "stale_reviews": []}
        try:
            if not self._table_exists(connection, "capabilities"):
                return {"capability_entities": [], "method_entities": [], "stale_reviews": []}
            capabilities = []
            has_activation_records = self._table_exists(connection, "activation_records")
            pinned_column = "a.pinned_version" if has_activation_records else "NULL AS pinned_version"
            activation_join = (
                "LEFT JOIN activation_records a ON a.github_repository_id=s.github_repository_id"
                if has_activation_records else ""
            )
            for row in connection.execute("SELECT * FROM capabilities ORDER BY name"):
                item = dict(row)
                item["personal_states"] = [record[0] for record in connection.execute(
                    """SELECT state FROM personal_states WHERE subject_type='CAPABILITY'
                    AND subject_id=? ORDER BY state""", (row["capability_id"],)
                )]
                item["implementations"] = [dict(record) for record in connection.execute(f"""
                    SELECT i.implementation_id,i.name,i.implementation_type,i.lifecycle_state,
                           s.canonical_name source_name,s.url source_url,
                           {pinned_column},f.current_release_tag,f.reviewed_release_tag,
                           f.review_freshness,f.last_upstream_check
                    FROM implementation_capabilities m
                    JOIN capability_implementations i USING(implementation_id)
                    LEFT JOIN capability_sources s USING(source_id)
                    {activation_join}
                    LEFT JOIN source_freshness f USING(source_id)
                    WHERE m.capability_id=? ORDER BY i.implementation_id
                """, (row["capability_id"],))]
                if any(state in {"OWNED", "AVAILABLE", "USED"} for state in item["personal_states"]):
                    capabilities.append(item)
            methods = []
            for row in connection.execute("""
                SELECT m.*,s.canonical_name source_name,s.url source_url
                FROM methods m LEFT JOIN capability_sources s USING(source_id)
                ORDER BY m.name
            """):
                item = dict(row)
                evidence_types = {record[0] for record in connection.execute("""
                    SELECT evidence_type FROM method_evidence
                    WHERE method_id=? AND qualifies=1
                """, (row["method_id"],))}
                if {"WORKFLOW_MECHANISM", "VERIFIED_USE"}.issubset(evidence_types):
                    methods.append(item)
            stale = []
            if self._table_exists(connection, "delta_review_queue"):
                stale = [dict(row) for row in connection.execute("""
                    SELECT q.id,q.source_id,q.trigger_reason,q.change_summary,q.suggested_outcome,
                           q.review_attempts,q.review_error,q.created_at,
                           q.old_head_sha,q.new_head_sha,q.old_release_tag,q.new_release_tag,
                           s.canonical_name source_name,s.github_repository_id,
                           f.review_freshness
                    FROM delta_review_queue q JOIN capability_sources s USING(source_id)
                    LEFT JOIN source_freshness f USING(source_id)
                    WHERE q.status='PENDING' ORDER BY q.created_at DESC,q.id DESC
                """)]
            return {
                "capability_entities": capabilities,
                "method_entities": methods,
                "stale_reviews": stale,
            }
        finally:
            connection.close()

    def capabilities(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        if not self.db_path.is_file():
            return []
        try:
            rows = _read_rows(self.db_path)
        except (OSError, sqlite3.Error, json.JSONDecodeError):
            return []
        latest_feedback, activation_queues = load_human_library_evidence(self.db_path)
        method_adoption: dict[int, str] = {}
        source_intelligence: dict[int, dict[str, Any]] = {}
        connection = self._connection()
        if connection is not None:
            try:
                if self._table_exists(connection, "methods") and self._table_exists(connection, "method_evidence"):
                    method_rows = connection.execute("""
                        SELECT s.github_repository_id,
                               MAX(CASE WHEN mechanism.evidence_type IS NOT NULL
                                         AND used.evidence_type IS NOT NULL THEN 1 ELSE 0 END) adopted
                        FROM methods m
                        JOIN capability_sources s ON s.source_id=m.source_id
                        LEFT JOIN method_evidence mechanism ON mechanism.method_id=m.method_id
                          AND mechanism.evidence_type='WORKFLOW_MECHANISM' AND mechanism.qualifies=1
                        LEFT JOIN method_evidence used ON used.method_id=m.method_id
                          AND used.evidence_type='VERIFIED_USE' AND used.qualifies=1
                        GROUP BY s.github_repository_id
                    """).fetchall()
                    method_adoption = {
                        int(row["github_repository_id"]): "ADOPTED" if row["adopted"] else "KNOWLEDGE_REFERENCE"
                        for row in method_rows if row["github_repository_id"] is not None
                    }
                for row in rows:
                    repository_id = int(row["github_repository_id"])
                    source_intelligence[repository_id] = self._source_intelligence(connection, repository_id)
            finally:
                connection.close()
        cards = []
        for row in rows:
            card = _with_usage(self.root, _card(row))
            state = card.get("activation_state", "")
            feedback = latest_feedback.get(int(row["github_repository_id"]))
            human_decision = feedback if feedback and feedback.get("label") in HUMAN_DECISION_LABELS else None
            card["human_decision"] = human_decision
            card["method_adoption_state"] = method_adoption.get(int(row["github_repository_id"]))
            card.update(source_intelligence.get(int(row["github_repository_id"]), {}))
            card["entity_kind"] = "SOURCE"
            card = project_human_library_item(
                card,
                latest_feedback=human_decision,
                queue_records=activation_queues.get(int(row["github_repository_id"]), []),
            )
            card["requires_human_decision"] = card["human_action_required"]
            card["lifecycle_status"] = card["human_category_label"]
            card["updated_at"] = card.get("evidence_timestamp") or ""
            cards.append(card)
        filters = filters or {}
        query = filters.get("q", "").strip().lower()
        state = filters.get("state", "").strip()
        category = filters.get("category", "").strip()
        if query:
            cards = [card for card in cards if query in json.dumps(card, ensure_ascii=False).lower()]
        if state:
            cards = [card for card in cards if state in {
                card.get("human_category"), card.get("lifecycle_status"), card.get("activation_state")
            }]
        if category:
            cards = [card for card in cards if card.get("best_route") == category]
        return sorted(cards, key=lambda item: _safe_date_sort(item.get("updated_at")), reverse=True)

    def _repository_names(self, connection: sqlite3.Connection, ids: list[int]) -> dict[int, str]:
        if not ids or not self._table_exists(connection, "repositories"):
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = connection.execute(
            f"SELECT github_repository_id, canonical_owner_repo FROM repositories WHERE github_repository_id IN ({placeholders})",
            ids,
        ).fetchall()
        return {int(row[0]): row[1] for row in rows}

    def _recent_discoveries(self, connection: sqlite3.Connection, limit: int = 8) -> list[dict[str, Any]]:
        if not self._table_exists(connection, "candidate_observations"):
            return []
        rows = connection.execute("""
            SELECT o.github_repository_id, o.observed_at, o.discovery_domain, o.source_query,
                   o.priority, o.deterministic_decision, r.canonical_owner_repo, r.url,
                   r.description, r.previous_decision
            FROM candidate_observations o
            JOIN repositories r ON r.github_repository_id=o.github_repository_id
            ORDER BY o.observed_at DESC, o.id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [{
            "type": "discovery",
            "time": row["observed_at"],
            "repository": row["canonical_owner_repo"],
            "url": row["url"],
            "summary": row["description"] or "暂无项目简介",
            "source": row["discovery_domain"] or row["source_query"],
            "stage": LIFECYCLE_LABELS.get(row["previous_decision"] or "REVIEW", "待判断"),
            "priority": row["priority"],
            "decision": row["deterministic_decision"],
        } for row in rows]

    def _validating(self, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        if not self._table_exists(connection, "activation_queue"):
            return []
        rows = connection.execute("""
            SELECT q.*, r.canonical_owner_repo, r.url
            FROM activation_queue q LEFT JOIN repositories r
              ON r.github_repository_id=q.repository_id
            WHERE q.status IN ('PENDING','PROCESSING','RETRYABLE')
            ORDER BY q.created_at DESC, q.id DESC
        """).fetchall()
        return [{
            "repository": row["canonical_owner_repo"] or f"repository:{row['repository_id']}",
            "url": row["url"],
            "step": ACTIVATION_PHASE_LABELS.get(row["phase"], "等待验证") if row["status"] != "RETRYABLE" else "等待重试",
            "started_at": row["last_attempt_at"] or row["created_at"],
            "risk": row["activation_tier"],
            "result": row["failure_class"] or row["desired_next_state"],
            "status": row["status"],
        } for row in rows]

    def activity(self, limit: int = 30) -> list[dict[str, Any]]:
        connection = self._connection()
        if connection is None:
            return []
        try:
            events: list[dict[str, Any]] = []
            if self._table_exists(connection, "scan_runs"):
                for row in connection.execute("SELECT * FROM scan_runs ORDER BY started_at DESC LIMIT 20"):
                    raw_status = row["status"] or "运行中"
                    events.append({"type": "radar", "time": row["started_at"], "title": "Radar 扫描", "repository": "", "status": _human_activity_status(raw_status), "machine_status": raw_status, "detail": f"候选 {row['candidate_count']} 个，失败 {row['failure_count']} 个"})
            if self._table_exists(connection, "chancellor_decision_history"):
                rows = connection.execute("""
                    SELECT h.*, r.canonical_owner_repo, r.url
                    FROM chancellor_decision_history h LEFT JOIN repositories r
                      ON r.github_repository_id=h.github_repository_id
                    ORDER BY h.imported_at DESC, h.id DESC LIMIT 30
                """).fetchall()
                for row in rows:
                    decision = _json(row["decision_json"], {})
                    raw_status = decision.get("ACTION", "已判断")
                    events.append({"type": "chancellor", "time": row["imported_at"], "title": "Chancellor 判断", "repository": row["canonical_owner_repo"] or "未知项目", "url": row["url"], "status": _human_activity_status(raw_status), "machine_status": raw_status, "detail": decision.get("WHAT_IS_IT", "")})
            if self._table_exists(connection, "activation_records"):
                rows = connection.execute("""
                    SELECT a.*, r.canonical_owner_repo, r.url
                    FROM activation_records a LEFT JOIN repositories r
                      ON r.github_repository_id=a.github_repository_id
                    ORDER BY a.updated_at DESC LIMIT 30
                """).fetchall()
                for row in rows:
                    raw_status = row["activation_state"]
                    events.append({"type": "activation", "time": row["updated_at"], "title": "能力状态变化", "repository": row["canonical_owner_repo"] or "未知项目", "url": row["url"], "status": _human_activity_status(raw_status), "machine_status": raw_status, "detail": row["notes"] or ""})
            if self._table_exists(connection, "activation_queue"):
                rows = connection.execute("""SELECT q.*,r.canonical_owner_repo,r.url FROM activation_queue q
                    LEFT JOIN repositories r ON r.github_repository_id=q.repository_id
                    ORDER BY q.id DESC LIMIT 30""").fetchall()
                for row in rows:
                    phase = row["phase"]
                    events.append({"type": "activation", "time": row["updated_at"],
                        "title": "能力验证", "repository": row["canonical_owner_repo"] or "未知项目",
                        "url": row["url"], "status": ACTIVATION_PHASE_LABELS.get(phase, phase),
                        "machine_status": row["status"],
                        "detail": row["failure_class"] or ("阶段：" + phase)})
            events.sort(key=lambda item: _safe_date_sort(item.get("time")), reverse=True)
            return events[:max(1, limit)]
        finally:
            connection.close()

    def documents(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        candidates: list[Path] = []
        for name in ROOT_DOCUMENTS:
            candidates.append(self.root / name)
        for directory in DOC_ROOTS:
            path = self.root / directory
            if path.is_dir():
                candidates.extend(path.rglob("*.md"))
        for path in candidates:
            try:
                relative = path.resolve().relative_to(self.root).as_posix()
            except (OSError, ValueError):
                continue
            if path.is_file() and path.suffix.lower() == ".md" and self._is_allowed_document(relative):
                found.append({"path": relative, "title": self._title(path), "category": self._category(relative), "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")})
        return sorted({item["path"]: item for item in found}.values(), key=lambda item: (item["category"], item["title"].lower()))

    def document_text(self, relative_path: str) -> str:
        path = self._resolve_document(relative_path)
        return path.read_text(encoding="utf-8")

    def _is_allowed_document(self, relative_path: str) -> bool:
        normalized = relative_path.replace("\\", "/").lstrip("/")
        if normalized in ROOT_DOCUMENTS:
            return True
        return any(normalized == root or normalized.startswith(root + "/") for root in DOC_ROOTS)

    def _resolve_document(self, relative_path: str) -> Path:
        if not relative_path or Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise ValueError("document path is outside the approved documentation roots")
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise ValueError("document path is outside the project root") from error
        if not self._is_allowed_document(candidate.relative_to(self.root).as_posix()) or not candidate.is_file():
            raise FileNotFoundError("document is not an approved project document")
        return candidate

    @staticmethod
    def _title(path: Path) -> str:
        try:
            first = path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        except (OSError, IndexError):
            first = path.stem
        return first.lstrip("# ").strip() or path.stem

    @staticmethod
    def _category(relative: str) -> str:
        if relative.startswith("docs/"):
            return "产品文档"
        if "RELEASE" in relative.upper() or "PUBLIC" in relative.upper():
            return "发布文档"
        if relative.startswith("reports/") or relative.startswith("library/"):
            return "能力报告"
        if relative in {"README.md", "README.zh-CN.md", "CONTRIBUTING.md"}:
            return "产品文档"
        return "开发历史"

    def snapshot(self) -> dict[str, Any]:
        cards = self.capabilities()
        entities = self._entity_snapshot()
        owned_capabilities = entities["capability_entities"]
        adopted_methods = entities["method_entities"]
        stale_reviews = entities["stale_reviews"]
        categories = [card.get("human_category", "") for card in cards]
        validating = []
        recent = []
        connection = self._connection()
        if connection is not None:
            try:
                recent = self._recent_discoveries(connection)
                validating = self._validating(connection)
            finally:
                connection.close()
        health = health_report(self.root)
        return {
            "product": "TechChancellor",
            "name_zh": "技术丞相",
            "status": "异常" if health.get("status") == "NOT_EVALUATED" else "提醒" if str(health.get("status", "")).startswith("DEGRADED") else "正常",
            "health": health,
            "counts": {
                "total": len(cards),
                "reviewed_projects": len(cards),
                "usable": sum(any(state in {"AVAILABLE", "USED"} for state in item["personal_states"]) for item in owned_capabilities),
                "directly_usable": sum(any(state in {"AVAILABLE", "USED"} for state in item["personal_states"]) for item in owned_capabilities),
                "used": sum("USED" in item["personal_states"] for item in owned_capabilities),
                "used_capabilities": sum("USED" in item["personal_states"] for item in owned_capabilities),
                "available_capabilities": sum("AVAILABLE" in item["personal_states"] for item in owned_capabilities),
                "adopted_methods": len(adopted_methods),
                "active_patterns": len(adopted_methods),
                "processing": categories.count("VALIDATING"),
                "validating": categories.count("VALIDATING"),
                "waiting_validation": categories.count("WAITING_VALIDATION"),
                "watchlist": categories.count("WATCHLIST"),
                "human_gated": categories.count("HUMAN_DECISION"),
                "not_adopted": sum(category in {"NOT_ADOPTED", "VALIDATION_FAILED", "ARCHIVED"} for category in categories),
                "stale_reviews": len(stale_reviews),
            },
            "latest_scan": health.get("latest_scan_run"),
            "latest_chancellor": health.get("latest_stage_b_run"),
            "recent_discoveries": recent,
            "validating": validating,
            **entities,
            "my_capabilities_cards": owned_capabilities,
            "method_cards": adopted_methods,
            "pending_cards": [card for card in cards if card.get("human_category") in {"WAITING_VALIDATION", "VALIDATING", "HUMAN_DECISION"}],
            "watch_archive_cards": [card for card in cards if card.get("human_category") in {"WATCHLIST", "NOT_ADOPTED", "VALIDATION_FAILED", "ARCHIVED"}],
            "directly_usable_cards": [card for card in cards if card.get("human_category") in {"USED", "USABLE"}],
            "knowledge_cards": [card for card in cards if card.get("human_category") == "ADOPTED_METHOD"],
            "not_adopted_cards": [card for card in cards if card.get("human_category") in {"NOT_ADOPTED", "VALIDATION_FAILED", "ARCHIVED"}],
            "human_gated_cards": [card for card in cards if card.get("human_category") == "HUMAN_DECISION"],
        }
