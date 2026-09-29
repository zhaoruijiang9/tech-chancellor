import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pti.health import health_report
from pti.capability_intelligence import CapabilityStore
from pti.storage import Database


class HealthReportTests(unittest.TestCase):
    def test_upstream_failure_is_visible_without_reclassifying_radar(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chancellor_pending").mkdir()
            path = root / "state" / "intelligence.db"
            Database(path).initialize()
            store = CapabilityStore(path)
            store.record_upstream_run({
                "run_id": "upstream-1",
                "started_at": "2026-09-29T01:00:00Z",
                "completed_at": "2026-09-29T01:01:00Z",
                "status": "FAILED",
                "checked": 0,
                "baseline_captured": 0,
                "no_change": 0,
                "changes_detected": 0,
                "failures": 1,
                "request_count": 1,
                "failure_class": "NETWORK",
            })
            with patch("pti.health._task", return_value={"name": "task", "last_result": "0"}):
                report = health_report(root)
            self.assertEqual(report["status"], "DEGRADED")
            self.assertIn("UPSTREAM_CHECK_NETWORK_FAILED", report["issues"])
            self.assertEqual(report["latest_upstream_run"]["status"], "FAILED")

    def test_health_report_separates_legacy_history_from_runtime_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state").mkdir()
            (root / "chancellor_pending").mkdir()
            connection = sqlite3.connect(root / "state" / "intelligence.db")
            connection.executescript("""
                CREATE TABLE scan_runs (run_id TEXT, started_at TEXT, completed_at TEXT);
                CREATE TABLE stage_b_runs (run_id TEXT, started_at TEXT, completed_at TEXT);
                CREATE TABLE chancellor_decision_history (github_repository_id INTEGER);
                INSERT INTO scan_runs VALUES ('s1', '2026-08-30T00:00:00Z', '2026-08-30T00:01:00Z');
                INSERT INTO stage_b_runs VALUES ('b1', '2026-08-30T00:02:00Z', '2026-08-30T00:03:00Z');
                INSERT INTO chancellor_decision_history VALUES (1);
                INSERT INTO chancellor_decision_history VALUES (1);
            """)
            connection.close()
            with patch("pti.health._task", return_value={"name": "task", "last_result": "0"}):
                result = health_report(root)
            self.assertEqual(result["status"], "DEGRADED_HISTORY_ONLY")
            self.assertIn("LEGACY_DUPLICATE_HISTORY_PRESERVED", result["issues"])
