import json
import tempfile
import unittest
from pathlib import Path

from pti.activation_policy import evaluate_activation_policy, transition_activation
from pti.activation_runtime import process_activation_queue
from pti.storage import Database


class ActivationRuntimeTests(unittest.TestCase):
    def test_pending_queue_is_resolved_without_claiming_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.enqueue_activation(7, "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL", "QUARANTINED", "PINNED_VERSION_MISSING;ROLLBACK_UNCLEAR")
            results = process_activation_queue(db)
            self.assertEqual(results[0]["activation_state"], "FAILED_WITH_EXPLAINED_REASON")
            self.assertEqual(db.list_activation_queue("PENDING"), [])
            self.assertEqual(db.get_activation(7)["isolated_test_status"], "NOT_RUN")

    def test_low_risk_tier_two_policy_is_eligible_only_after_all_gates(self):
        capability = {
            "repository": "owner/tool",
            "activation_tier": "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL",
            "pinned_version": "abc123",
            "requires_credential": False,
            "requires_admin": False,
            "requires_service": False,
            "persistent_listener": False,
            "system_modification": False,
            "path_modification": False,
            "browser_extension": False,
            "rollback_available": True,
        }
        decision = evaluate_activation_policy(capability, {
            "static_analysis_pass": True,
            "isolated_test_pass": True,
            "capability_delta": True,
        })

        self.assertTrue(decision.eligible)
        self.assertIn("AUTO_ENABLE_LOW_RISK_TIER2_TRIAL", decision.automatic_actions_allowed)
        self.assertEqual(decision.max_activation_state, "TRIAL_ENABLED")
        self.assertIn("PINNED_VERSION_AVAILABLE", decision.reason_codes)

    def test_credential_or_service_hard_gates_tier_two(self):
        capability = {
            "repository": "owner/service",
            "activation_tier": "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL",
            "pinned_version": "abc123",
            "requires_credential": True,
            "requires_service": True,
            "rollback_available": True,
        }
        decision = evaluate_activation_policy(capability, {})

        self.assertFalse(decision.eligible)
        self.assertIn("CREDENTIAL_REQUIRED", decision.reason_codes)
        self.assertIn("SERVICE_REQUIRED", decision.reason_codes)
        self.assertEqual(decision.max_activation_state, "QUARANTINED")

    def test_activation_queue_is_idempotent_and_claimable(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.enqueue_activation(7, "TIER_1_DECLARATIVE_SKILL", "TRIAL_ENABLED", "static pass")
            db.enqueue_activation(7, "TIER_1_DECLARATIVE_SKILL", "TRIAL_ENABLED", "duplicate")
            pending = db.list_activation_queue("PENDING")
            self.assertEqual(len(pending), 1)
            claimed = db.claim_activation(pending[0]["id"])
            self.assertEqual(claimed["status"], "PROCESSING")
            db.complete_activation(claimed["id"], "SUCCEEDED")
            self.assertEqual(db.list_activation_queue("SUCCEEDED")[0]["attempt_count"], 1)

    def test_used_requires_real_use_evidence_and_trial_transition_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.upsert_activation({
                "github_repository_id": 7,
                "activation_tier": "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL",
                "activation_state": "ISOLATED_TEST_PASS",
                "evidence_maturity": "TESTED",
                "pinned_version": "abc123",
                "rollback_status": "READY",
            })
            transition_activation(db, 7, "TRIAL_ENABLED")
            with self.assertRaises(ValueError):
                transition_activation(db, 7, "USED")
            transition_activation(db, 7, "USED", real_use=True)
            self.assertEqual(db.get_activation(7)["evidence_maturity"], "USED")

    def test_real_use_record_requires_explicit_real_task_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.upsert_activation({
                "github_repository_id": 8,
                "activation_tier": "TIER_2_LOW_PRIVILEGE_LOCAL_TOOL",
                "activation_state": "TRIAL_ENABLED",
                "evidence_maturity": "TESTED",
                "pinned_version": "abc123",
                "rollback_status": "READY",
            })
            with self.assertRaises(ValueError):
                db.record_real_use(8, "demo", "architecture", "pass", "fixture", real_task_evidence=False)
            db.record_real_use(8, "demo", "architecture", "pass", "current task receipt", real_task_evidence=True)
            self.assertEqual(db.get_activation(8)["activation_state"], "USED")


if __name__ == "__main__":
    unittest.main()
