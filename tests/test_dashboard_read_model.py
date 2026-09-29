import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pti.bootstrap import initialize_project
from pti.dashboard_read_model import DashboardReadModel
from pti.models import RepositoryRecord
from pti.storage import Database
from pti.capability_intelligence import CapabilityStore


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
        self.assertEqual(snapshot["capability_entities"], [])
        self.assertEqual(snapshot["method_entities"], [])
        self.assertEqual(snapshot["stale_reviews"], [])

    def test_upstream_monitor_failure_is_a_visible_dashboard_reminder(self):
        with patch("pti.dashboard_read_model.health_report", return_value={
            "status": "DEGRADED", "issues": ["UPSTREAM_CHECK_NETWORK_FAILED"],
        }):
            snapshot = DashboardReadModel(self.root).snapshot()
        self.assertEqual(snapshot["status"], "提醒")

    def test_capability_entity_is_distinct_from_source_and_shows_implementation(self):
        store = CapabilityStore(self.root / "state" / "intelligence.db")
        store.upsert_source("github:1", "GITHUB_REPOSITORY", "owner/archify", "https://github.com/owner/archify", 1)
        store.upsert_implementation("impl:archify", "github:1", "Archify", "TOOL", "USED")
        store.upsert_capability("ARCHITECTURE_VIEW", "项目架构可视化", "生成可检验的架构视图")
        store.link_implementation_capability("impl:archify", "ARCHITECTURE_VIEW", "NEW_CAPABILITY", "controlled use")
        store.set_personal_state("CAPABILITY", "ARCHITECTURE_VIEW", "USED", "real use")
        store.set_personal_state("CAPABILITY", "ARCHITECTURE_VIEW", "AVAILABLE", "controlled trial")

        snapshot = DashboardReadModel(self.root).snapshot()

        self.assertEqual(snapshot["counts"]["reviewed_projects"], 0)
        self.assertEqual(snapshot["counts"]["used_capabilities"], 1)
        self.assertEqual(snapshot["capability_entities"][0]["capability_id"], "ARCHITECTURE_VIEW")
        self.assertEqual(snapshot["capability_entities"][0]["implementations"][0]["source_name"], "owner/archify")

    def test_method_entities_need_real_workflow_evidence(self):
        store = CapabilityStore(self.root / "state" / "intelligence.db")
        store.upsert_method("SPEC", None, "规格先行", "Define acceptance first")
        store.record_method_evidence("SPEC", "DISTILLED_REFERENCE", "docs/spec.md", "notes", False)
        self.assertEqual(DashboardReadModel(self.root).snapshot()["method_entities"], [])
        store.record_method_evidence("SPEC", "WORKFLOW_MECHANISM", "skills/spec/SKILL.md", "Codex skill", True)
        store.record_method_evidence("SPEC", "VERIFIED_USE", "reports/task.md", "used", True)
        self.assertEqual(DashboardReadModel(self.root).snapshot()["method_entities"][0]["method_id"], "SPEC")

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
        db.record_real_use(1, "test-project", "architecture", "USED_SUCCESSFULLY", "test output", real_task_evidence=True)
        add(2, "github/spec-kit", "REFERENCE_ONLY", "ACTIVE_PATTERN")
        add(3, "bmad-code-org/BMAD-METHOD", "REFERENCE_ONLY", "ACTIVE_PATTERN")
        add(4, "FoundationAgents/MetaGPT", "REFERENCE_ONLY", "ACTIVE_PATTERN")
        add(5, "TauricResearch/TradingAgents", "REFERENCE_ONLY", "BLOCKED_HUMAN")
        add(6, "nieledran/backtesting-engine", "CANDIDATE_FOR_QUARANTINE", "BLOCKED_HUMAN")
        db.record_feedback(6, "APPROVE_FOR_REVIEW", "Approved once.")
        CapabilityStore(self.root / "state" / "intelligence.db").migrate_reviewed_sources()

        model = DashboardReadModel(self.root)
        cards = {item["repository"]: item for item in model.capabilities()}
        snapshot = model.snapshot()

        self.assertEqual(cards["tt-a1i/archify"]["human_category"], "USED")
        self.assertEqual(cards["github/spec-kit"]["human_category"], "WATCHLIST")
        self.assertEqual(cards["github/spec-kit"]["item_kind"], "METHOD_SOURCE")
        self.assertEqual(cards["FoundationAgents/MetaGPT"]["human_category"], "NOT_ADOPTED")
        self.assertEqual(cards["TauricResearch/TradingAgents"]["human_category"], "HUMAN_DECISION")
        self.assertTrue(cards["TauricResearch/TradingAgents"]["requires_human_decision"])
        self.assertEqual(cards["nieledran/backtesting-engine"]["human_category"], "WAITING_VALIDATION")
        self.assertFalse(cards["nieledran/backtesting-engine"]["requires_human_decision"])
        self.assertEqual(snapshot["counts"]["usable"], 1)
        self.assertEqual(snapshot["counts"]["adopted_methods"], 0)
        self.assertEqual(snapshot["counts"]["processing"], 0)
        self.assertEqual(snapshot["counts"]["waiting_validation"], 1)
        self.assertEqual(snapshot["counts"]["watchlist"], 2)
        self.assertEqual(len(snapshot["my_capabilities_cards"]), 1)
        self.assertEqual(snapshot["my_capabilities_cards"][0]["capability_id"], "PROJECT_ARCHITECTURE_VISUALIZATION")
        self.assertEqual(len(snapshot["method_cards"]), 0)


if __name__ == "__main__":
    unittest.main()
