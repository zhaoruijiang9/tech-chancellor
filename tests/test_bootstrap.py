import json
import tempfile
import unittest
from pathlib import Path

from pti.bootstrap import initialize_project
from pti.health import health_report


class BootstrapTests(unittest.TestCase):
    def test_initialize_is_idempotent_and_creates_empty_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "discovery.json"
            profile = root / "profile.json"
            config.write_text(json.dumps({"request_budget": 1}), encoding="utf-8")
            profile.write_text(json.dumps({"AI_AGENT": "UNKNOWN"}), encoding="utf-8")

            first = initialize_project(root, config, profile)
            second = initialize_project(root, config, profile)

            self.assertEqual(first["status"], "INITIALIZED")
            self.assertEqual(second["created_directories"], [])
            self.assertTrue((root / "state" / "intelligence.db").is_file())
            report = health_report(root)
            self.assertIn(report["status"], {"HEALTHY", "DEGRADED_HISTORY_ONLY"})
            self.assertEqual(report["decision_history_count"], 0)

    def test_health_reports_missing_database_without_crashing(self):
        with tempfile.TemporaryDirectory() as directory:
            result = health_report(directory)
            self.assertEqual(result["status"], "NOT_INITIALIZED")
            self.assertIn("DATABASE_NOT_INITIALIZED", result["issues"])


if __name__ == "__main__":
    unittest.main()
