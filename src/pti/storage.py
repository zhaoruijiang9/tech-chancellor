import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .models import RepositoryRecord
from .chancellor_contract import validate_decision


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS repositories (
                    github_repository_id INTEGER PRIMARY KEY,
                    canonical_owner_repo TEXT NOT NULL,
                    url TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    stars INTEGER NOT NULL DEFAULT 0,
                    forks INTEGER NOT NULL DEFAULT 0,
                    pushed_at TEXT,
                    release_state TEXT,
                    license_spdx TEXT,
                    is_fork INTEGER NOT NULL DEFAULT 0,
                    parent_repository_id INTEGER,
                    previous_score REAL,
                    previous_decision TEXT,
                    previous_routes TEXT NOT NULL DEFAULT '[]',
                    rejection_reason TEXT,
                    review_after TEXT,
                    content_fingerprint TEXT,
                    description TEXT NOT NULL DEFAULT '',
                    topics TEXT NOT NULL DEFAULT '[]',
                    default_branch TEXT,
                    observation_fingerprint TEXT,
                    material_evidence_fingerprint TEXT,
                    material_evidence_projection TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            connection.execute("""CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_repository_id INTEGER NOT NULL,
                label TEXT NOT NULL CHECK(label IN ('USEFUL','NOT_USEFUL','ALREADY_HAVE','WRONG_ROUTE','TOO_COMPLEX','TOO_RISKY','WATCH','APPROVE_FOR_REVIEW')),
                note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS chancellor_decisions (
                github_repository_id INTEGER PRIMARY KEY, decision_json TEXT NOT NULL,
                packet_name TEXT NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS scan_runs (
                run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT,
                status TEXT, request_count INTEGER NOT NULL DEFAULT 0,
                candidate_count INTEGER NOT NULL DEFAULT 0, failure_count INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS candidate_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, scan_run_id TEXT NOT NULL,
                github_repository_id INTEGER NOT NULL, discovery_domain TEXT NOT NULL,
                source_query TEXT NOT NULL, deterministic_score REAL NOT NULL,
                deterministic_decision TEXT NOT NULL, priority TEXT NOT NULL,
                enrichment_level TEXT, enrichment_failures_json TEXT NOT NULL DEFAULT '[]',
                observed_at TEXT NOT NULL, UNIQUE(scan_run_id, github_repository_id, source_query)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS chancellor_decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, github_repository_id INTEGER NOT NULL,
                scan_run_id TEXT, decision_json TEXT NOT NULL, packet_name TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS notification_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, scan_run_id TEXT, github_repository_id INTEGER,
                status TEXT NOT NULL CHECK(status IN ('NOTIFICATION_NOT_REQUIRED','NOTIFICATION_SENT','NOTIFICATION_FAILED')),
                reason TEXT NOT NULL, report_path TEXT, route TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS stage_b_runs (
                run_id TEXT PRIMARY KEY, trigger_type TEXT NOT NULL, started_at TEXT NOT NULL,
                completed_at TEXT, status TEXT, pending_count INTEGER NOT NULL DEFAULT 0,
                claimed_count INTEGER NOT NULL DEFAULT 0, codex_invocation_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0, retryable_failure_count INTEGER NOT NULL DEFAULT 0,
                no_pending INTEGER NOT NULL DEFAULT 0, already_active INTEGER NOT NULL DEFAULT 0,
                exit_status INTEGER
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS activation_records (
                github_repository_id INTEGER PRIMARY KEY,
                activation_tier TEXT NOT NULL,
                activation_state TEXT NOT NULL,
                evidence_maturity TEXT NOT NULL DEFAULT 'REVIEWED',
                pinned_version TEXT,
                static_analysis_status TEXT NOT NULL DEFAULT 'NOT_RUN',
                isolated_test_status TEXT NOT NULL DEFAULT 'NOT_RUN',
                trial_status TEXT NOT NULL DEFAULT 'NOT_ENABLED',
                rollback_status TEXT NOT NULL DEFAULT 'UNKNOWN',
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            activation_columns = {row[1] for row in connection.execute("PRAGMA table_info(activation_records)")}
            for name, definition in {
                "real_use_project": "TEXT",
                "real_use_task_type": "TEXT",
                "real_use_at": "TEXT",
                "real_use_outcome": "TEXT",
                "real_use_evidence": "TEXT",
            }.items():
                if name not in activation_columns:
                    connection.execute(f"ALTER TABLE activation_records ADD COLUMN {name} {definition}")
            connection.execute("""CREATE TABLE IF NOT EXISTS activation_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                activation_tier TEXT NOT NULL,
                desired_next_state TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_attempt_at TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                failure_class TEXT
            )""")
            connection.execute("""UPDATE scan_runs SET status='INTERRUPTED_LEGACY_RUNTIME_REGRESSION',
                completed_at=COALESCE(completed_at, started_at)
                WHERE completed_at IS NULL AND (status IS NULL OR status='')""")
            connection.execute("""UPDATE stage_b_runs SET status='INTERRUPTED_RUNTIME_RECOVERED',
                completed_at=COALESCE(completed_at, started_at), exit_status=1
                WHERE completed_at IS NULL AND (status IS NULL OR status='')""")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(user_feedback)")}
            for name, definition in {
                "scan_run_id": "TEXT", "route": "TEXT", "report_path": "TEXT",
                "chancellor_history_id": "INTEGER",
                "observation_fingerprint": "TEXT",
                "material_evidence_fingerprint": "TEXT",
                "material_evidence_projection": "TEXT NOT NULL DEFAULT '{}'",
            }.items():
                if name not in columns:
                    connection.execute(f"ALTER TABLE user_feedback ADD COLUMN {name} {definition}")
            repository_columns = {row[1] for row in connection.execute("PRAGMA table_info(repositories)")}
            for name, definition in {
                "observation_fingerprint": "TEXT",
                "material_evidence_fingerprint": "TEXT",
                "material_evidence_projection": "TEXT NOT NULL DEFAULT '{}'",
            }.items():
                if name not in repository_columns:
                    connection.execute(f"ALTER TABLE repositories ADD COLUMN {name} {definition}")
            latest_rows = connection.execute("""select h.github_repository_id,h.decision_json,h.packet_name,h.imported_at
                from chancellor_decision_history h join (select github_repository_id,max(id) id
                from chancellor_decision_history group by github_repository_id) latest on latest.id=h.id""").fetchall()
            for row in latest_rows:
                try:
                    decision = json.loads(row[1])
                except (TypeError, json.JSONDecodeError):
                    continue
                if validate_decision(decision).valid:
                    connection.execute("""insert into chancellor_decisions
                        (github_repository_id,decision_json,packet_name,imported_at) values (?,?,?,?)
                        on conflict(github_repository_id) do update set decision_json=excluded.decision_json,
                        packet_name=excluded.packet_name,imported_at=excluded.imported_at""",
                        (row[0], json.dumps(decision, ensure_ascii=False, sort_keys=True), row[2], row[3]))
            current_rows = connection.execute("select github_repository_id,decision_json from chancellor_decisions").fetchall()
            for row in current_rows:
                try:
                    valid = validate_decision(json.loads(row[1])).valid
                except (TypeError, json.JSONDecodeError):
                    valid = False
                if not valid:
                    connection.execute("delete from chancellor_decisions where github_repository_id = ?", (row[0],))

    def upsert_repository(self, record: RepositoryRecord) -> None:
        values = record.to_dict()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO repositories (
                    github_repository_id, canonical_owner_repo, url, first_seen, last_seen,
                    stars, forks, pushed_at, release_state, license_spdx, is_fork,
                    parent_repository_id, previous_score, previous_decision, previous_routes,
                    rejection_reason, review_after, content_fingerprint, description, topics,
                    default_branch, observation_fingerprint, material_evidence_fingerprint,
                    material_evidence_projection
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(github_repository_id) DO UPDATE SET
                    canonical_owner_repo=excluded.canonical_owner_repo,
                    url=excluded.url,
                    last_seen=excluded.last_seen,
                    stars=excluded.stars,
                    forks=excluded.forks,
                    pushed_at=excluded.pushed_at,
                    release_state=excluded.release_state,
                    license_spdx=excluded.license_spdx,
                    is_fork=excluded.is_fork,
                    parent_repository_id=excluded.parent_repository_id,
                    previous_score=excluded.previous_score,
                    previous_decision=excluded.previous_decision,
                    previous_routes=excluded.previous_routes,
                    rejection_reason=excluded.rejection_reason,
                    review_after=excluded.review_after,
                    content_fingerprint=excluded.content_fingerprint,
                    description=excluded.description,
                    topics=excluded.topics,
                    default_branch=excluded.default_branch,
                    observation_fingerprint=excluded.observation_fingerprint,
                    material_evidence_fingerprint=excluded.material_evidence_fingerprint,
                    material_evidence_projection=excluded.material_evidence_projection
                """,
                (
                    values["github_repository_id"], values["canonical_owner_repo"], values["url"],
                    values["first_seen"], values["last_seen"], values["stars"], values["forks"],
                    values["pushed_at"], values["release_state"], values["license_spdx"],
                    int(values["is_fork"]), values["parent_repository_id"], values["previous_score"],
                    values["previous_decision"], json.dumps(values["previous_routes"]),
                    values["rejection_reason"], values["review_after"], values["content_fingerprint"],
                    values["description"], json.dumps(values["topics"]), values["default_branch"],
                    values["observation_fingerprint"], values["material_evidence_fingerprint"],
                    json.dumps(values["material_evidence_projection"], ensure_ascii=False),
                ),
            )

    @staticmethod
    def _record(row: sqlite3.Row | None) -> RepositoryRecord | None:
        if row is None:
            return None
        values = dict(row)
        values["is_fork"] = bool(values["is_fork"])
        values["previous_routes"] = json.loads(values.pop("previous_routes") or "[]")
        values["topics"] = json.loads(values.pop("topics") or "[]")
        values["material_evidence_projection"] = json.loads(values.get("material_evidence_projection") or "{}")
        return RepositoryRecord(**values)

    def get_repository(self, repository_id: int) -> RepositoryRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM repositories WHERE github_repository_id = ?", (repository_id,)
            ).fetchone()
        return self._record(row)

    def has_current_semantic_decision(self, repository_id: int) -> bool:
        with self._connect() as connection:
            return connection.execute("SELECT 1 FROM chancellor_decisions WHERE github_repository_id = ?", (repository_id,)).fetchone() is not None

    def list_repositories(self) -> list[RepositoryRecord]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM repositories ORDER BY last_seen DESC").fetchall()
        return [self._record(row) for row in rows]

    def record_evaluation(
        self,
        repository_id: int,
        score: float,
        decision: str,
        routes: list[str],
        rejection_reason: str | None,
        review_after: str | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """UPDATE repositories
                   SET previous_score = ?, previous_decision = ?, previous_routes = ?,
                       rejection_reason = ?, review_after = ?
                   WHERE github_repository_id = ?""",
                (score, decision, json.dumps(routes), rejection_reason, review_after, repository_id),
            )

    def record_feedback(self, repository_id: int, label: str, note: str = "", scan_run_id: str | None = None,
                        route: str | None = None, report_path: str | None = None,
                        chancellor_history_id: int | None = None) -> None:
        with self._connect() as connection:
            connection.execute("""INSERT INTO user_feedback
                (github_repository_id, label, note, scan_run_id, route, report_path, chancellor_history_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (repository_id, label, note[:2000], scan_run_id, route, report_path, chancellor_history_id))

    def get_feedback(self, repository_id: int) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT github_repository_id, label, note, created_at, scan_run_id, route, report_path, chancellor_history_id FROM user_feedback WHERE github_repository_id = ? ORDER BY id", (repository_id,)).fetchall()
        return [dict(row) for row in rows]

    def upsert_activation(self, record: dict) -> None:
        with self._connect() as connection:
            connection.execute("""INSERT INTO activation_records
                (github_repository_id, activation_tier, activation_state, evidence_maturity,
                 pinned_version, static_analysis_status, isolated_test_status, trial_status,
                 rollback_status, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(github_repository_id) DO UPDATE SET
                 activation_tier=excluded.activation_tier,
                 activation_state=excluded.activation_state,
                 evidence_maturity=excluded.evidence_maturity,
                 pinned_version=excluded.pinned_version,
                 static_analysis_status=excluded.static_analysis_status,
                 isolated_test_status=excluded.isolated_test_status,
                 trial_status=excluded.trial_status,
                 rollback_status=excluded.rollback_status,
                 notes=excluded.notes,
                 updated_at=CURRENT_TIMESTAMP""",
                (record["github_repository_id"], record["activation_tier"], record["activation_state"],
                 record.get("evidence_maturity", "REVIEWED"), record.get("pinned_version"),
                 record.get("static_analysis_status", "NOT_RUN"), record.get("isolated_test_status", "NOT_RUN"),
                 record.get("trial_status", "NOT_ENABLED"), record.get("rollback_status", "UNKNOWN"),
                 record.get("notes", "")))

    def get_activation(self, repository_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM activation_records WHERE github_repository_id = ?", (repository_id,)).fetchone()
        return dict(row) if row else None

    def list_activations(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM activation_records ORDER BY github_repository_id").fetchall()
        return [dict(row) for row in rows]

    def record_real_use(self, repository_id: int, project_label: str, task_type: str,
                        outcome: str, evidence: str, *, real_task_evidence: bool) -> None:
        if not real_task_evidence:
            raise ValueError("real use requires explicit current-task evidence")
        with self._connect() as connection:
            row = connection.execute("SELECT activation_state FROM activation_records WHERE github_repository_id=?", (repository_id,)).fetchone()
            if not row or row[0] not in {"TRIAL_ENABLED", "USED"}:
                raise ValueError("capability must be trial-enabled before real use")
            connection.execute("""UPDATE activation_records SET activation_state='USED', evidence_maturity='USED',
                real_use_project=?, real_use_task_type=?, real_use_at=CURRENT_TIMESTAMP,
                real_use_outcome=?, real_use_evidence=?, updated_at=CURRENT_TIMESTAMP
                WHERE github_repository_id=?""",
                (project_label[:300], task_type[:120], outcome[:1000], evidence[:2000], repository_id))

    def enqueue_activation(self, repository_id: int, activation_tier: str, desired_next_state: str, reason: str) -> int:
        with self._connect() as connection:
            existing = connection.execute("""SELECT id FROM activation_queue
                WHERE repository_id=? AND desired_next_state=? AND status IN ('PENDING','PROCESSING')
                ORDER BY id DESC LIMIT 1""", (repository_id, desired_next_state)).fetchone()
            if existing:
                return int(existing[0])
            cursor = connection.execute("""INSERT INTO activation_queue
                (repository_id, activation_tier, desired_next_state, reason)
                VALUES (?, ?, ?, ?)""", (repository_id, activation_tier, desired_next_state, reason[:2000]))
            return int(cursor.lastrowid)

    def list_activation_queue(self, status: str | None = None) -> list[dict]:
        with self._connect() as connection:
            if status:
                rows = connection.execute("SELECT * FROM activation_queue WHERE status=? ORDER BY id", (status,)).fetchall()
            else:
                rows = connection.execute("SELECT * FROM activation_queue ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def claim_activation(self, queue_id: int) -> dict | None:
        with self._connect() as connection:
            connection.execute("""UPDATE activation_queue SET status='PROCESSING',
                attempt_count=attempt_count+1, last_attempt_at=CURRENT_TIMESTAMP
                WHERE id=? AND status='PENDING'""", (queue_id,))
            row = connection.execute("SELECT * FROM activation_queue WHERE id=?", (queue_id,)).fetchone()
        return dict(row) if row else None

    def complete_activation(self, queue_id: int, status: str, failure_class: str | None = None) -> None:
        if status not in {"SUCCEEDED", "RETRYABLE", "BLOCKED_HUMAN", "FAILED_TERMINAL"}:
            raise ValueError(f"invalid activation queue status: {status}")
        with self._connect() as connection:
            connection.execute("UPDATE activation_queue SET status=?, failure_class=? WHERE id=?",
                               (status, failure_class, queue_id))

    def start_scan_run(self, run_id: str, started_at: str) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO scan_runs (run_id, started_at) VALUES (?, ?)", (run_id, started_at))

    def record_candidate_observation(self, run_id: str, record: RepositoryRecord, discovery_domain: str,
                                     source_query: str, score: float, decision: str, priority: str,
                                     enrichment_level: str | None, enrichment_failures: list[dict]) -> None:
        with self._connect() as connection:
            connection.execute("""INSERT OR IGNORE INTO candidate_observations
                (scan_run_id, github_repository_id, discovery_domain, source_query, deterministic_score,
                 deterministic_decision, priority, enrichment_level, enrichment_failures_json, observed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, record.github_repository_id, discovery_domain, source_query, score, decision, priority,
                 enrichment_level, json.dumps(enrichment_failures, ensure_ascii=False), record.last_seen))

    def finish_scan_run(self, run_id: str, status: str, request_count: int, failure_count: int,
                        completed_at: str, candidate_count: int | None = None) -> None:
        with self._connect() as connection:
            if candidate_count is None:
                candidate_count = connection.execute("SELECT count(*) FROM candidate_observations WHERE scan_run_id = ?", (run_id,)).fetchone()[0]
            connection.execute("""UPDATE scan_runs SET completed_at = ?, status = ?, request_count = ?,
                candidate_count = ?, failure_count = ? WHERE run_id = ?""",
                (completed_at, status, request_count, candidate_count, failure_count, run_id))

    def record_chancellor_decision(self, repository_id: int, decision: dict, packet_name: str,
                                   scan_run_id: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute("""INSERT INTO chancellor_decisions (github_repository_id, decision_json, packet_name)
                VALUES (?, ?, ?)
                ON CONFLICT(github_repository_id) DO UPDATE SET decision_json=excluded.decision_json,
                packet_name=excluded.packet_name, imported_at=CURRENT_TIMESTAMP""",
                (repository_id, json.dumps(decision, ensure_ascii=False, sort_keys=True), packet_name))
            connection.execute("""INSERT INTO chancellor_decision_history
                (github_repository_id, scan_run_id, decision_json, packet_name) VALUES (?, ?, ?, ?)""",
                (repository_id, scan_run_id, json.dumps(decision, ensure_ascii=False, sort_keys=True), packet_name))
            connection.execute("UPDATE repositories SET previous_decision = ?, previous_routes = ? WHERE github_repository_id = ?",
                               (decision["ACTION"], json.dumps([decision["BEST_ROUTE"]]), repository_id))

    def latest_chancellor_history(self, repository_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM chancellor_decision_history WHERE github_repository_id = ? ORDER BY id DESC LIMIT 1", (repository_id,)).fetchone()
        return dict(row) if row else None

    def latest_candidate_observation(self, repository_id: int) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM candidate_observations WHERE github_repository_id = ? ORDER BY id DESC LIMIT 1", (repository_id,)).fetchone()
        return dict(row) if row else None

    def record_notification_event(self, scan_run_id: str | None, repository_id: int | None, status: str,
                                  reason: str, report_path: str | None = None, route: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute("""INSERT INTO notification_events
                (scan_run_id, github_repository_id, status, reason, report_path, route)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (scan_run_id, repository_id, status, reason, report_path, route))

    def start_stage_b_run(self, run_id: str, trigger_type: str, started_at: str, pending_count: int) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO stage_b_runs (run_id, trigger_type, started_at, pending_count) VALUES (?, ?, ?, ?)",
                               (run_id, trigger_type, started_at, pending_count))

    def finish_stage_b_run(self, run_id: str, completed_at: str, status: str, claimed_count: int,
                           codex_invocations: int, success_count: int, retryable_failures: int,
                           no_pending: bool, already_active: bool, exit_status: int) -> None:
        with self._connect() as connection:
            connection.execute("""UPDATE stage_b_runs SET completed_at=?, status=?, claimed_count=?,
                codex_invocation_count=?, success_count=?, retryable_failure_count=?, no_pending=?,
                already_active=?, exit_status=? WHERE run_id=?""",
                (completed_at, status, claimed_count, codex_invocations, success_count, retryable_failures,
                 int(no_pending), int(already_active), exit_status, run_id))
