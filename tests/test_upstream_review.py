import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from pti.capability_intelligence import CapabilityStore
from pti.github_api import ApiResult
from pti.upstream_intelligence import Fingerprint, check_upstream
from pti.upstream_review import CodexDeltaReviewer, review_pending_deltas


class Provider:
    request_count = 1

    def __init__(self, fingerprint):
        self.fingerprint = fingerprint

    def fetch(self, source, previous):
        return self.fingerprint


class UpstreamReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "intelligence.db"
        self.store = CapabilityStore(self.path)
        self.store.upsert_source("github:1", "GITHUB_REPOSITORY", "owner/tool", "https://github.com/owner/tool", 1)
        self.store.upsert_implementation("impl:tool", "github:1", "Tool", "TOOL")
        self.store.set_personal_state("IMPLEMENTATION", "impl:tool", "VALIDATION_FAILED", "prior isolation blocker")
        base = Fingerprint("a" * 40, "v1", "2026-09-01T00:00:00Z", "b" * 40,
                           "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z")
        changed = Fingerprint("c" * 40, "v2", "2026-09-29T00:00:00Z", "d" * 40,
                              "2026-09-29T00:00:00Z", "2026-09-29T00:00:00Z",
                              release_notes="Adds worktree isolation, but rollback remains unknown")
        check_upstream(self.store, Provider(base), now="2026-09-29T00:00:00Z", force=True)
        check_upstream(self.store, Provider(changed), now="2026-09-29T01:00:00Z", force=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_review_records_bounded_evidence_and_does_not_change_activation(self):
        seen = []

        def reviewer(packet):
            seen.append(packet)
            return {"outcome": "REVALIDATION_REQUIRED", "evidence": "v2 adds worktree isolation; rollback is not verified."}

        result = review_pending_deltas(self.store, reviewer, now="2026-09-29T02:00:00Z")
        self.assertEqual(result["reviewed"], 1)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["change"]["old_release_tag"], "v1")
        self.assertIn("worktree isolation", seen[0]["change"]["summary"])
        review = self.store.list_delta_reviews()[0]
        self.assertEqual(review["status"], "REVIEWED")
        self.assertEqual(review["review_outcome"], "REVALIDATION_REQUIRED")
        self.assertEqual(self.store.get_source_freshness("github:1")["review_freshness"], "CURRENT")
        states = self.store.get_implementation("impl:tool")["personal_states"]
        self.assertEqual([row["state"] for row in states], ["VALIDATION_FAILED"])
        self.assertEqual(review_pending_deltas(self.store, reviewer)["reviewed"], 0)

    def test_insufficient_evidence_stays_pending(self):
        result = review_pending_deltas(self.store, lambda packet: {
            "outcome": "INSUFFICIENT_EVIDENCE", "evidence": "Release note does not establish rollback behavior."
        })
        self.assertEqual(result["reviewed"], 0)
        self.assertEqual(result["failed"], 1)
        review = self.store.list_delta_reviews()[0]
        self.assertEqual(review["status"], "PENDING")
        self.assertEqual(review["review_attempts"], 1)
        self.assertEqual(self.store.get_source_freshness("github:1")["review_freshness"], "STALE")

    def test_reviewer_error_does_not_erase_pending_change(self):
        def reviewer(packet):
            raise RuntimeError("unavailable")

        result = review_pending_deltas(self.store, reviewer)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(self.store.list_delta_reviews()[0]["status"], "PENDING")
        self.assertEqual(self.store.get_source_freshness("github:1")["review_freshness"], "STALE")

    def test_detected_change_is_not_an_automatic_upgrade(self):
        self.assertEqual(self.store.get_implementation("impl:tool")["lifecycle_state"], "OBSERVED")
        self.assertIsNone(self.store.list_delta_reviews()[0]["review_outcome"])

    def test_codex_reviewer_uses_read_only_ephemeral_delta_packet(self):
        reviewer = CodexDeltaReviewer(Path(__file__).resolve().parents[1])
        seen = {}

        def run(command, **kwargs):
            seen["command"] = command
            seen["prompt"] = kwargs["input"]
            Path(command[command.index("--output-last-message") + 1]).write_text(
                '{"outcome":"REVALIDATION_REQUIRED","evidence":"v2 claims isolation; local revalidation remains necessary."}',
                encoding="utf-8",
            )
            return CompletedProcess(command, 0)

        with patch.object(reviewer.client, "compare_commits", return_value=ApiResult(raw={
            "ahead_by": 1, "total_commits": 1,
            "commits": [{"commit": {"message": "fix: isolate worktree"}}],
            "files": [{"filename": "src/worktree.py"}],
        })), patch("pti.upstream_review.subprocess.run", side_effect=run):
            result = review_pending_deltas(self.store, reviewer)

        self.assertEqual(result["reviewed"], 1)
        self.assertIn("--sandbox", seen["command"])
        self.assertEqual(seen["command"][seen["command"].index("--sandbox") + 1], "read-only")
        self.assertIn("--ephemeral", seen["command"])
        self.assertIn("src/worktree.py", seen["prompt"])
        self.assertEqual(self.store.get_implementation("impl:tool")["lifecycle_state"], "OBSERVED")


if __name__ == "__main__":
    unittest.main()
