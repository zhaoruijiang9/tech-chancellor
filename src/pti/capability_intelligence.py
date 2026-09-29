from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DELTA_KINDS = {
    "NEW_CAPABILITY",
    "OVERLAP",
    "REPLACEMENT",
    "COMPLEMENT",
    "NO_MEANINGFUL_DELTA",
}
RELATION_TYPES = {
    "DEPENDS_ON",
    "REPLACES",
    "OVERLAPS",
    "COMPLEMENTS",
    "CONFLICTS_WITH",
}


CAPABILITY_DEFINITIONS = {
    "PROJECT_ARCHITECTURE_VISUALIZATION": ("项目架构可视化", "生成可核验的架构、数据流、时序和前后对比视图"),
    "SPECIFICATION_DRIVEN_DEVELOPMENT": ("规格驱动开发", "在实现前明确规格、边界与验收条件"),
    "TRACEABLE_IMPLEMENTATION_GATES": ("可追踪实施门槛", "把计划、实现和验证连接为可审计交付链"),
    "STRUCTURED_DEVELOPMENT_WORKFLOW": ("结构化开发工作流", "按澄清、规划、实现和验证阶段组织复杂开发"),
    "REPOSITORY_CONTEXT_MAPPING": ("代码库上下文映射", "组织仓库结构、符号和调用关系"),
    "CODEBASE_SEMANTIC_RETRIEVAL": ("代码库语义检索", "跨文件按概念检索相关代码与上下文"),
    "AGENT_WORKFLOW_ORCHESTRATION": ("Agent 工作流编排", "组织多阶段或多角色 Agent 工作流"),
    "CONTEXT_COMPRESSION": ("上下文压缩", "压缩工具输出并保留关键证据"),
    "DESKTOP_CONTEXT_CAPTURE": ("桌面上下文采集", "采集和组织桌面活动上下文"),
    "SKILL_ECOSYSTEM_DISCOVERY": ("Skill 生态发现", "从第三方索引发现候选能力方向"),
    "MULTI_AGENT_FINANCIAL_RESEARCH": ("多 Agent 金融研究", "以多角色 Agent 组织金融研究流程"),
    "QUANT_BACKTEST_EXPERIMENTATION": ("量化回测实验", "在隔离的公开或合成数据上设计回测实验"),
}


SOURCE_CAPABILITY_MAP = {
    "composiohq/awesome-claude-skills": [("SKILL_ECOSYSTEM_DISCOVERY", "COMPLEMENT")],
    "foundationagents/metagpt": [("AGENT_WORKFLOW_ORCHESTRATION", "OVERLAP")],
    "tauricresearch/tradingagents": [
        ("MULTI_AGENT_FINANCIAL_RESEARCH", "NEW_CAPABILITY"),
        ("AGENT_WORKFLOW_ORCHESTRATION", "OVERLAP"),
    ],
    "bmad-code-org/bmad-method": [
        ("STRUCTURED_DEVELOPMENT_WORKFLOW", "COMPLEMENT"),
        ("TRACEABLE_IMPLEMENTATION_GATES", "COMPLEMENT"),
    ],
    "cased/kit": [("REPOSITORY_CONTEXT_MAPPING", "OVERLAP")],
    "chunkhound/chunkhound": [("CODEBASE_SEMANTIC_RETRIEVAL", "COMPLEMENT")],
    "coleam00/archon": [("AGENT_WORKFLOW_ORCHESTRATION", "OVERLAP")],
    "github/spec-kit": [
        ("SPECIFICATION_DRIVEN_DEVELOPMENT", "COMPLEMENT"),
        ("TRACEABLE_IMPLEMENTATION_GATES", "COMPLEMENT"),
    ],
    "gmickel/flow-next": [("AGENT_WORKFLOW_ORCHESTRATION", "OVERLAP")],
    "headroomlabs-ai/headroom": [("CONTEXT_COMPRESSION", "COMPLEMENT")],
    "langchain-ai/langchain": [("AGENT_WORKFLOW_ORCHESTRATION", "OVERLAP")],
    "nieledran/backtesting-engine": [("QUANT_BACKTEST_EXPERIMENTATION", "NEW_CAPABILITY")],
    "tt-a1i/archify": [("PROJECT_ARCHITECTURE_VISUALIZATION", "NEW_CAPABILITY")],
    "volcengine/minecontext": [("DESKTOP_CONTEXT_CAPTURE", "COMPLEMENT")],
}


