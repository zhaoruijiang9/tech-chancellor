import unittest

from pti.human_library import project_human_library_item


def card(repository, state, action="REFERENCE_ONLY", **extra):
    return {
        "repository": repository,
        "activation_state": state,
        "semantic_action": action,
        "evidence_maturity": extra.pop("evidence_maturity", "REVIEWED"),
        "isolated_test_status": extra.pop("isolated_test_status", "NOT_RUN"),
        "trial_status": extra.pop("trial_status", "NOT_ENABLED"),
        "real_use_outcome": extra.pop("real_use_outcome", None),
        **extra,
    }


class HumanLibraryProjectionTests(unittest.TestCase):
    def test_real_use_evidence_is_a_used_capability(self):
        result = project_human_library_item(card(
            "tt-a1i/archify",
            "USED",
            action="CANDIDATE_FOR_QUARANTINE",
            evidence_maturity="USED",
            isolated_test_status="PASS",
            trial_status="ENABLED_CONTROLLED",
            real_use_outcome="USED_SUCCESSFULLY",
        ))
        self.assertEqual(result["human_category"], "USED")
        self.assertEqual(result["item_kind"], "CAPABILITY")
        self.assertFalse(result["human_action_required"])

    def test_distilled_reference_without_workflow_evidence_is_not_adopted(self):
        for repository in ("bmad-code-org/BMAD-METHOD", "github/spec-kit"):
            with self.subTest(repository=repository):
                result = project_human_library_item(card(repository, "ACTIVE_PATTERN"))
                self.assertEqual(result["human_category"], "WATCHLIST")
                self.assertEqual(result["item_kind"], "METHOD_SOURCE")

    def test_method_is_adopted_only_when_capability_model_proves_it(self):
        result = project_human_library_item(card(
            "bmad-code-org/BMAD-METHOD",
            "ACTIVE_PATTERN",
            method_adoption_state="ADOPTED",
        ))
        self.assertEqual(result["human_category"], "ADOPTED_METHOD")
        self.assertEqual(result["item_kind"], "METHOD_SOURCE")

    def test_reference_only_item_is_not_mislabeled_as_adopted_method(self):
        result = project_human_library_item(card("cased/kit", "ACTIVE_PATTERN"))
        self.assertEqual(result["human_category"], "WATCHLIST")
        self.assertEqual(result["item_kind"], "KNOWLEDGE_REFERENCE")

    def test_high_duplication_projects_are_not_adopted(self):
        for repository in ("FoundationAgents/MetaGPT", "langchain-ai/langchain"):
            with self.subTest(repository=repository):
                result = project_human_library_item(card(repository, "ACTIVE_PATTERN"))
                self.assertEqual(result["human_category"], "NOT_ADOPTED")
                self.assertEqual(result["item_kind"], "PROJECT")

    def test_prior_approval_moves_item_out_of_human_decision(self):
        result = project_human_library_item(
            card("nieledran/backtesting-engine", "BLOCKED_HUMAN", action="CANDIDATE_FOR_QUARANTINE"),
            latest_feedback={"label": "APPROVE_FOR_REVIEW", "created_at": "2026-09-28 14:11:56"},
            queue_records=[{"status": "BLOCKED_HUMAN", "attempt_count": 1}],
        )
        self.assertEqual(result["human_category"], "WAITING_VALIDATION")
        self.assertFalse(result["human_action_required"])
        self.assertEqual(result["processing_state"], "APPROVED_WAITING_VALIDATION")

    def test_processing_queue_is_the_only_active_validation_state(self):
        result = project_human_library_item(
            card("nieledran/backtesting-engine", "BLOCKED_HUMAN", action="CANDIDATE_FOR_QUARANTINE"),
            latest_feedback={"label": "APPROVE_FOR_REVIEW"},
            queue_records=[{"status": "PROCESSING", "attempt_count": 1}],
        )
        self.assertEqual(result["human_category"], "VALIDATING")
        self.assertEqual(result["processing_state"], "IN_PROGRESS")

    def test_unresolved_sensitive_candidate_still_needs_owner_decision(self):
        result = project_human_library_item(
            card("TauricResearch/TradingAgents", "BLOCKED_HUMAN"),
            queue_records=[{"status": "BLOCKED_HUMAN", "failure_class": "HUMAN_APPROVAL_REQUIRED"}],
        )
        self.assertEqual(result["human_category"], "HUMAN_DECISION")
        self.assertTrue(result["human_action_required"])

    def test_terminal_activation_attempt_is_validation_failed_not_installed(self):
        result = project_human_library_item(
            card("coleam00/archon", "FAILED_WITH_EXPLAINED_REASON", action="CANDIDATE_FOR_QUARANTINE"),
            queue_records=[{
                "status": "FAILED_TERMINAL",
                "attempt_count": 1,
                "failure_class": "SAFE_REPRODUCIBLE_ACTIVATION_NOT_AVAILABLE",
            }],
        )
        self.assertEqual(result["human_category"], "VALIDATION_FAILED")
        self.assertEqual(result["item_kind"], "CANDIDATE")
        self.assertFalse(result["installed"])
        self.assertFalse(result["runnable"])


if __name__ == "__main__":
    unittest.main()
