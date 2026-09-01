import json
import tempfile
import unittest
from pathlib import Path

from pti.models import RepositoryRecord
from pti.storage import Database


def _repo(repo_id=7):
    return RepositoryRecord(repo_id, "example/project", "https://github.com/example/project")


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp_dir.name) / "state.db")
        self.db.initialize()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_observability_records_scan_candidate_decision_feedback_and_notification(self):
        db = self.db
        db.start_scan_run("scan-1", "2026-08-27T00:00:00Z")
        db.record_candidate_observation(
        "scan-1", _repo(), "AI_EXPERIENCE", "context engineering AI", 31,
        "USER_REVIEW_RECOMMENDED", "HIGH_PRIORITY", "STANDARD",
        [{"source": "README", "code": "HTTP_403"}],
        )
        db.finish_scan_run("scan-1", "SCAN_SUCCESS", 1, 0, "2026-08-27T00:00:02Z")
        db.record_chancellor_decision(7, {"ACTION": "WATCH", "BEST_ROUTE": "AI_EXPERIENCE"}, "packet.json", "scan-1")
        history_id = db.latest_chancellor_history(7)["id"]
        db.record_feedback(7, "USEFUL", "good", "scan-1", "AI_EXPERIENCE", "reports/latest.json", history_id)
        db.record_notification_event("scan-1", 7, "NOTIFICATION_NOT_REQUIRED", "NO_HIGH_SIGNAL", "reports/latest.json", "AI_EXPERIENCE")

        with db._connect() as connection:
            self.assertEqual(connection.execute("select count(*) from scan_runs").fetchone()[0], 1)
            observation = connection.execute("select * from candidate_observations").fetchone()
            self.assertEqual(tuple(observation[1:5]), ("scan-1", 7, "AI_EXPERIENCE", "context engineering AI"))
            self.assertEqual(json.loads(observation[9]), [{"source": "README", "code": "HTTP_403"}])
            self.assertEqual(connection.execute("select count(*) from chancellor_decision_history").fetchone()[0], 1)
            feedback = connection.execute("select scan_run_id, route, report_path, chancellor_history_id from user_feedback").fetchone()
            self.assertEqual(tuple(feedback), ("scan-1", "AI_EXPERIENCE", "reports/latest.json", history_id))
            self.assertEqual(connection.execute("select count(*) from notification_events").fetchone()[0], 1)


    def test_chancellor_history_is_append_only_while_current_decision_remains_unique(self):
        db = self.db
        db.upsert_repository(_repo())
        db.record_chancellor_decision(7, {"ACTION": "WATCH", "BEST_ROUTE": "AI_EXPERIENCE"}, "a.json", "scan-a")
        db.record_chancellor_decision(7, {"ACTION": "REFERENCE_ONLY", "BEST_ROUTE": "AI_AGENT"}, "b.json", "scan-b")

        with db._connect() as connection:
            self.assertEqual(connection.execute("select count(*) from chancellor_decisions").fetchone()[0], 1)
            self.assertEqual(connection.execute("select count(*) from chancellor_decision_history").fetchone()[0], 2)
            current = json.loads(connection.execute("select decision_json from chancellor_decisions where github_repository_id=7").fetchone()[0])
            self.assertEqual(current["ACTION"], "REFERENCE_ONLY")
