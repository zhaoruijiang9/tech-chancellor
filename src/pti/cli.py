from dataclasses import dataclass
import os
import uuid
from .models import utc_now
from .runtime_lock import CrashSafeLock, LockState
from pathlib import Path

from .github_api import GitHubClient, RequestBudget
from .discovery import run_discovery
from .reporting import build_report, write_chancellor_pending, write_inbox_artifacts, write_run_report
from .storage import Database


ALLOWED_PHASE_1_ACTIONS = {"discover", "score", "route", "report"}


@dataclass(frozen=True)
class OutputGuard:
    allowed: bool
    reason: str


def validate_output_root(root: str | Path) -> OutputGuard:
    candidate = Path(root).resolve()
    forbidden = Path("D:/money").resolve()
    try:
        candidate.relative_to(forbidden)
    except ValueError:
        return OutputGuard(True, "independent intelligence root")
    return OutputGuard(False, "D:/money is a protected production root")


def run_once(root: str | Path, config_path: str | Path, profile_path: str | Path, dry_run: bool = True) -> dict:
    root = Path(root).resolve()
    guard = validate_output_root(root)
    if not guard.allowed:
        raise ValueError(guard.reason)
    if not dry_run:
        raise ValueError("Phase 1 supports manual dry-run only")
    import json
    lock = CrashSafeLock(root / "state" / "scan.lock", "pti-scan")
    lock_state = lock.acquire()
    if lock_state == LockState.ACTIVE_VALID_LOCK:
        return {"status": "SCAN_ALREADY_ACTIVE", "decisions": 0, "failures": [{"code": "SCAN_ALREADY_ACTIVE"}], "request_count": 0, "artifacts": []}
    if lock_state != LockState.ACQUIRED:
        return {"status": "SCAN_LOCK_NOT_EVALUATED", "decisions": 0, "failures": [{"code": lock_state.value}], "request_count": 0, "artifacts": []}
    try:
        run_id = uuid.uuid4().hex[:12]
        db = Database(root / "state" / "intelligence.db")
        db.initialize()
        db.start_scan_run(run_id, utc_now())
        try:
            config = json.loads(Path(config_path).read_text(encoding="utf-8"))
            profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
            client = GitHubClient(budget=RequestBudget(int(config.get("request_budget", 8))))
            discovery = run_discovery(config, client, db, profile, run_id)
            report = build_report(discovery.decisions, discovery.failures)
            paths = write_inbox_artifacts(root, report.high_priority + report.secondary, run_id)
            paths.extend(write_chancellor_pending(root, report.high_priority + report.secondary, run_id))
            report_path = write_run_report(root, report)
            status = "SCAN_NOT_EVALUATED" if discovery.failures else "SCAN_SUCCESS"
            if not report.high_priority and not report.secondary and not discovery.failures:
                status = "SCAN_SUCCESS_NO_HIGH_SIGNAL"
            db.finish_scan_run(run_id, status, discovery.request_count, len(discovery.failures), utc_now(), len(discovery.decisions))
            db.record_notification_event(run_id, None, "NOTIFICATION_NOT_REQUIRED", "NO_USER_VISIBLE_NOTIFICATION_EMITTED", str(report_path))
            return {"status": status, "run_id": run_id, "decisions": len(discovery.decisions), "failures": discovery.failures, "request_count": discovery.request_count, "artifacts": [str(path) for path in paths] + [str(report_path)]}
        except Exception:
            db.finish_scan_run(run_id, "SCAN_NOT_EVALUATED", 0, 1, utc_now())
            db.record_notification_event(run_id, None, "NOTIFICATION_NOT_REQUIRED", "SCAN_NOT_EVALUATED", str(root / "reports" / "latest.json"))
            raise
    finally:
        lock.release()


def record_feedback(root: str | Path, repo: str, label: str, note: str = "") -> None:
    db = Database(Path(root).resolve() / "state" / "intelligence.db")
    db.initialize()
    record = next((item for item in db.list_repositories() if item.canonical_owner_repo.lower() == repo.lower()), None)
    if record is None:
        raise ValueError(f"repository not found in ledger: {repo}")
        history = db.latest_chancellor_history(record.github_repository_id)
        observation = db.latest_candidate_observation(record.github_repository_id)
        route = record.previous_routes[0] if record.previous_routes else None
    history = db.latest_chancellor_history(record.github_repository_id)
    observation = db.latest_candidate_observation(record.github_repository_id)
    route = record.previous_routes[0] if record.previous_routes else None
    db.record_feedback(record.github_repository_id, label, note,
                       history.get("scan_run_id") if history else observation.get("scan_run_id") if observation else None, route,
                       str(Path(root).resolve() / "reports" / "latest.json"),
                       history.get("id") if history else None)