METHOD_DEFINITIONS = {
    "bmad-code-org/bmad-method": [
        ("BMAD_REQUIREMENTS_CLARIFICATION", "需求澄清", "在规划前澄清目标、约束和未知项"),
        ("BMAD_PHASED_DELIVERY", "阶段化交付", "按规划、实现和验证阶段推进复杂任务"),
        ("BMAD_VERIFICATION_LOOP", "验证闭环", "在完成声明前保留可重复验证证据"),
    ],
    "github/spec-kit": [
        ("SPEC_KIT_SPECIFICATION_FIRST", "规格先行", "实现前形成可验收规格"),
        ("SPEC_KIT_ACCEPTANCE_GATES", "验收门槛", "用明确条件约束实现与完成声明"),
        ("SPEC_KIT_TRACEABLE_PLANNING", "可追踪规划", "保持需求、计划、实现和验证之间的追踪关系"),
    ],
}


CAPABILITY_RELATIONS = [
    (
        "SPECIFICATION_DRIVEN_DEVELOPMENT",
        "COMPLEMENTS",
        "TRACEABLE_IMPLEMENTATION_GATES",
        "Spec Kit separates specification from implementation and verification gates.",
    ),
    (
        "STRUCTURED_DEVELOPMENT_WORKFLOW",
        "COMPLEMENTS",
        "TRACEABLE_IMPLEMENTATION_GATES",
        "BMAD combines phased workflow guidance with explicit completion checks.",
    ),
    (
        "MULTI_AGENT_FINANCIAL_RESEARCH",
        "DEPENDS_ON",
        "AGENT_WORKFLOW_ORCHESTRATION",
        "TradingAgents organizes financial research through multiple coordinated agent roles.",
    ),
]


