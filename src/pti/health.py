import json
import sqlite3
import subprocess
import time
from pathlib import Path

from .packet_lifecycle import active_pending_count


def _task(name: str) -> dict:
    try:
        completed = subprocess.run(["schtasks", "/query", "/tn", name, "/fo", "LIST", "/v"],
                                   capture_output=True, text=True, encoding="oem", errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        return {"name": name, "status": "QUERY_FAILED", "error": str(error)}
    values = {}
    for line in completed.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return {"name": name, "status": values.get("Status", "UNKNOWN"),
            "last_result": values.get("Last Result", "UNKNOWN"),
            "last_run": values.get("Last Run Time", "UNKNOWN"),
            "next_run": values.get("Next Run Time", "UNKNOWN"),
            "action": values.get("Task To Run", "UNKNOWN"), "query_exit": completed.returncode}


def _latest(connection, table: str) -> dict | None:
    row = connection.execute(f"SELECT * FROM {table} ORDER BY started_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def health_report(root: str | Path) -> dict:
    root = Path(root).resolve()
    state = root / "state"
    db_path = state / "intelligence.db"
    if not db_path.is_file():
        return {
            "status": "NOT_INITIALIZED",
            "active_pending": 0,
            "locks": {"scan.lock": "ABSENT", "chancellor.lock": "ABSENT"},
            "tasks": [],
            "latest_scan_run": None,
            "latest_stage_b_run": None,
            "decision_history_count": 0,
            "unique_decision_repositories": 0,
            "issues": ["DATABASE_NOT_INITIALIZED"],
        }
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        scan = _latest(connection, "scan_runs")
        stage_b = _latest(connection, "stage_b_runs")
        history_count = connection.execute("SELECT count(*) FROM chancellor_decision_history").fetchone()[0]
        unique_history = connection.execute("SELECT count(DISTINCT github_repository_id) FROM chancellor_decision_history").fetchone()[0]
        legacy_incomplete = connection.execute("SELECT count(*) FROM scan_runs WHERE completed_at IS NULL").fetchone()[0]
    finally:
        connection.close()
    locks = {}
    stale_locks = []
    for name in ("scan.lock", "chancellor.lock"):
        path = state / name
        if not path.exists():
            locks[name] = "ABSENT"
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            age = time.time() - path.stat().st_mtime
            locks[name] = {"state": "PRESENT", "age_seconds": round(age), "metadata": payload}
            if age >= 900:
                stale_locks.append(name)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            locks[name] = {"state": "MALFORMED", "error": str(error)}
            stale_locks.append(name)
    tasks = [_task(r"\PersonalTechIntelligence\PTI-Radar-Scan"),
             _task(r"\PersonalTechIntelligence\PTI-Chancellor")]
    task_failures = [task["name"] for task in tasks if task.get("last_result") not in {"0", "UNKNOWN"}]
    active = active_pending_count(root / "chancellor_pending")
    status = "HEALTHY"
    issues = []
    if stale_locks:
        status = "NOT_EVALUATED"
        issues.append("STALE_OR_MALFORMED_LOCK")
    if legacy_incomplete:
        status = "NOT_EVALUATED"
        issues.append("INCOMPLETE_SCAN_RUN")
    if active:
        status = "NOT_EVALUATED"
        issues.append("ACTIVE_PENDING_PACKETS")
    if task_failures:
        status = "NOT_EVALUATED"
        issues.append("TASK_LAST_RESULT_NONZERO")
    if history_count > unique_history and status == "HEALTHY":
        status = "DEGRADED_HISTORY_ONLY"
        issues.append("LEGACY_DUPLICATE_HISTORY_PRESERVED")
    return {"status": status, "active_pending": active, "locks": locks, "tasks": tasks,
            "latest_scan_run": scan, "latest_stage_b_run": stage_b,
            "decision_history_count": history_count, "unique_decision_repositories": unique_history,
            "issues": issues}
