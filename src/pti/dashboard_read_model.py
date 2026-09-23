import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .capability_library import _card, _read_rows
from .health import health_report
from .human_toolbox import STATUS_LABELS, _with_usage


LIFECYCLE_LABELS = {
    "DISCOVERED": "最近发现",
    "REVIEW": "待判断",
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

    def capabilities(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        if not self.db_path.is_file():
            return []
        try:
            rows = _read_rows(self.db_path)
        except (OSError, sqlite3.Error, json.JSONDecodeError):
            return []
        cards = []
        for row in rows:
            card = _with_usage(self.root, _card(row))
            state = card.get("activation_state", "")
            action = card.get("semantic_action", "")
            if state in {"QUARANTINE_READY", "BLOCKED_HUMAN"} and not card.get("human_status"):
                card["human_status"] = LIFECYCLE_LABELS.get(state, state)
            card["lifecycle_status"] = LIFECYCLE_LABELS.get(state, STATUS_LABELS.get(state, state))
            if action == "REFERENCE_ONLY":
                card["lifecycle_status"] = LIFECYCLE_LABELS["REFERENCE_ONLY"]
            card["updated_at"] = card.get("evidence_timestamp") or ""
            cards.append(card)
        filters = filters or {}
        query = filters.get("q", "").strip().lower()
        state = filters.get("state", "").strip()
        category = filters.get("category", "").strip()
        if query:
            cards = [card for card in cards if query in json.dumps(card, ensure_ascii=False).lower()]
        if state:
            cards = [card for card in cards if card.get("lifecycle_status") == state or card.get("activation_state") == state]
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
            WHERE q.status IN ('PENDING','PROCESSING')
            ORDER BY q.created_at DESC, q.id DESC
        """).fetchall()
        return [{
            "repository": row["canonical_owner_repo"] or f"repository:{row['repository_id']}",
            "url": row["url"],
            "step": "等待验证" if row["status"] == "PENDING" else "正在处理",
            "started_at": row["last_attempt_at"] or row["created_at"],
            "risk": row["activation_tier"],
            "result": row["desired_next_state"],
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
        states = [card.get("activation_state", "") for card in cards]
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
            "status": "异常" if health.get("status") == "NOT_EVALUATED" else "提醒" if health.get("status") == "DEGRADED_HISTORY_ONLY" else "正常",
            "health": health,
            "counts": {
                "total": len(cards),
                "directly_usable": sum(state in {"TRIAL_ENABLED", "USED"} for state in states),
                "used": states.count("USED"),
                "active_patterns": states.count("ACTIVE_PATTERN"),
                "validating": len(validating) + sum(state == "QUARANTINE_READY" for state in states),
                "human_gated": states.count("BLOCKED_HUMAN"),
                "not_adopted": sum(state in {"TESTED_NOT_ADOPTED", "FAILED_WITH_EXPLAINED_REASON", "FAILED_TERMINAL"} for state in states),
            },
            "latest_scan": health.get("latest_scan_run"),
            "latest_chancellor": health.get("latest_stage_b_run"),
            "recent_discoveries": recent,
            "validating": validating,
            "directly_usable_cards": [card for card in cards if card.get("activation_state") in {"TRIAL_ENABLED", "USED"}],
            "knowledge_cards": [card for card in cards if card.get("activation_state") == "ACTIVE_PATTERN" or card.get("semantic_action") == "REFERENCE_ONLY"],
            "not_adopted_cards": [card for card in cards if card.get("activation_state") in {"TESTED_NOT_ADOPTED", "FAILED_WITH_EXPLAINED_REASON", "FAILED_TERMINAL"}],
            "human_gated_cards": [card for card in cards if card.get("activation_state") == "BLOCKED_HUMAN"],
        }
