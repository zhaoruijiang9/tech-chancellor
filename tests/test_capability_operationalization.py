import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pti.capability_intelligence import CapabilityStore, project_activation_state
from pti.capability_invocation import active_bindings, invocation_health, normalize_github_link
from pti.cli import run_once
from pti.activation_readiness import audit_current_library, second_pilot_candidates
from pti.discovery import run_discovery
from pti.dashboard_read_model import DashboardReadModel
from pti.github_api import ApiResult
from pti.models import EnrichmentEvidence, RepositoryRecord
from pti.storage import Database


def repo(repository_id, name, stars=100):
    return RepositoryRecord(repository_id, name, f"https://github.com/{name}", stars=stars,
                            description=f"Useful agent workflow {name}")


class Client:
    def __init__(self, search=None, lookups=None, fail_lookup=False):
        self.search = search or []
        self.lookups = lookups or {}
        self.fail_lookup = fail_lookup
        self.looked_up = []

    def search_repositories(self, query, page=1, per_page=5):
        return ApiResult(items=self.search)

    def get_repository(self, owner, name):
        self.looked_up.append(f"{owner}/{name}")
        if self.fail_lookup:
            raise RuntimeError("source unavailable")
        return ApiResult(items=[self.lookups[f"{owner}/{name}"]])

    def enrich_repository(self, owner, name, level="STANDARD"):
        return EnrichmentEvidence(level=level, readme="A documented agent workflow")


class OperationalizationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.db = Database(self.root / "state" / "intelligence.db")
        self.db.initialize()
        self.db.upsert_repository(repo(7, "example/skill-index"))
        store = CapabilityStore(self.db.path)
        store.upsert_source("github:7", "GITHUB_REPOSITORY", "example/skill-index",
                            "https://github.com/example/skill-index", 7)
        store.upsert_implementation("impl:example/skill-index", "github:7", "index", "TOOL_OR_WORKFLOW")
        store.upsert_capability("SKILL_ECOSYSTEM_DISCOVERY", "Skill discovery", "Index")
        store.link_implementation_capability("impl:example/skill-index", "SKILL_ECOSYSTEM_DISCOVERY",
                                              "COMPLEMENT", "review")
        self.db.upsert_activation({"github_repository_id": 7, "activation_tier": "TIER_1_DECLARATIVE_SKILL",
                                   "activation_state": "TRIAL_ENABLED", "isolated_test_status": "PASS",
                                   "rollback_status": "READY"})
        project_activation_state(self.db.path, 7, "AVAILABLE", "test-activation")
        base = self.root / "managed_capabilities" / "repo-7"
        (base / "versions" / ("a" * 40)).mkdir(parents=True)
        (base / "active.json").write_text(json.dumps({"sha": "a" * 40}), encoding="utf-8")
        (base / "versions" / ("a" * 40) / "README.md").write_text(
            "- [agent workflow](https://github.com/new/workflow/tree/main/skill)\n"
            "- [agent extra](https://github.com/new/workflow/blob/main/README.md)\n"
            "- [agent old](https://github.com/old/existing/tree/main/skill)\n",
            encoding="utf-8")
        self.bindings = [{"capability_id": "SKILL_ECOSYSTEM_DISCOVERY",
                          "implementation_id": "impl:example/skill-index", "consumer": "RADAR_DISCOVERY",
                          "adapter_type": "READ_ONLY_MARKDOWN_INDEX", "intent_terms": ["agent"],
                          "invoke_entrypoint": "pti.capability_invocation.invoke_index",
                          "max_raw_results": 10, "max_normalized_candidates": 5,
                          "max_new_candidates": 2, "timeout_seconds": 3}]
        self.config = {"query_groups": [{"domain": "AI_AGENT", "queries": ["AI coding agent workflow"]}],
                       "per_query_cap": 5, "total_candidate_cap": 20, "enrichment_candidate_cap": 3}
        self.db.start_scan_run("real-run", "2026-09-29T00:00:00Z")

    def test_contract_binds_only_available_implementation(self):
        self.assertEqual(len(active_bindings(self.db, self.root, self.bindings, "RADAR_DISCOVERY")), 1)
        self.db.upsert_activation({"github_repository_id": 7, "activation_tier": "TIER_1_DECLARATIVE_SKILL",
                                   "activation_state": "ROLLED_BACK"})
        self.assertEqual(active_bindings(self.db, self.root, self.bindings, "RADAR_DISCOVERY"), [])

    def test_used_implementation_is_bound_only_once(self):
        self.db.upsert_activation({"github_repository_id": 7, "activation_tier": "TIER_1_DECLARATIVE_SKILL",
                                   "activation_state": "USED", "isolated_test_status": "PASS",
                                   "rollback_status": "READY"})
        project_activation_state(self.db.path, 7, "USED", "real-use:test")
        self.assertEqual(len(active_bindings(self.db, self.root, self.bindings, "RADAR_DISCOVERY")), 1)

    def test_executable_adapter_is_never_auto_bound(self):
        unsafe = [{**self.bindings[0], "adapter_type": "EXECUTABLE_PYTHON"}]
        self.assertEqual(active_bindings(self.db, self.root, unsafe, "RADAR_DISCOVERY"), [])

    def test_unrecognized_entrypoint_is_not_bound(self):
        wrong = [{**self.bindings[0], "invoke_entrypoint": "third_party.run"}]
        self.assertEqual(active_bindings(self.db, self.root, wrong, "RADAR_DISCOVERY"), [])

    def test_binding_cannot_select_another_implementation_of_same_capability(self):
        wrong = [{**self.bindings[0], "implementation_id": "impl:other/index"}]
        self.assertEqual(active_bindings(self.db, self.root, wrong, "RADAR_DISCOVERY"), [])

    def test_link_normalization_rejects_non_github_and_nested_paths(self):
        self.assertEqual(normalize_github_link("https://github.com/Owner/Repo/tree/main/skill"), "Owner/Repo")
        self.assertIsNone(normalize_github_link("https://github.com.evil.test/Owner/Repo"))
        self.assertIsNone(normalize_github_link("https://github.com/Owner"))

    def test_material_use_requires_new_candidate_and_semantic_review(self):
        self.db.upsert_repository(repo(8, "old/existing"))
        client = Client(lookups={"new/workflow": repo(9, "new/workflow")})
        result = run_discovery(self.config, client, self.db, {}, "real-run",
                               capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(client.looked_up, ["new/workflow"])
        self.assertEqual(len([d for d in result.decisions if d.candidate.github_repository_id == 9]), 1)
        self.assertTrue(next(d for d in result.decisions if d.candidate.github_repository_id == 9).semantic_review)
        invocation = self.db.list_capability_invocations()[0]
        self.assertEqual(invocation["consumer"], "RADAR_DISCOVERY")
        self.assertEqual(invocation["material_use"], 1)
        self.assertTrue(invocation["invoked_at"].endswith("Z"))
        self.assertEqual(self.db.get_activation(7)["activation_state"], "USED")
        self.assertEqual(invocation_health(self.db, "impl:example/skill-index")["consecutive_failures"], 0)

    def test_duplicate_or_unreviewed_result_stays_available(self):
        self.db.upsert_repository(repo(8, "old/existing"))
        client = Client(search=[repo(9, "new/workflow")], lookups={"new/workflow": repo(9, "new/workflow")})
        result = run_discovery(self.config, client, self.db, {}, "real-run",
                               capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(len(result.decisions), 1)
        self.assertEqual(client.looked_up, [])
        self.assertEqual(self.db.list_capability_invocations()[0]["material_use"], 0)
        self.assertEqual(self.db.get_activation(7)["activation_state"], "TRIAL_ENABLED")

    def test_capability_failure_is_soft_and_health_is_recorded(self):
        client = Client(search=[repo(11, "github/ordinary")], fail_lookup=True)
        result = run_discovery(self.config, client, self.db, {}, "real-run",
                               capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(len(result.decisions), 1)
        self.assertEqual(result.failures, [])
        invocation = self.db.list_capability_invocations()[0]
        self.assertEqual(invocation["success"], 0)
        self.assertEqual(invocation_health(self.db, "impl:example/skill-index")["consecutive_failures"], 1)

    def test_invalid_binding_does_not_fail_radar(self):
        client = Client(search=[repo(11, "github/ordinary")])
        invalid = [{**self.bindings[0], "timeout_seconds": "invalid"}]
        result = run_discovery(self.config, client, self.db, {}, "real-run",
                               capability_root=self.root, consumer_bindings=invalid)
        self.assertEqual(len(result.decisions), 1)
        self.assertEqual(result.failures, [])

    def test_no_semantic_review_does_not_promote_used(self):
        self.config["enrichment_candidate_cap"] = 0
        client = Client(lookups={"new/workflow": repo(9, "new/workflow")})
        run_discovery(self.config, client, self.db, {}, "real-run",
                      capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(self.db.list_capability_invocations()[0]["material_use"], 0)
        self.assertEqual(self.db.get_activation(7)["activation_state"], "TRIAL_ENABLED")

    def test_missing_readme_evidence_does_not_promote_used(self):
        self.db.upsert_repository(repo(8, "old/existing"))

        class NoReadmeClient(Client):
            def enrich_repository(self, owner, name, level="STANDARD"):
                return EnrichmentEvidence(level=level)

        client = NoReadmeClient(lookups={"new/workflow": repo(9, "new/workflow")})
        run_discovery(self.config, client, self.db, {}, "real-run",
                      capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(self.db.list_capability_invocations()[0]["material_use"], 0)
        self.assertEqual(self.db.get_activation(7)["activation_state"], "TRIAL_ENABLED")

    def test_production_run_writes_existing_review_artifacts_and_use_evidence(self):
        self.db.upsert_repository(repo(8, "old/existing"))
        config_dir = self.root / "config"
        config_dir.mkdir()
        (config_dir / "discovery.json").write_text(json.dumps(self.config), encoding="utf-8")
        (config_dir / "profile.json").write_text("{}", encoding="utf-8")
        (config_dir / "capability_consumers.json").write_text(
            json.dumps({"bindings": self.bindings}), encoding="utf-8")
        client = Client(lookups={"new/workflow": repo(9, "new/workflow")})
        with patch("pti.cli.GitHubClient", return_value=client):
            result = run_once(self.root, config_dir / "discovery.json", config_dir / "profile.json")
        self.assertEqual(result["status"], "SCAN_SUCCESS")
        self.assertTrue(result["capability_invocations"][0]["material_use"])
        self.assertEqual(self.db.get_activation(7)["activation_state"], "USED")
        packets = list((self.root / "chancellor_pending").glob("9--*.json"))
        self.assertEqual(len(packets), 1)
        self.assertEqual(json.loads(packets[0].read_text(encoding="utf-8"))["repository_identity"]["canonical_owner_repo"], "new/workflow")

    def test_discovery_budget_limits_github_lookups(self):
        self.bindings[0]["max_new_candidates"] = 1
        client = Client(lookups={"new/workflow": repo(9, "new/workflow"),
                                 "old/existing": repo(8, "old/existing")})
        run_discovery(self.config, client, self.db, {}, "real-run",
                      capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(client.looked_up, ["new/workflow"])

    def test_single_review_slot_has_no_capability_source_privilege(self):
        self.db.upsert_repository(repo(8, "old/existing"))
        self.config["total_candidate_cap"] = 1
        self.config["enrichment_candidate_cap"] = 1
        client = Client(search=[repo(11, "github/ordinary", stars=10000)],
                        lookups={"new/workflow": repo(9, "new/workflow")})
        result = run_discovery(self.config, client, self.db, {}, "real-run",
                               capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual([item.candidate.github_repository_id for item in result.decisions], [11])
        self.assertTrue(result.decisions[0].semantic_review)
        self.assertEqual(result.capability_invocations[0]["selected_new_count"], 0)

    def test_irrelevant_index_result_is_not_material_use(self):
        self.bindings[0]["intent_terms"] = ["research"]
        self.bindings[0]["intent_rules"] = {"research": {"domain": "QUANT_DATA",
            "required_any": ["quant", "financial", "trading", "market data"]}}
        base = self.root / "managed_capabilities" / "repo-7" / "versions" / ("a" * 40)
        (base / "README.md").write_text(
            "- [family research](https://github.com/new/family-history-research-skill)", encoding="utf-8")
        self.config["query_groups"][0]["queries"] = ["quant research data language:python"]
        client = Client(lookups={"new/family-history-research-skill":
                                 repo(9, "new/family-history-research-skill")})
        result = run_discovery(self.config, client, self.db, {}, "real-run",
                               capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(result.capability_invocations[0]["new_count"], 0)
        self.assertEqual(result.capability_invocations[0]["rejected_irrelevant_count"], 1)
        self.assertEqual(self.db.get_activation(7)["activation_state"], "TRIAL_ENABLED")

    def test_invocation_record_is_idempotent_per_consumer_run(self):
        self.db.upsert_repository(repo(8, "old/existing"))
        client = Client(lookups={"new/workflow": repo(9, "new/workflow")})
        for _ in range(2):
            run_discovery(self.config, client, self.db, {}, "real-run",
                          capability_root=self.root, consumer_bindings=self.bindings)
        self.assertEqual(len(self.db.list_capability_invocations()), 1)

    def test_readiness_is_separate_from_activation_and_second_pilot_skips_available(self):
        classifications = {"impl:example/skill-index": {
            "category": "READY_WITH_EXISTING_ADAPTER", "blocker": "Already active and awaiting material use"}}
        result = audit_current_library(self.db, classifications)
        self.assertEqual(result["audited"], 1)
        self.assertEqual(result["unclassified"], [])
        self.assertEqual(second_pilot_candidates(self.db), [])
        self.assertEqual(self.db.get_activation(7)["activation_state"], "TRIAL_ENABLED")
        with self.db._connect() as connection:
            readiness = connection.execute("SELECT category FROM activation_readiness").fetchone()[0]
        self.assertEqual(readiness, "READY_WITH_EXISTING_ADAPTER")

    def test_readiness_reports_unclassified_instead_of_guessing(self):
        result = audit_current_library(self.db, {})
        self.assertEqual(result["audited"], 0)
        self.assertEqual(result["unclassified"], ["impl:example/skill-index"])

    def test_dashboard_projects_usage_health_and_readiness(self):
        self.db.upsert_repository(repo(8, "old/existing"))
        audit_current_library(self.db, {"impl:example/skill-index": {
            "category": "READY_WITH_EXISTING_ADAPTER", "blocker": "Awaiting a real consumer"}})
        client = Client(lookups={"new/workflow": repo(9, "new/workflow")})
        run_discovery(self.config, client, self.db, {}, "real-run",
                      capability_root=self.root, consumer_bindings=self.bindings)
        model = DashboardReadModel(self.root)
        connection = model._connection()
        try:
            card = model._source_intelligence(connection, 7)
        finally:
            connection.close()
        self.assertEqual(card["activation_readiness"]["category"], "READY_WITH_EXISTING_ADAPTER")
        self.assertEqual(card["capability_usage"]["consumer"], "RADAR_DISCOVERY")
        self.assertEqual(card["capability_usage"]["health"]["consecutive_failures"], 0)
        self.assertTrue(any(event["type"] == "capability_invocation" for event in model.activity()))


if __name__ == "__main__":
    unittest.main()
