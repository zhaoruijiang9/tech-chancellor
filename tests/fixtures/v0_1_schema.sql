-- Schema extracted from the published v0.1.0 release, with no user rows.
CREATE TABLE activation_queue (
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
            );

CREATE TABLE activation_records (
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
            , real_use_project TEXT, real_use_task_type TEXT, real_use_at TEXT, real_use_outcome TEXT, real_use_evidence TEXT);

CREATE TABLE candidate_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, scan_run_id TEXT NOT NULL,
                github_repository_id INTEGER NOT NULL, discovery_domain TEXT NOT NULL,
                source_query TEXT NOT NULL, deterministic_score REAL NOT NULL,
                deterministic_decision TEXT NOT NULL, priority TEXT NOT NULL,
                enrichment_level TEXT, enrichment_failures_json TEXT NOT NULL DEFAULT '[]',
                observed_at TEXT NOT NULL, UNIQUE(scan_run_id, github_repository_id, source_query)
            );

CREATE TABLE chancellor_decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, github_repository_id INTEGER NOT NULL,
                scan_run_id TEXT, decision_json TEXT NOT NULL, packet_name TEXT NOT NULL,
                imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE chancellor_decisions (
                github_repository_id INTEGER PRIMARY KEY, decision_json TEXT NOT NULL,
                packet_name TEXT NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE notification_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, scan_run_id TEXT, github_repository_id INTEGER,
                status TEXT NOT NULL CHECK(status IN ('NOTIFICATION_NOT_REQUIRED','NOTIFICATION_SENT','NOTIFICATION_FAILED')),
                reason TEXT NOT NULL, report_path TEXT, route TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

CREATE TABLE repositories (
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
                );

CREATE TABLE scan_runs (
                run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, completed_at TEXT,
                status TEXT, request_count INTEGER NOT NULL DEFAULT 0,
                candidate_count INTEGER NOT NULL DEFAULT 0, failure_count INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE stage_b_runs (
                run_id TEXT PRIMARY KEY, trigger_type TEXT NOT NULL, started_at TEXT NOT NULL,
                completed_at TEXT, status TEXT, pending_count INTEGER NOT NULL DEFAULT 0,
                claimed_count INTEGER NOT NULL DEFAULT 0, codex_invocation_count INTEGER NOT NULL DEFAULT 0,
                success_count INTEGER NOT NULL DEFAULT 0, retryable_failure_count INTEGER NOT NULL DEFAULT 0,
                no_pending INTEGER NOT NULL DEFAULT 0, already_active INTEGER NOT NULL DEFAULT 0,
                exit_status INTEGER
            );

CREATE TABLE user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_repository_id INTEGER NOT NULL,
                label TEXT NOT NULL CHECK(label IN ('USEFUL','NOT_USEFUL','ALREADY_HAVE','WRONG_ROUTE','TOO_COMPLEX','TOO_RISKY','WATCH','APPROVE_FOR_REVIEW')),
                note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            , scan_run_id TEXT, route TEXT, report_path TEXT, chancellor_history_id INTEGER, observation_fingerprint TEXT, material_evidence_fingerprint TEXT, material_evidence_projection TEXT NOT NULL DEFAULT '{}');
