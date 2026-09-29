import sqlite3
import tempfile
import unittest
from pathlib import Path

from pti.capability_intelligence import CapabilityStore
from pti.models import RepositoryRecord
from pti.storage import Database


REVIEWED = [
    (1078079172, "ComposioHQ/awesome-claude-skills"),
    (660551251, "FoundationAgents/MetaGPT"),
    (909213664, "TauricResearch/TradingAgents"),
    (965615190, "bmad-code-org/BMAD-METHOD"),
    (970357908, "cased/kit"),
    (995920026, "chunkhound/chunkhound"),
    (929121414, "coleam00/archon"),
    (1042367133, "github/spec-kit"),
    (1123446919, "gmickel/flow-next"),
    (1129940957, "headroomlabs-ai/headroom"),
    (552661142, "langchain-ai/langchain"),
    (1188951122, "nieledran/backtesting-engine"),
    (1211139949, "tt-a1i/archify"),
    (1007681088, "volcengine/MineContext"),
]


class CapabilitySchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "intelligence.db"
        self.db = Database(self.path)
        self.db.initialize()
        self.store = CapabilityStore(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_database_has_normalized_capability_tables(self):
        connection = sqlite3.connect(self.path)
        try:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        finally:
            connection.close()
        self.assertTrue({
            "capability_sources",
            "capability_implementations",
            "capabilities",
            "implementation_capabilities",
            "methods",
            "method_evidence",
            "capability_relations",
            "personal_states",
            "source_freshness",
            "upstream_check_runs",
            "delta_review_queue",
        }.issubset(tables))
        self.assertEqual(self.store.library_snapshot()["sources"], [])

    def test_one_capability_can_have_multiple_implementations(self):
        self.store.upsert_source("github:1", "GITHUB_REPOSITORY", "owner/one", "https://github.com/owner/one", 1)
        self.store.upsert_source("github:2", "GITHUB_REPOSITORY", "owner/two", "https://github.com/owner/two", 2)
        self.store.upsert_capability("CODE_SEARCH", "代码检索", "跨文件定位代码")
        for suffix in ("one", "two"):
            self.store.upsert_implementation(f"impl:{suffix}", f"github:{1 if suffix == 'one' else 2}", suffix, "TOOL")
            self.store.link_implementation_capability(
                f"impl:{suffix}", "CODE_SEARCH", "OVERLAP", "test evidence"
            )

        capability = self.store.get_capability("CODE_SEARCH")

        self.assertEqual(
            {item["implementation_id"] for item in capability["implementations"]},
            {"impl:one", "impl:two"},
        )

    def test_one_repository_implementation_can_provide_multiple_capabilities(self):
        self.store.upsert_source("github:1", "GITHUB_REPOSITORY", "owner/tool", "https://github.com/owner/tool", 1)
        self.store.upsert_implementation("impl:tool", "github:1", "tool", "TOOL")
        for capability_id in ("CODE_SEARCH", "ARCHITECTURE_MAP"):
            self.store.upsert_capability(capability_id, capability_id, capability_id)
            self.store.link_implementation_capability(
                "impl:tool", capability_id, "NEW_CAPABILITY", "test evidence"
            )

        implementation = self.store.get_implementation("impl:tool")

        self.assertEqual(
            {item["capability_id"] for item in implementation["capabilities"]},
            {"CODE_SEARCH", "ARCHITECTURE_MAP"},
        )

    def test_method_requires_mechanism_and_verified_use_to_be_adopted(self):
        self.store.upsert_method("SPEC_FIRST", None, "规格先行", "Write a spec before implementation")
        self.store.record_method_evidence(
            "SPEC_FIRST", "DISTILLED_REFERENCE", "docs/reference.md", "Reference note", qualifies=False
        )
        self.assertEqual(self.store.get_method("SPEC_FIRST")["adoption_state"], "KNOWLEDGE_REFERENCE")

        self.store.record_method_evidence(
            "SPEC_FIRST", "WORKFLOW_MECHANISM", "skills/spec-first/SKILL.md", "Codex skill", qualifies=True
        )
        self.assertEqual(self.store.get_method("SPEC_FIRST")["adoption_state"], "KNOWLEDGE_REFERENCE")

        self.store.record_method_evidence(
            "SPEC_FIRST", "VERIFIED_USE", "reports/task-1.md", "Observed use through that skill", qualifies=True
        )
        self.assertEqual(self.store.get_method("SPEC_FIRST")["adoption_state"], "ADOPTED")

    def test_capability_relations_require_evidence_and_are_idempotent(self):
        self.store.upsert_capability("SPEC", "规格先行", "")
        self.store.upsert_capability("GATES", "验收门", "")
        with self.assertRaises(ValueError):
            self.store.upsert_capability_relation("SPEC", "COMPLEMENTS", "GATES", "")
        self.store.upsert_capability_relation("SPEC", "COMPLEMENTS", "GATES", "source evidence")
        self.store.upsert_capability_relation("SPEC", "COMPLEMENTS", "GATES", "source evidence")
        self.assertEqual(len(self.store.list_capability_relations()), 1)

    def test_reviewed_repository_migration_is_additive_and_idempotent(self):
        for repository_id, repository in REVIEWED:
            self.db.upsert_repository(RepositoryRecord(
                repository_id, repository, f"https://github.com/{repository}"
            ))
            self.db.record_chancellor_decision(repository_id, {
                "ACTION": "REFERENCE_ONLY",
                "BEST_ROUTE": "AI_AGENT",
                "WHAT_IS_IT": repository,
            }, f"{repository_id}.json")
            self.db.upsert_activation({
                "github_repository_id": repository_id,
                "activation_tier": "TIER_0_KNOWLEDGE_PATTERN",
                "activation_state": "ACTIVE_PATTERN",
                "notes": "test",
            })
        self.db.upsert_activation({
            "github_repository_id": 1211139949,
            "activation_tier": "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL",
            "activation_state": "USED",
            "evidence_maturity": "USED",
            "pinned_version": "abc123",
            "isolated_test_status": "PASS",
            "trial_status": "ENABLED_CONTROLLED",
            "rollback_status": "READY",
            "notes": "used",
        })
        self.db.record_real_use(1211139949, "test-project", "architecture", "USED_SUCCESSFULLY", "test output", real_task_evidence=True)
        self.db.record_feedback(1188951122, "APPROVE_FOR_REVIEW", "Approved once")

        first = self.store.migrate_reviewed_sources()
        second = self.store.migrate_reviewed_sources()
        self.store.set_personal_state("IMPLEMENTATION", "impl:nieledran/backtesting-engine", "VERIFIED", "later: manual evidence")
        third = self.store.migrate_reviewed_sources()

        self.assertEqual(first["reviewed_sources"], 14)
        self.assertEqual(second["reviewed_sources"], 14)
        self.assertEqual(third["reviewed_sources"], 14)
        snapshot = self.store.library_snapshot()
        self.assertEqual(len(snapshot["sources"]), 14)
        self.assertEqual(len(snapshot["implementations"]), 14)
        self.assertGreater(len(snapshot["capabilities"]), 1)
        self.assertEqual(snapshot["adopted_methods"], [])
        archify = self.store.get_capability("PROJECT_ARCHITECTURE_VISUALIZATION")
        self.assertEqual(
            {state["state"] for state in archify["personal_states"]},
            {"VERIFIED", "USED", "AVAILABLE"},
        )
        backtesting = self.store.get_implementation("impl:nieledran/backtesting-engine")
        self.assertEqual(
            {state["state"] for state in backtesting["personal_states"]},
            {"APPROVED_WAITING_VALIDATION", "VERIFIED"},
        )


if __name__ == "__main__":
    unittest.main()
