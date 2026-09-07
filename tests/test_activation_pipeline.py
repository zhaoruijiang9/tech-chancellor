import tempfile
import unittest
from pathlib import Path

from pti.activation_runtime import postprocess_semantic_decision
from pti.models import RepositoryRecord
from pti.storage import Database


class ActivationPipelineTests(unittest.TestCase):
    def test_tier_zero_is_promoted_without_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.upsert_repository(RepositoryRecord(1, "owner/pattern", "https://github.com/owner/pattern"))
            postprocess_semantic_decision(db, 1, {
                "ACTION": "REFERENCE_ONLY", "BEST_ROUTE": "AI_AGENT",
                "WHAT_IS_IT": "A workflow pattern", "CAPABILITY_DELTA": "pattern reference",
            })
            self.assertEqual(db.get_activation(1)["activation_state"], "ACTIVE_PATTERN")
            self.assertEqual(db.list_activation_queue(), [])

    def test_low_risk_candidate_is_queued_without_blocking_semantic_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.upsert_repository(RepositoryRecord(2, "owner/tool", "https://github.com/owner/tool"))
            result = postprocess_semantic_decision(db, 2, {
                "ACTION": "CANDIDATE_FOR_QUARANTINE", "BEST_ROUTE": "AI_AGENT",
                "WHAT_IS_IT": "A local tool", "CAPABILITY_DELTA": "bounded local output",
            })
            self.assertEqual(result["status"], "ACTIVATION_QUEUED")
            self.assertEqual(db.list_activation_queue("PENDING")[0]["desired_next_state"], "QUARANTINED")


if __name__ == "__main__":
    unittest.main()
