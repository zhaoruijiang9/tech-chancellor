import tempfile
import unittest
from pathlib import Path

from pti.activation_runtime import postprocess_semantic_decision
from pti.models import RepositoryRecord
from pti.stage_b import run_stage_b
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

    def test_hazardous_candidate_is_human_gated_before_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.upsert_repository(RepositoryRecord(3, "owner/token-tool", "https://github.com/owner/token-tool"))
            result = postprocess_semantic_decision(db, 3, {
                "ACTION": "CANDIDATE_FOR_QUARANTINE", "BEST_ROUTE": "AI_AGENT",
                "WHAT_IS_IT": "A tool requiring an API token", "CAPABILITY_DELTA": "local output",
            })
            self.assertEqual(result["status"], "ACTIVATION_BLOCKED_HUMAN")
            self.assertEqual(db.list_activation_queue("BLOCKED_HUMAN")[0]["attempt_count"], 0)

    def test_reference_pattern_does_not_hide_new_executable_review(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.upsert_repository(RepositoryRecord(4, "owner/evolving-tool", "https://github.com/owner/evolving-tool"))
            db.upsert_activation({"github_repository_id": 4, "activation_tier": "TIER_0_KNOWLEDGE_PATTERN",
                                  "activation_state": "ACTIVE_PATTERN"})
            result = postprocess_semantic_decision(db, 4, {
                "ACTION": "CANDIDATE_FOR_QUARANTINE", "BEST_ROUTE": "AI_AGENT",
                "WHAT_IS_IT": "A local tool", "CAPABILITY_DELTA": "bounded output",
            })
            self.assertEqual(result["status"], "ACTIVATION_QUEUED")

    def test_stage_b_does_not_execute_an_existing_activation_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = Database(root / "state" / "intelligence.db")
            db.initialize()
            db.enqueue_activation(9, "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL", "QUARANTINED", "low risk")
            result = run_stage_b(root)
            self.assertEqual(result["codex_invocations"], 0)
            self.assertEqual(db.list_activation_queue()[0]["status"], "PENDING")
            self.assertEqual(db.list_activation_queue()[0]["attempt_count"], 0)


if __name__ == "__main__":
    unittest.main()
