import json
import tempfile
import unittest
from pathlib import Path

from pti.bootstrap import initialize_project
from pti.dashboard_read_model import DashboardReadModel
from pti.models import RepositoryRecord
from pti.storage import Database


class DashboardReadModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "discovery.json").write_text(json.dumps({}), encoding="utf-8")
        (self.root / "config" / "local_capability_profile.json").write_text(json.dumps({}), encoding="utf-8")
        initialize_project(self.root, self.root / "config" / "discovery.json", self.root / "config" / "local_capability_profile.json")
        (self.root / "README.md").write_text("# Hello\n\nA document.", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_database_is_a_valid_empty_state(self):
        model = DashboardReadModel(self.root)
        snapshot = model.snapshot()
        self.assertEqual(snapshot["counts"]["total"], 0)
        self.assertEqual(snapshot["recent_discoveries"], [])
        self.assertEqual(snapshot["validating"], [])
        self.assertTrue(any(item["path"] == "README.md" for item in model.documents()))

    def test_document_path_traversal_is_rejected(self):
        model = DashboardReadModel(self.root)
        with self.assertRaises(ValueError):
            model.document_text("../README.md")
        with self.assertRaises(ValueError):
            model.document_text("C:/Windows/win.ini")

    def test_human_feedback_resolves_the_visible_decision_prompt(self):
        db = Database(self.root / "state" / "intelligence.db")
        db.upsert_repository(RepositoryRecord(7, "owner/repo", "https://github.com/owner/repo"))
        db.record_chancellor_decision(7, {
            "ACTION": "CANDIDATE_FOR_QUARANTINE",
            "BEST_ROUTE": "QUANT_DATA",
            "WHAT_IS_IT": "A test capability",
        }, "test.json")
        db.upsert_activation({
            "github_repository_id": 7,
            "activation_tier": "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL",
            "activation_state": "BLOCKED_HUMAN",
            "evidence_maturity": "REVIEWED",
            "pinned_version": None,
            "static_analysis_status": "BOUNDARY_REVIEWED",
            "isolated_test_status": "NOT_RUN",
            "trial_status": "NOT_ENABLED",
            "rollback_status": "UNKNOWN",
            "notes": "Awaiting a human choice.",
        })

        before = DashboardReadModel(self.root).capabilities()[0]
        self.assertTrue(before["requires_human_decision"])
        self.assertIsNone(before["human_decision"])

        db.record_feedback(7, "WATCH", "Keep it under observation.")
        after = DashboardReadModel(self.root).capabilities()[0]
        self.assertFalse(after["requires_human_decision"])
        self.assertEqual(after["human_decision"]["label"], "WATCH")

    def test_human_library_projection_separates_capabilities_methods_and_pending_work(self):
        db = Database(self.root / "state" / "intelligence.db")

        def add(repository_id, repository, action, activation_state):
            db.upsert_repository(RepositoryRecord(
                repository_id, repository, f"https://github.com/{repository}"
            ))
            db.record_chancellor_decision(repository_id, {
                "ACTION": action,
                "BEST_ROUTE": "AI_AGENT",
                "WHAT_IS_IT": repository,
            }, f"{repository_id}.json")
            db.upsert_activation({
                "github_repository_id": repository_id,
                "activation_tier": "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL" if action == "CANDIDATE_FOR_QUARANTINE" else "TIER_0_KNOWLEDGE_PATTERN",
                "activation_state": activation_state,
                "evidence_maturity": "USED" if activation_state == "USED" else "REVIEWED",
                "pinned_version": "abc123" if activation_state == "USED" else None,
                "static_analysis_status": "PASS" if activation_state == "USED" else "NOT_RUN",
                "isolated_test_status": "PASS" if activation_state == "USED" else "NOT_RUN",
                "trial_status": "ENABLED_CONTROLLED" if activation_state == "USED" else "NOT_ENABLED",
                "rollback_status": "READY",
                "notes": "test",
            })

        add(1, "tt-a1i/archify", "CANDIDATE_FOR_QUARANTINE", "USED")
        add(2, "github/spec-kit", "REFERENCE_ONLY", "ACTIVE_PATTERN")
        add(3, "bmad-code-org/BMAD-METHOD", "REFERENCE_ONLY", "ACTIVE_PATTERN")
        add(4, "FoundationAgents/MetaGPT", "REFERENCE_ONLY", "ACTIVE_PATTERN")
        add(5, "TauricResearch/TradingAgents", "REFERENCE_ONLY", "BLOCKED_HUMAN")
        add(6, "nieledran/backtesting-engine", "CANDIDATE_FOR_QUARANTINE", "BLOCKED_HUMAN")
        db.record_feedback(6, "APPROVE_FOR_REVIEW", "Approved once.")

        model = DashboardReadModel(self.root)
        cards = {item["repository"]: item for item in model.capabilities()}
        snapshot = model.snapshot()

        self.assertEqual(cards["tt-a1i/archify"]["human_category"], "USED")
        self.assertEqual(cards["github/spec-kit"]["human_category"], "ADOPTED_METHOD")
        self.assertEqual(cards["FoundationAgents/MetaGPT"]["human_category"], "NOT_ADOPTED")
        self.assertEqual(cards["TauricResearch/TradingAgents"]["human_category"], "HUMAN_DECISION")
        self.assertTrue(cards["TauricResearch/TradingAgents"]["requires_human_decision"])
        self.assertEqual(cards["nieledran/backtesting-engine"]["human_category"], "VALIDATING")
        self.assertFalse(cards["nieledran/backtesting-engine"]["requires_human_decision"])
        self.assertEqual(snapshot["counts"]["usable"], 1)
        self.assertEqual(snapshot["counts"]["adopted_methods"], 2)
        self.assertEqual(snapshot["counts"]["processing"], 1)
        self.assertEqual(snapshot["counts"]["watchlist"], 0)
        self.assertEqual(len(snapshot["my_capabilities_cards"]), 1)
        self.assertEqual(len(snapshot["method_cards"]), 2)


if __name__ == "__main__":
    unittest.main()