def initialize_capability_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS capability_schema_meta (
            schema_version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS capability_migrations (
            migration_name TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS capability_sources (
            source_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            url TEXT NOT NULL,
            github_repository_id INTEGER UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS capability_implementations (
            implementation_id TEXT PRIMARY KEY,
            source_id TEXT REFERENCES capability_sources(source_id),
            name TEXT NOT NULL,
            implementation_type TEXT NOT NULL,
            lifecycle_state TEXT NOT NULL DEFAULT 'OBSERVED',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS capabilities (
            capability_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS implementation_capabilities (
            implementation_id TEXT NOT NULL REFERENCES capability_implementations(implementation_id),
            capability_id TEXT NOT NULL REFERENCES capabilities(capability_id),
            delta_kind TEXT NOT NULL CHECK(delta_kind IN ('NEW_CAPABILITY','OVERLAP','REPLACEMENT','COMPLEMENT','NO_MEANINGFUL_DELTA')),
            evidence_ref TEXT NOT NULL,
            PRIMARY KEY (implementation_id, capability_id)
        );
        CREATE TABLE IF NOT EXISTS methods (
            method_id TEXT PRIMARY KEY,
            source_id TEXT REFERENCES capability_sources(source_id),
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS method_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method_id TEXT NOT NULL REFERENCES methods(method_id),
            evidence_type TEXT NOT NULL,
            evidence_ref TEXT NOT NULL,
            mechanism TEXT NOT NULL DEFAULT '',
            qualifies INTEGER NOT NULL DEFAULT 0,
            observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(method_id, evidence_type, evidence_ref)
        );
        CREATE TABLE IF NOT EXISTS capability_relations (
            from_capability_id TEXT NOT NULL REFERENCES capabilities(capability_id),
            relation_type TEXT NOT NULL CHECK(relation_type IN ('DEPENDS_ON','REPLACES','OVERLAPS','COMPLEMENTS','CONFLICTS_WITH')),
            to_capability_id TEXT NOT NULL REFERENCES capabilities(capability_id),
            evidence_ref TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(from_capability_id, relation_type, to_capability_id)
        );
        CREATE TABLE IF NOT EXISTS personal_states (
            subject_type TEXT NOT NULL CHECK(subject_type IN ('CAPABILITY','IMPLEMENTATION','METHOD')),
            subject_id TEXT NOT NULL,
            state TEXT NOT NULL,
            evidence_ref TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(subject_type, subject_id, state)
        );
        CREATE TABLE IF NOT EXISTS source_freshness (
            source_id TEXT PRIMARY KEY REFERENCES capability_sources(source_id),
            current_head_sha TEXT,
            current_release_tag TEXT,
            current_release_published_at TEXT,
            current_readme_sha TEXT,
            current_repository_updated_at TEXT,
            current_repository_pushed_at TEXT,
            reviewed_head_sha TEXT,
            reviewed_release_tag TEXT,
            reviewed_readme_sha TEXT,
            last_upstream_check TEXT,
            last_upstream_change TEXT,
            last_review TEXT,
            upstream_freshness TEXT NOT NULL DEFAULT 'UNKNOWN',
            review_freshness TEXT NOT NULL DEFAULT 'UNKNOWN',
            last_check_status TEXT NOT NULL DEFAULT 'NEVER_CHECKED',
            last_error_class TEXT,
            last_error_code TEXT
        );
        CREATE TABLE IF NOT EXISTS upstream_check_runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            checked_count INTEGER NOT NULL DEFAULT 0,
            baseline_count INTEGER NOT NULL DEFAULT 0,
            no_change_count INTEGER NOT NULL DEFAULT 0,
            changed_count INTEGER NOT NULL DEFAULT 0,
            failure_count INTEGER NOT NULL DEFAULT 0,
            request_count INTEGER NOT NULL DEFAULT 0,
            failure_class TEXT
        );
        CREATE TABLE IF NOT EXISTS delta_review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL REFERENCES capability_sources(source_id),
            old_head_sha TEXT,
            new_head_sha TEXT,
            old_release_tag TEXT,
            new_release_tag TEXT,
            trigger_reason TEXT NOT NULL,
            suggested_outcome TEXT,
            change_summary TEXT,
            review_outcome TEXT,
            review_evidence TEXT,
            review_attempts INTEGER NOT NULL DEFAULT 0,
            review_error TEXT,
            reviewed_at TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_delta_review_per_source
        ON delta_review_queue(source_id)
        WHERE status IN ('PENDING','PROCESSING');
        """
    )
    connection.execute(
        "INSERT OR IGNORE INTO capability_schema_meta(schema_version) VALUES (?)",
        (SCHEMA_VERSION,),
    )
    columns = {row[1] for row in connection.execute("PRAGMA table_info(delta_review_queue)")}
    for column, definition in {
        "review_evidence": "TEXT", "suggested_outcome": "TEXT", "change_summary": "TEXT",
        "review_attempts": "INTEGER NOT NULL DEFAULT 0", "review_error": "TEXT", "reviewed_at": "TEXT",
    }.items():
        if column not in columns:
            connection.execute(f"ALTER TABLE delta_review_queue ADD COLUMN {column} {definition}")


@dataclass
class CapabilityStore:
    path: Path

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            initialize_capability_schema(connection)
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def upsert_source(
        self,
        source_id: str,
        source_type: str,
        canonical_name: str,
        url: str,
        github_repository_id: int | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO capability_sources
                (source_id,source_type,canonical_name,url,github_repository_id)
                VALUES (?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                source_type=excluded.source_type,canonical_name=excluded.canonical_name,
                url=excluded.url,github_repository_id=excluded.github_repository_id,
                updated_at=CURRENT_TIMESTAMP""",
                (source_id, source_type, canonical_name, url, github_repository_id),
            )

    def upsert_implementation(
        self,
        implementation_id: str,
        source_id: str | None,
        name: str,
        implementation_type: str,
        lifecycle_state: str = "OBSERVED",
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO capability_implementations
                (implementation_id,source_id,name,implementation_type,lifecycle_state)
                VALUES (?,?,?,?,?)
                ON CONFLICT(implementation_id) DO UPDATE SET
                source_id=excluded.source_id,name=excluded.name,
                implementation_type=excluded.implementation_type,
                lifecycle_state=excluded.lifecycle_state,updated_at=CURRENT_TIMESTAMP""",
                (implementation_id, source_id, name, implementation_type, lifecycle_state),
            )

    def upsert_capability(self, capability_id: str, name: str, description: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO capabilities(capability_id,name,description) VALUES (?,?,?)
                ON CONFLICT(capability_id) DO UPDATE SET name=excluded.name,
                description=excluded.description,updated_at=CURRENT_TIMESTAMP""",
                (capability_id, name, description),
            )

    def link_implementation_capability(
        self,
        implementation_id: str,
        capability_id: str,
        delta_kind: str,
        evidence_ref: str,
    ) -> None:
        if delta_kind not in DELTA_KINDS:
            raise ValueError(f"unsupported capability delta: {delta_kind}")
        if not evidence_ref.strip():
            raise ValueError("capability mapping requires evidence")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO implementation_capabilities
                (implementation_id,capability_id,delta_kind,evidence_ref) VALUES (?,?,?,?)
                ON CONFLICT(implementation_id,capability_id) DO UPDATE SET
                delta_kind=excluded.delta_kind,evidence_ref=excluded.evidence_ref""",
                (implementation_id, capability_id, delta_kind, evidence_ref),
            )

    def upsert_method(
        self,
        method_id: str,
        source_id: str | None,
        name: str,
        description: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO methods(method_id,source_id,name,description) VALUES (?,?,?,?)
                ON CONFLICT(method_id) DO UPDATE SET source_id=excluded.source_id,
                name=excluded.name,description=excluded.description,updated_at=CURRENT_TIMESTAMP""",
                (method_id, source_id, name, description),
            )

    def record_method_evidence(
        self,
        method_id: str,
        evidence_type: str,
        evidence_ref: str,
        mechanism: str,
        qualifies: bool,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO method_evidence
                (method_id,evidence_type,evidence_ref,mechanism,qualifies) VALUES (?,?,?,?,?)
                ON CONFLICT(method_id,evidence_type,evidence_ref) DO UPDATE SET
                mechanism=excluded.mechanism,qualifies=excluded.qualifies""",
                (method_id, evidence_type, evidence_ref, mechanism, int(qualifies)),
            )

    def set_personal_state(
        self, subject_type: str, subject_id: str, state: str, evidence_ref: str
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO personal_states(subject_type,subject_id,state,evidence_ref)
                VALUES (?,?,?,?) ON CONFLICT(subject_type,subject_id,state) DO UPDATE SET
                evidence_ref=excluded.evidence_ref,updated_at=CURRENT_TIMESTAMP""",
                (subject_type, subject_id, state, evidence_ref),
            )

    def upsert_capability_relation(
        self,
        from_capability_id: str,
        relation_type: str,
        to_capability_id: str,
        evidence_ref: str,
    ) -> None:
        if relation_type not in RELATION_TYPES:
            raise ValueError(f"unsupported capability relation: {relation_type}")
        if not evidence_ref.strip():
            raise ValueError("capability relation requires evidence")
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO capability_relations
                (from_capability_id,relation_type,to_capability_id,evidence_ref)
                VALUES (?,?,?,?) ON CONFLICT(from_capability_id,relation_type,to_capability_id)
                DO UPDATE SET evidence_ref=excluded.evidence_ref""",
                (from_capability_id, relation_type, to_capability_id, evidence_ref),
            )

    @staticmethod
    def _method_state(connection: sqlite3.Connection, method_id: str) -> str:
        types = {
            row[0]
            for row in connection.execute(
                "SELECT evidence_type FROM method_evidence WHERE method_id=? AND qualifies=1",
                (method_id,),
            )
        }
        if {"WORKFLOW_MECHANISM", "VERIFIED_USE"}.issubset(types):
            return "ADOPTED"
        return "KNOWLEDGE_REFERENCE"

    def get_method(self, method_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM methods WHERE method_id=?", (method_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["evidence"] = [
                dict(item)
                for item in connection.execute(
                    "SELECT * FROM method_evidence WHERE method_id=? ORDER BY id", (method_id,)
                )
            ]
            result["adoption_state"] = self._method_state(connection, method_id)
            return result

    def get_capability(self, capability_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM capabilities WHERE capability_id=?", (capability_id,)
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["implementations"] = [
                dict(item)
                for item in connection.execute(
                    """SELECT i.*,m.delta_kind,m.evidence_ref
                    FROM implementation_capabilities m
                    JOIN capability_implementations i USING(implementation_id)
                    WHERE m.capability_id=? ORDER BY i.implementation_id""",
                    (capability_id,),
                )
            ]
            result["personal_states"] = [
                dict(item)
                for item in connection.execute(
                    """SELECT state,evidence_ref,updated_at FROM personal_states
                    WHERE subject_type='CAPABILITY' AND subject_id=? ORDER BY state""",
                    (capability_id,),
                )
            ]
            return result

    def get_implementation(self, implementation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM capability_implementations WHERE implementation_id=?",
                (implementation_id,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["capabilities"] = [
                dict(item)
                for item in connection.execute(
                    """SELECT c.*,m.delta_kind,m.evidence_ref
                    FROM implementation_capabilities m JOIN capabilities c USING(capability_id)
                    WHERE m.implementation_id=? ORDER BY c.capability_id""",
                    (implementation_id,),
                )
            ]
            result["personal_states"] = [
                dict(item)
                for item in connection.execute(
                    """SELECT state,evidence_ref,updated_at FROM personal_states
                    WHERE subject_type='IMPLEMENTATION' AND subject_id=? ORDER BY state""",
                    (implementation_id,),
                )
            ]
            return result

    def list_capability_relations(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM capability_relations ORDER BY from_capability_id,relation_type,to_capability_id"
            )]

    def library_snapshot(self) -> dict[str, Any]:
        with self._connect() as connection:
            sources = [dict(row) for row in connection.execute(
                "SELECT * FROM capability_sources ORDER BY canonical_name"
            )]
            implementations = [dict(row) for row in connection.execute(
                "SELECT * FROM capability_implementations ORDER BY implementation_id"
            )]
            capabilities = [dict(row) for row in connection.execute(
                "SELECT * FROM capabilities ORDER BY capability_id"
            )]
            methods = []
            for row in connection.execute("SELECT * FROM methods ORDER BY method_id"):
                item = dict(row)
                item["adoption_state"] = self._method_state(connection, item["method_id"])
                methods.append(item)
            return {
                "sources": sources,
                "implementations": implementations,
                "capabilities": capabilities,
                "methods": methods,
                "adopted_methods": [item for item in methods if item["adoption_state"] == "ADOPTED"],
            }

    def list_monitor_sources(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("""
                SELECT s.*,
                    CASE
                        WHEN EXISTS(SELECT 1 FROM personal_states p JOIN capability_implementations i
                            ON i.implementation_id=p.subject_id
                            WHERE i.source_id=s.source_id AND p.subject_type='IMPLEMENTATION' AND p.state='USED')
                            THEN 'USED'
                        WHEN EXISTS(SELECT 1 FROM personal_states p JOIN capability_implementations i
                            ON i.implementation_id=p.subject_id
                            WHERE i.source_id=s.source_id AND p.subject_type='IMPLEMENTATION'
                            AND p.state='APPROVED_WAITING_VALIDATION') THEN 'APPROVED_WAITING_VALIDATION'
                        WHEN EXISTS(SELECT 1 FROM personal_states p JOIN capability_implementations i
                            ON i.implementation_id=p.subject_id
                            WHERE i.source_id=s.source_id AND p.subject_type='IMPLEMENTATION'
                            AND p.state='HUMAN_DECISION') THEN 'HUMAN_DECISION'
                        WHEN EXISTS(SELECT 1 FROM personal_states p JOIN capability_implementations i
                            ON i.implementation_id=p.subject_id
                            WHERE i.source_id=s.source_id AND p.subject_type='IMPLEMENTATION'
                            AND p.state='VALIDATION_FAILED') THEN 'VALIDATION_FAILED'
                        WHEN EXISTS(SELECT 1 FROM personal_states p JOIN capability_implementations i
                            ON i.implementation_id=p.subject_id
                            WHERE i.source_id=s.source_id AND p.subject_type='IMPLEMENTATION'
                            AND p.state='ARCHIVED') THEN 'ARCHIVED'
                        WHEN EXISTS(SELECT 1 FROM methods m WHERE m.source_id=s.source_id)
                            THEN 'METHOD_SOURCE'
                        WHEN EXISTS(SELECT 1 FROM personal_states p JOIN capability_implementations i
                            ON i.implementation_id=p.subject_id
                            WHERE i.source_id=s.source_id AND p.subject_type='IMPLEMENTATION'
                            AND p.state='REJECTED') THEN 'REJECTED'
                        ELSE 'WATCHLIST'
                    END AS monitoring_state
                FROM capability_sources s
                WHERE s.source_type='GITHUB_REPOSITORY'
                ORDER BY s.canonical_name
            """)]

    def get_source_freshness(self, source_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM source_freshness WHERE source_id=?", (source_id,)
            ).fetchone()
            return dict(row) if row else None

    def record_source_baseline(self, source_id: str, fingerprint: Any, checked_at: str) -> None:
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO source_freshness(
                    source_id,current_head_sha,current_release_tag,current_release_published_at,
                    current_readme_sha,current_repository_updated_at,current_repository_pushed_at,
                    last_upstream_check,upstream_freshness,review_freshness,last_check_status)
                VALUES(?,?,?,?,?,?,?,?,'BASELINE_CAPTURED','UNKNOWN','BASELINE_CAPTURED')
                ON CONFLICT(source_id) DO UPDATE SET
                    current_head_sha=excluded.current_head_sha,
                    current_release_tag=excluded.current_release_tag,
                    current_release_published_at=excluded.current_release_published_at,
                    current_readme_sha=excluded.current_readme_sha,
                    current_repository_updated_at=excluded.current_repository_updated_at,
                    current_repository_pushed_at=excluded.current_repository_pushed_at,
                    last_upstream_check=excluded.last_upstream_check,
                    upstream_freshness='BASELINE_CAPTURED',
                    review_freshness='UNKNOWN',
                    last_check_status='BASELINE_CAPTURED',
                    last_error_class=NULL,last_error_code=NULL
                WHERE source_freshness.current_head_sha IS NULL
            """, (
                source_id, fingerprint.head_sha, fingerprint.release_tag,
                fingerprint.release_published_at, fingerprint.readme_sha,
                fingerprint.repository_updated_at, fingerprint.repository_pushed_at,
                checked_at,
            ))

    def record_source_check(
        self, source_id: str, fingerprint: Any, checked_at: str,
        changed: bool, queue_review: bool, review_outcome: str | None,
        trigger_reason: str, change_summary: str = "",
    ) -> bool:
        with self._connect() as connection:
            old = connection.execute(
                "SELECT * FROM source_freshness WHERE source_id=?", (source_id,)
            ).fetchone()
            if old is None:
                raise ValueError(f"source baseline missing: {source_id}")
            previously_stale = old["review_freshness"] == "STALE"
            review_stale = queue_review or previously_stale
            connection.execute("""
                UPDATE source_freshness SET
                    current_head_sha=?,current_release_tag=?,current_release_published_at=?,
                    current_readme_sha=?,current_repository_updated_at=?,current_repository_pushed_at=?,
                    last_upstream_check=?,last_upstream_change=CASE WHEN ? THEN ? ELSE last_upstream_change END,
                    upstream_freshness=?,review_freshness=?,last_check_status=?,
                    last_error_class=NULL,last_error_code=NULL
                WHERE source_id=?
            """, (
                fingerprint.head_sha, fingerprint.release_tag,
                fingerprint.release_published_at, fingerprint.readme_sha,
                fingerprint.repository_updated_at, fingerprint.repository_pushed_at,
                checked_at, int(changed), checked_at,
                "CHANGED" if changed or previously_stale else "UNCHANGED",
                "STALE" if review_stale else old["review_freshness"],
                "CHANGE_DETECTED" if changed else "NO_CHANGE",
                source_id,
            ))
            if not queue_review:
                return False
            cursor = connection.execute("""
                INSERT OR IGNORE INTO delta_review_queue(
                    source_id,old_head_sha,new_head_sha,old_release_tag,new_release_tag,
                    trigger_reason,suggested_outcome,change_summary)
                VALUES(?,?,?,?,?,?,?,?)
            """, (
                source_id, old["current_head_sha"], fingerprint.head_sha,
                old["current_release_tag"], fingerprint.release_tag,
                trigger_reason, review_outcome, change_summary[:5000],
            ))
            if cursor.rowcount == 0:
                connection.execute("""
                    UPDATE delta_review_queue SET new_head_sha=?,new_release_tag=?,
                    trigger_reason=?,suggested_outcome=?,change_summary=?,
                    review_attempts=0,review_error=NULL,updated_at=CURRENT_TIMESTAMP
                    WHERE source_id=? AND status IN ('PENDING','PROCESSING')
                """, (
                    fingerprint.head_sha, fingerprint.release_tag,
                    trigger_reason, review_outcome, change_summary[:5000], source_id,
                ))
            return cursor.rowcount == 1

    def record_source_failure(
        self, source_id: str, checked_at: str, failure_class: str, failure_code: str
    ) -> None:
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO source_freshness(
                    source_id,last_upstream_check,last_check_status,last_error_class,last_error_code)
                VALUES(?,?,'CHECK_FAILED',?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                    last_upstream_check=excluded.last_upstream_check,
                    last_check_status=excluded.last_check_status,
                    last_error_class=excluded.last_error_class,
                    last_error_code=excluded.last_error_code
            """, (source_id, checked_at, failure_class, failure_code))

    def list_delta_reviews(self, status: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if status is None:
                rows = connection.execute("SELECT * FROM delta_review_queue ORDER BY id").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM delta_review_queue WHERE status=? ORDER BY id", (status,)
                ).fetchall()
            return [dict(row) for row in rows]

    def complete_delta_review(
        self, review_id: int, outcome: str, evidence: str, reviewed_at: str
    ) -> None:
        allowed = {
            "NO_RELEVANT_CHANGE", "REVIEW_STILL_VALID", "REVIEW_UPDATED",
            "REVALIDATION_REQUIRED", "OWNER_DECISION_MAY_CHANGE",
        }
        if outcome not in allowed or not evidence.strip():
            raise ValueError("delta review requires a valid outcome and evidence")
        with self._connect() as connection:
            review = connection.execute(
                "SELECT * FROM delta_review_queue WHERE id=? AND status='PENDING'",
                (review_id,),
            ).fetchone()
            if review is None:
                raise ValueError("pending delta review not found")
            freshness = connection.execute(
                "SELECT * FROM source_freshness WHERE source_id=?",
                (review["source_id"],),
            ).fetchone()
            if freshness is None or freshness["current_head_sha"] != review["new_head_sha"] or freshness["current_release_tag"] != review["new_release_tag"]:
                raise ValueError("upstream changed again; refresh review evidence first")
            connection.execute("""
                UPDATE delta_review_queue SET status='REVIEWED',review_outcome=?,
                    review_evidence=?,review_error=NULL,reviewed_at=?,updated_at=? WHERE id=?
            """, (outcome, evidence.strip(), reviewed_at, reviewed_at, review_id))
            connection.execute("""
                UPDATE source_freshness SET reviewed_head_sha=current_head_sha,
                    reviewed_release_tag=current_release_tag,
                    reviewed_readme_sha=current_readme_sha,
                    last_review=?,review_freshness='CURRENT',
                    upstream_freshness='UNCHANGED'
                WHERE source_id=?
            """, (reviewed_at, review["source_id"]))

    def record_delta_review_failure(self, review_id: int, failure_code: str) -> None:
        with self._connect() as connection:
            connection.execute("""
                UPDATE delta_review_queue SET review_attempts=review_attempts+1,
                    review_error=?,updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='PENDING'
            """, (failure_code[:100], review_id))

    def record_upstream_run(self, record: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO upstream_check_runs(
                    run_id,started_at,completed_at,status,checked_count,baseline_count,
                    no_change_count,changed_count,failure_count,request_count,failure_class)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (
                record["run_id"], record["started_at"], record["completed_at"],
                record["status"], record["checked"], record["baseline_captured"],
                record["no_change"], record["changes_detected"], record["failures"],
                record["request_count"], record.get("failure_class"),
            ))

    def migrate_reviewed_sources(self) -> dict[str, int]:
        with self._connect() as connection:
            migrated = connection.execute(
                "SELECT 1 FROM capability_migrations WHERE migration_name='reviewed_sources_v1'"
            ).fetchone()
            rows = [] if migrated else connection.execute(
                """SELECT r.github_repository_id,r.canonical_owner_repo,r.url,
                COALESCE(a.activation_state,'') activation_state,
                COALESCE(a.evidence_maturity,'') evidence_maturity,
                COALESCE(a.isolated_test_status,'') isolated_test_status,
                COALESCE(a.trial_status,'') trial_status,
                COALESCE(a.real_use_outcome,'') real_use_outcome,
                (SELECT label FROM user_feedback f WHERE f.github_repository_id=r.github_repository_id
                 ORDER BY f.id DESC LIMIT 1) feedback_label,
                (SELECT status FROM activation_queue q WHERE q.repository_id=r.github_repository_id
                 ORDER BY q.id DESC LIMIT 1) queue_status
                FROM repositories r
                JOIN chancellor_decisions d USING(github_repository_id)
                LEFT JOIN activation_records a USING(github_repository_id)
                ORDER BY r.github_repository_id"""
            ).fetchall()
        if migrated:
            snapshot = self.library_snapshot()
            return {
                "reviewed_sources": len(snapshot["sources"]),
                "implementations": len(snapshot["implementations"]),
                "capabilities": len(snapshot["capabilities"]),
                "methods": len(snapshot["methods"]),
                "adopted_methods": len(snapshot["adopted_methods"]),
            }
        if not rows:
            return {"reviewed_sources": 0, "implementations": 0, "capabilities": 0, "methods": 0, "adopted_methods": 0}
        for row in rows:
            repository_id = int(row["github_repository_id"])
            repository = str(row["canonical_owner_repo"])
            repository_key = repository.lower()
            source_id = f"github:{repository_id}"
            implementation_id = f"impl:{repository}"
            self.upsert_source(
                source_id,
                "GITHUB_REPOSITORY",
                repository,
                str(row["url"]),
                repository_id,
            )
            self.upsert_implementation(
                implementation_id,
                source_id,
                repository.rsplit("/", 1)[-1],
                "TOOL_OR_WORKFLOW",
                str(row["activation_state"] or "OBSERVED"),
            )
            for capability_id, delta_kind in SOURCE_CAPABILITY_MAP.get(repository_key, []):
                name, description = CAPABILITY_DEFINITIONS[capability_id]
                self.upsert_capability(capability_id, name, description)
                self.link_implementation_capability(
                    implementation_id,
                    capability_id,
                    delta_kind,
                    f"V0.9 decision and source review: {repository}",
                )
            for method_id, name, description in METHOD_DEFINITIONS.get(repository_key, []):
                self.upsert_method(method_id, source_id, name, description)
                self.record_method_evidence(
                    method_id,
                    "DISTILLED_REFERENCE",
                    f"source:{repository}",
                    "Repository review and local summary; no qualifying workflow mechanism or use record found",
                    qualifies=False,
                )
            with self._connect() as connection:
                connection.execute(
                    """DELETE FROM personal_states WHERE subject_type='IMPLEMENTATION'
                    AND subject_id=? AND evidence_ref LIKE 'migration:%'""",
                    (implementation_id,),
                )
            if (repository_key == "tt-a1i/archify" and row["activation_state"] == "USED"
                    and row["evidence_maturity"] == "USED" and row["isolated_test_status"] == "PASS"
                    and row["real_use_outcome"] == "USED_SUCCESSFULLY"):
                for state in ("VERIFIED", "USED", "AVAILABLE"):
                    self.set_personal_state(
                        "IMPLEMENTATION", implementation_id, state, "migration: activation and real-use evidence"
                    )
                    self.set_personal_state(
                        "CAPABILITY", "PROJECT_ARCHITECTURE_VISUALIZATION", state, "migration: Archify controlled real use"
                    )
            elif repository_key == "nieledran/backtesting-engine" and row["feedback_label"] == "APPROVE_FOR_REVIEW":
                state = "VALIDATING" if row["queue_status"] == "PROCESSING" else "APPROVED_WAITING_VALIDATION"
                self.set_personal_state("IMPLEMENTATION", implementation_id, state, "migration: owner feedback APPROVE_FOR_REVIEW")
            elif repository_key == "tauricresearch/tradingagents":
                self.set_personal_state("IMPLEMENTATION", implementation_id, "HUMAN_DECISION", "migration: sensitive boundary unresolved")
            elif repository_key == "coleam00/archon":
                self.set_personal_state("IMPLEMENTATION", implementation_id, "VALIDATION_FAILED", "migration: controlled activation stopped safely")
            elif repository_key in {"foundationagents/metagpt", "langchain-ai/langchain"}:
                self.set_personal_state("IMPLEMENTATION", implementation_id, "REJECTED", "migration: high overlap and no validated delta")
            else:
                self.set_personal_state("IMPLEMENTATION", implementation_id, "WATCHLIST", "migration: reviewed reference only")
        for from_id, relation, to_id, evidence in CAPABILITY_RELATIONS:
            if self.get_capability(from_id) and self.get_capability(to_id):
                self.upsert_capability_relation(from_id, relation, to_id, evidence)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO capability_migrations(migration_name) VALUES ('reviewed_sources_v1')"
            )
        snapshot = self.library_snapshot()
        return {
            "reviewed_sources": len(snapshot["sources"]),
            "implementations": len(snapshot["implementations"]),
            "capabilities": len(snapshot["capabilities"]),
            "methods": len(snapshot["methods"]),
            "adopted_methods": len(snapshot["adopted_methods"]),
        }
