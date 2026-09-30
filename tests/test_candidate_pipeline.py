import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pti.cli import run_once
from pti.discovery import DiscoveryRun
from pti.models import RepositoryRecord
from pti.policy import Candidate, decide_candidate, score_candidate
from pti.reporting import write_chancellor_pending
from pti.storage import Database


def evaluation(repository_id=7, source="GITHUB_RADAR", stars=100, readme="# Agent workflow\nDocumented capabilities"):
    item = decide_candidate(score_candidate(Candidate(
        f"example/project-{repository_id}", "Agent workflow architecture", ["AI_AGENT"],
        stars, 0, 4, 4, 1, readme, f"https://github.com/example/project-{repository_id}", repository_id), {}))
    item.review_reason = "FIRST_REVIEW"
    item.semantic_review = {"review_provider": "LOCAL_EVIDENCE_RUBRIC", "ACTION": "USER_REVIEW_RECOMMENDED"}
    item.source_provenance = [{"source_type": source, "source_id": source, "scan_id": "scan-a"}]
    item.repository_evidence = {"readme": readme, "tree_paths": ["README.md"]}
    return item


class CandidatePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = Database(self.root / "state/intelligence.db")
        self.db.initialize()

    def persist(self, item, run_id="scan-a"):
        from pti.candidate_pipeline import persist_candidate
        self.db.upsert_repository(RepositoryRecord(item.candidate.github_repository_id,
            item.candidate.name, item.candidate.url, description=item.candidate.description))
        return persist_candidate(self.db, item, run_id)

    def test_stage_b_input_is_not_truncated_to_display_top_five(self):
        items = [evaluation(i, stars=10000) for i in range(1, 7)]
        for item in items[:5]:
            item.semantic_review = {}
        config = self.root / "config"
        config.mkdir()
        (config / "discovery.json").write_text("{}", encoding="utf-8")
        (config / "profile.json").write_text("{}", encoding="utf-8")
        with patch("pti.cli.run_discovery", return_value=DiscoveryRun(decisions=items)):
            run_once(self.root, config / "discovery.json", config / "profile.json")
        packets = list((self.root / "chancellor_pending").glob("*.json"))
        self.assertEqual(len(packets), 1)
        self.assertEqual(json.loads(packets[0].read_text(encoding="utf-8"))["repository_identity"]["github_repository_id"], 6)

    def test_native_and_capability_sources_have_same_admission(self):
        from pti.candidate_pipeline import candidate_admission
        self.assertTrue(candidate_admission(evaluation())["admitted"])
        self.assertTrue(candidate_admission(evaluation(source="CAPABILITY"))["admitted"])

    def test_intent_mismatch_missing_readme_low_quality_are_rejected(self):
        from pti.candidate_pipeline import candidate_admission
        for change, reason in (("intent", "INTENT_MISMATCH"), ("readme", "MISSING_README"),
                               ("quality", "BELOW_QUALITY_THRESHOLD")):
            item = evaluation()
            if change == "intent":
                item.intent_relevant = False
            elif change == "readme":
                item.candidate.readme = ""
                item.repository_evidence = {}
            else:
                item.total = 10
            self.assertIn(reason, candidate_admission(item)["reasons"])

    def test_identity_must_match_canonical_url(self):
        from pti.candidate_pipeline import candidate_admission
        item = evaluation()
        item.candidate.url = "https://github.com/other/repository"
        self.assertFalse(candidate_admission(item)["admitted"])

    def test_same_identity_multiple_sources_gets_one_bounded_packet(self):
        first = evaluation()
        first.candidate.readme = "README evidence " * 800
        second = evaluation(source="CAPABILITY")
        self.persist(first)
        self.persist(second)
        paths = write_chancellor_pending(self.root, [first, second], "scan-a")
        self.assertEqual(len(paths), 1)
        payload = json.loads(paths[0].read_text(encoding="utf-8"))
        self.assertEqual(len(payload["source_provenance"]), 2)
        self.assertIn("repository_evidence", payload)
        self.assertIn("capability_hypotheses", payload)
        self.assertIn("local_capability_profile", payload)
        self.assertLessEqual(len(payload["repository_evidence"]["readme"]), 6000)

    def test_repeat_scan_reuses_packet_instead_of_creating_duplicate(self):
        item = evaluation()
        self.persist(item)
        first = write_chancellor_pending(self.root, [item], "scan-a")
        second = write_chancellor_pending(self.root, [item], "scan-b")
        self.assertEqual([p.name for p in second], [p.name for p in first])
        self.assertEqual(len(list((self.root / "chancellor_pending").glob("*.json"))), 1)

    def test_completed_packet_and_current_final_decision_are_not_requeued(self):
        item = evaluation()
        self.persist(item)
        self.db.record_chancellor_decision(7, {"ACTION": "WATCH", "BEST_ROUTE": "AI_AGENT"}, "done.json", "scan-a")
        self.assertEqual(write_chancellor_pending(self.root, [item], "scan-b"), [])

    def test_repair_is_dry_run_first_bounded_and_idempotent(self):
        from pti.candidate_pipeline import repair_stranded_candidates
        self.persist(evaluation())
        self.persist(evaluation(8))
        name = "example/project-7"
        dry = repair_stranded_candidates(self.root, name)
        self.assertEqual(dry["status"], "REPAIR_READY")
        self.assertFalse((self.root / "chancellor_pending").exists())
        result = repair_stranded_candidates(self.root, name, dry_run=False)
        again = repair_stranded_candidates(self.root, name, dry_run=False)
        self.assertEqual(result["status"], "RESUMED")
        self.assertEqual(again["status"], "ALREADY_PENDING")
        with self.db._connect() as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM candidate_observations").fetchone()[0], 0)
        self.assertEqual(len(list((self.root / "chancellor_pending").glob("*.json"))), 1)

    def test_diversity_is_symmetric_and_never_overrides_single_slot_rank(self):
        from pti.review_queue import select_source_diverse
        high = evaluation(1, "NATIVE", stars=10000)
        low = evaluation(2, "CAPABILITY", stars=1000)
        other = evaluation(3, "NATIVE", stars=10000)
        key = lambda item: (-item.total, -item.candidate.stars, item.candidate.name)
        self.assertEqual(select_source_diverse([low, high, other], 1, key), [high])
        self.assertEqual({x.candidate.github_repository_id for x in select_source_diverse([high, other, low], 2, key)}, {1, 2})
        low.candidate.security_risk = 4
        self.assertEqual(select_source_diverse([high, other, low], 2, key), [high, other])

    def test_health_detects_screened_candidate_without_packet(self):
        from pti.candidate_pipeline import stalled_candidates
        self.persist(evaluation())
        with self.db._connect() as connection:
            connection.execute("UPDATE canonical_candidates SET screened_at='2000-01-01T00:00:00Z'")
        self.assertEqual(len(stalled_candidates(self.root)), 1)
        write_chancellor_pending(self.root, [evaluation()], "scan-a")
        self.assertEqual(stalled_candidates(self.root), [])

    def test_pending_card_and_activity_explain_local_and_final_review(self):
        from pti.dashboard_read_model import DashboardReadModel, _parse_time
        self.assertEqual(_parse_time("2026-09-30 09:22:08"), "2026-09-30T09:22:08Z")
        self.persist(evaluation(source="CAPABILITY"))
        write_chancellor_pending(self.root, [evaluation(source="CAPABILITY")], "scan-a")
        model = DashboardReadModel(self.root)
        card = next(x for x in model.capabilities() if x["repository"] == "example/project-7")
        self.assertEqual(card["candidate_pipeline"]["stage"], "WAITING_CHANCELLOR")
        self.assertEqual(card["candidate_pipeline"]["stage_label"], "等待 Chancellor 最终评审")
        self.assertTrue(any(x["type"] == "candidate_pipeline" for x in model.activity()))

    def test_stage_b_projection_and_terminal_decisions_never_enqueue(self):
        from pti.candidate_pipeline import project_final_decision
        from pti.activation_runtime import postprocess_semantic_decision
        for repository_id, action in enumerate(("WATCH", "REFERENCE_ONLY", "IGNORE", "ARCHIVE", "USER_REVIEW_RECOMMENDED"), 30):
            item = evaluation(repository_id)
            self.persist(item)
            decision = {"ACTION": action, "BEST_ROUTE": "AI_AGENT", "CAPABILITY_DELTA": "Potential workflow overlap"}
            self.db.record_chancellor_decision(repository_id, decision, "final.json", "scan-a")
            projection = project_final_decision(self.db, repository_id, decision, {})
            result = postprocess_semantic_decision(self.db, repository_id, decision, {})
            self.assertEqual(projection["implementation_id"], f"impl:example/project-{repository_id}")
            self.assertNotEqual(result["status"], "ACTIVATION_QUEUED")
        self.assertEqual(self.db.list_activation_queue(), [])

    def test_no_delta_and_os_sandbox_blockers_are_propagated(self):
        from pti.candidate_pipeline import project_final_decision
        from pti.activation_runtime import postprocess_semantic_decision
        for repository_id, duplication, expected in ((40, "NO_MEANINGFUL_DELTA", "NO_MEANINGFUL_DELTA"), (41, "Some overlap", "REQUIRES_OS_SANDBOX")):
            self.persist(evaluation(repository_id))
            decision = {"ACTION": "CANDIDATE_FOR_QUARANTINE", "BEST_ROUTE": "AI_AGENT", "DUPLICATION": duplication}
            project_final_decision(self.db, repository_id, decision, {})
            result = postprocess_semantic_decision(self.db, repository_id, decision, {})
            self.assertEqual(result["reason"], expected)
        self.assertEqual(self.db.list_activation_queue(), [])

    def test_existing_safe_adapter_uses_same_activation_queue(self):
        from pti.candidate_pipeline import project_final_decision
        from pti.activation_runtime import postprocess_semantic_decision
        from pti.capability_intelligence import CapabilityStore
        self.persist(evaluation(42))
        store = CapabilityStore(self.db.path)
        store.upsert_capability("SKILL_ECOSYSTEM_DISCOVERY", "Skill index", "Read-only index")
        packet = {"capability_hypotheses": [{"capability_id": "SKILL_ECOSYSTEM_DISCOVERY"}]}
        decision = {"ACTION": "CANDIDATE_FOR_QUARANTINE", "BEST_ROUTE": "AI_AGENT", "WHAT_IS_IT": "Read-only skill catalog"}
        project_final_decision(self.db, 42, decision, packet)
        result = postprocess_semantic_decision(self.db, 42, decision, packet)
        self.assertEqual(result["status"], "ACTIVATION_QUEUED")
        self.assertEqual(len(self.db.list_activation_queue("PENDING")), 1)
        self.assertEqual(self.db.list_activation_queue()[0]["attempt_count"], 0)

    def test_authorized_rereview_can_follow_a_completed_packet(self):
        item = evaluation()
        self.persist(item)
        first = write_chancellor_pending(self.root, [item], "scan-a")[0]
        first.rename(first.with_name(first.stem + ".processed.json"))
        self.db.record_chancellor_decision(7, {"ACTION": "WATCH", "BEST_ROUTE": "AI_AGENT"}, first.name, "scan-a")
        item.review_reason = "WATCH_DUE"
        second = write_chancellor_pending(self.root, [item], "scan-b")
        self.assertEqual(len(second), 1)
        self.assertNotEqual(first.name, second[0].name)

    def test_shared_stage_b_persists_final_and_projects_only_target_repository(self):
        from types import SimpleNamespace
        from pti.stage_b import run_stage_b
        from pti.chancellor_contract import REQUIRED_FIELDS
        for repository_id in (50, 51):
            self.persist(evaluation(repository_id, "CAPABILITY" if repository_id == 50 else "GITHUB_RADAR"))
        write_chancellor_pending(self.root, [evaluation(50), evaluation(51)], "scan-a")
        decision = {field: "Bounded test evidence" for field in REQUIRED_FIELDS}
        decision.update(ACTION="WATCH", BEST_ROUTE="AI_AGENT")
        (self.root / "config").mkdir(exist_ok=True)
        (self.root / "config/stage_b.json").write_text('{"model":"test-supported-model"}', encoding="utf-8")
        import subprocess
        real_run = subprocess.run
        def reviewer(arguments, **kwargs):
            if "--output-last-message" not in arguments:
                return real_run(arguments, **kwargs)
            output = Path(arguments[arguments.index("--output-last-message") + 1])
            output.write_text(json.dumps(decision), encoding="utf-8")
            self.assertIn("--sandbox", arguments)
            self.assertIn("read-only", arguments)
            self.assertEqual(arguments[arguments.index("--model") + 1], "test-supported-model")
            self.assertIn("source_provenance", kwargs["input"])
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        with patch("pti.stage_b.subprocess.run", side_effect=reviewer):
            result = run_stage_b(self.root, limit=1, repository="example/project-50")
        self.assertEqual(result["processed"], 1)
        self.assertTrue(self.db.has_current_semantic_decision(50))
        self.assertFalse(self.db.has_current_semantic_decision(51))
        self.assertEqual(self.db.list_activation_queue(), [])
        with self.db._connect() as connection:
            self.assertEqual(connection.execute("SELECT stage FROM canonical_candidates WHERE github_repository_id=50").fetchone()[0], "CHANCELLOR_DECIDED")
            self.assertEqual(connection.execute("SELECT lifecycle_state FROM capability_implementations WHERE implementation_id='impl:example/project-50'").fetchone()[0], "WATCH")

    def test_provenance_merges_into_existing_packet_without_second_packet(self):
        self.persist(evaluation())
        first = write_chancellor_pending(self.root, [evaluation()], "scan-a")
        second = write_chancellor_pending(self.root, [evaluation(source="CAPABILITY")], "scan-b")
        self.assertEqual(first, second)
        self.assertEqual(len(json.loads(second[0].read_text(encoding="utf-8"))["source_provenance"]), 2)

    def test_human_gate_has_real_dashboard_action_and_no_queue(self):
        from pti.candidate_pipeline import project_final_decision
        from pti.activation_runtime import postprocess_semantic_decision
        from pti.dashboard_read_model import DashboardReadModel
        self.persist(evaluation(52))
        decision = {"ACTION": "USER_REVIEW_RECOMMENDED", "BEST_ROUTE": "AI_AGENT"}
        self.db.record_chancellor_decision(52, decision, "final.json", "scan-a")
        project_final_decision(self.db, 52, decision, {})
        postprocess_semantic_decision(self.db, 52, decision, {})
        card = next(x for x in DashboardReadModel(self.root).capabilities() if x["repository"] == "example/project-52")
        self.assertTrue(card["human_action_required"])
        self.assertEqual(self.db.list_activation_queue(), [])

    def test_credential_risk_is_human_gated_before_adapter_selection(self):
        from pti.candidate_pipeline import project_final_decision
        from pti.activation_runtime import postprocess_semantic_decision
        self.persist(evaluation(53))
        decision = {"ACTION": "CANDIDATE_FOR_QUARANTINE", "BEST_ROUTE": "AI_AGENT", "WHAT_IS_IT": "Tool requiring API token"}
        project_final_decision(self.db, 53, decision, {})
        result = postprocess_semantic_decision(self.db, 53, decision, {})
        self.assertEqual(result["reason"], "HUMAN_GATE")
        self.assertEqual(self.db.get_activation(53)["activation_state"], "BLOCKED_HUMAN")
        self.assertEqual(self.db.list_activation_queue(), [])


if __name__ == "__main__":
    unittest.main()
