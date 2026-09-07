import tempfile
import unittest
from pathlib import Path

from pti.activation_policy import (
    ACTIVATION_STATES,
    EVIDENCE_MATURITY,
    TIER_1,
    TIER_4,
    classify_activation_tier,
)
from pti.storage import Database


class ActivationPolicyTests(unittest.TestCase):
    def test_sensitive_trading_capability_is_always_tier_four(self):
        self.assertEqual(classify_activation_tier("TOOL", "TRADING", "TradingAgents"), TIER_4)

    def test_declarative_skill_can_be_classified_as_tier_one(self):
        self.assertEqual(classify_activation_tier("TOOL", "AI_AGENT", "archify"), TIER_1)

    def test_activation_record_is_sqlite_authoritative_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            record = {
                "github_repository_id": 1211139949,
                "activation_tier": TIER_1,
                "activation_state": "QUARANTINED",
                "evidence_maturity": EVIDENCE_MATURITY["REVIEWED"],
                "pinned_version": "abc123",
                "static_analysis_status": "PASS",
                "isolated_test_status": "NOT_RUN",
                "trial_status": "NOT_ENABLED",
                "rollback_status": "READY",
                "notes": "controlled pilot",
            }
            db.upsert_activation(record)
            db.upsert_activation({**record, "activation_state": "STATIC_ANALYSIS_PASS"})
            saved = db.get_activation(record["github_repository_id"])
            self.assertEqual(saved["activation_state"], "STATIC_ANALYSIS_PASS")
            self.assertEqual(saved["pinned_version"], "abc123")
            self.assertIn("STATIC_ANALYSIS_PASS", ACTIVATION_STATES)


if __name__ == "__main__":
    unittest.main()
