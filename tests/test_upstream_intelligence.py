import tempfile
import unittest
from pathlib import Path

from pti.capability_intelligence import CapabilityStore
from pti.upstream_intelligence import (
    Fingerprint,
    GitHubFingerprintProvider,
    MonitorFailure,
    check_upstream,
    classify_change,
)
from pti.github_api import ApiFailure, ApiResult, RequestBudget


class StaticProvider:
    def __init__(self, fingerprint=None, failure=None):
        self.fingerprint = fingerprint
        self.failure = failure
        self.calls = []
        self.request_count = 0

    def fetch(self, source, previous):
        self.calls.append(source["source_id"])
        if self.failure:
            raise self.failure
        self.request_count += 1
        return self.fingerprint


class UpstreamIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "intelligence.db"
        self.store = CapabilityStore(self.path)
        self.store.upsert_source(
            "github:1", "GITHUB_REPOSITORY", "owner/archon",
            "https://github.com/owner/archon", 1,
        )
        self.store.upsert_implementation("impl:archon", "github:1", "archon", "TOOL", "FAILED_WITH_EXPLAINED_REASON")
        self.store.set_personal_state("IMPLEMENTATION", "impl:archon", "VALIDATION_FAILED", "isolation not established")
        self.base = Fingerprint(
            head_sha="a" * 40,
            release_tag="v1.0.0",
            release_published_at="2026-09-20T00:00:00Z",
            readme_sha="b" * 40,
            repository_updated_at="2026-09-20T00:00:00Z",
            repository_pushed_at="2026-09-20T00:00:00Z",
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_first_run_captures_baseline_without_review_job(self):
        result = check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:00:00Z", force=True)
        freshness = self.store.get_source_freshness("github:1")
        self.assertEqual(result["baseline_captured"], 1)
        self.assertEqual(result["changes_detected"], 0)
        self.assertEqual(self.store.list_delta_reviews(), [])
        self.assertEqual(freshness["last_check_status"], "BASELINE_CAPTURED")
        self.assertEqual(freshness["review_freshness"], "UNKNOWN")
        self.assertIsNone(freshness["reviewed_head_sha"])
        self.assertIsNone(freshness["last_review"])

    def test_second_unchanged_run_reports_no_change(self):
        check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:00:00Z", force=True)
        result = check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:01:00Z", force=True)
        self.assertEqual(result["no_change"], 1)
        self.assertEqual(self.store.get_source_freshness("github:1")["last_check_status"], "NO_CHANGE")
        self.assertEqual(self.store.list_delta_reviews(), [])

    def test_release_change_queues_one_review_and_preserves_old_review_version(self):
        check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:00:00Z", force=True)
        changed = Fingerprint(
            head_sha="c" * 40,
            release_tag="v1.1.0",
            release_published_at="2026-09-29T00:00:00Z",
            readme_sha="d" * 40,
            repository_updated_at="2026-09-29T00:00:00Z",
            repository_pushed_at="2026-09-29T00:00:00Z",
            release_notes="Adds isolated execution and credential boundary controls",
        )
        first = check_upstream(self.store, StaticProvider(changed), now="2026-09-29T01:00:00Z", force=True)
        second = check_upstream(self.store, StaticProvider(changed), now="2026-09-29T01:01:00Z", force=True)
        freshness = self.store.get_source_freshness("github:1")
        self.assertEqual(first["changes_detected"], 1)
        self.assertEqual(first["reviews_queued"], 1)
        self.assertEqual(second["reviews_queued"], 0)
        self.assertEqual(len(self.store.list_delta_reviews()), 1)
        self.assertIsNone(freshness["reviewed_release_tag"])
        self.assertEqual(freshness["current_release_tag"], "v1.1.0")
        self.assertEqual(freshness["upstream_freshness"], "CHANGED")
        self.assertEqual(freshness["review_freshness"], "STALE")
        self.assertEqual(self.store.list_delta_reviews()[0]["suggested_outcome"], "REVALIDATION_REQUIRED")
        self.assertIsNone(self.store.list_delta_reviews()[0]["review_outcome"])

    def test_head_only_typo_does_not_queue_deep_review(self):
        check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:00:00Z", force=True)
        changed = Fingerprint(
            head_sha="c" * 40,
            release_tag="v1.0.0",
            release_published_at="2026-09-20T00:00:00Z",
            readme_sha="b" * 40,
            repository_updated_at="2026-09-29T00:00:00Z",
            repository_pushed_at="2026-09-29T00:00:00Z",
            commit_message="docs: fix typo",
        )
        result = check_upstream(self.store, StaticProvider(changed), now="2026-09-29T01:00:00Z", force=True)
        self.assertEqual(result["changes_detected"], 1)
        self.assertEqual(result["reviews_queued"], 0)
        self.assertEqual(self.store.list_delta_reviews(), [])
        self.assertEqual(self.store.get_source_freshness("github:1")["review_freshness"], "UNKNOWN")

    def test_failure_is_classified_and_does_not_overwrite_baseline(self):
        check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:00:00Z", force=True)
        for error_class in ("NETWORK", "RATE_LIMIT", "SYSTEM"):
            with self.subTest(error_class=error_class):
                result = check_upstream(
                    self.store,
                    StaticProvider(failure=MonitorFailure(error_class, "test failure")),
                    now="2026-09-29T01:00:00Z",
                    force=True,
                )
                self.assertEqual(result["failures"], 1)
                freshness = self.store.get_source_freshness("github:1")
                self.assertEqual(freshness["current_head_sha"], self.base.head_sha)
                self.assertEqual(freshness["last_error_class"], error_class)

    def test_initial_failure_recovers_to_persisted_baseline(self):
        failed = check_upstream(
            self.store,
            StaticProvider(failure=MonitorFailure("NETWORK", "offline")),
            now="2026-09-29T00:00:00Z",
        )
        self.assertEqual(failed["failures"], 1)
        recovered = check_upstream(
            self.store, StaticProvider(self.base), now="2026-09-29T00:01:00Z"
        )
        freshness = self.store.get_source_freshness("github:1")
        self.assertEqual(recovered["baseline_captured"], 1)
        self.assertEqual(freshness["current_head_sha"], self.base.head_sha)
        self.assertEqual(freshness["last_check_status"], "BASELINE_CAPTURED")
        self.assertIsNone(freshness["last_error_class"])

    def test_unchanged_source_is_skipped_until_state_based_cadence(self):
        check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:00:00Z", force=True)
        provider = StaticProvider(self.base)
        result = check_upstream(self.store, provider, now="2026-09-30T00:00:00Z")
        self.assertEqual(result["skipped_not_due"], 1)
        self.assertEqual(provider.calls, [])

    def test_change_classification_requires_relevant_failed_project_evidence(self):
        only_version = Fingerprint(
            head_sha="c" * 40,
            release_tag="v1.1.0",
            release_published_at="2026-09-29T00:00:00Z",
            readme_sha="b" * 40,
            repository_updated_at="2026-09-29T00:00:00Z",
            repository_pushed_at="2026-09-29T00:00:00Z",
        )
        outcome = classify_change(self.base, only_version, "VALIDATION_FAILED")
        self.assertNotEqual(outcome["review_outcome"], "REVALIDATION_REQUIRED")
        self.assertTrue(outcome["queue_review"])

    def test_unchanged_release_notes_cannot_reopen_failed_project(self):
        head_only = Fingerprint(
            head_sha="c" * 40,
            release_tag=self.base.release_tag,
            release_published_at=self.base.release_published_at,
            readme_sha=self.base.readme_sha,
            repository_updated_at="2026-09-29T00:00:00Z",
            repository_pushed_at="2026-09-29T00:00:00Z",
            commit_message="docs: fix typo",
            release_notes="Old release mentions credential isolation",
        )
        outcome = classify_change(self.base, head_only, "VALIDATION_FAILED")
        self.assertFalse(outcome["queue_review"])
        self.assertEqual(outcome["review_outcome"], "NO_RELEVANT_CHANGE")

    def test_completed_delta_review_moves_reviewed_version_and_closes_queue(self):
        check_upstream(self.store, StaticProvider(self.base), now="2026-09-29T00:00:00Z", force=True)
        changed = Fingerprint(
            head_sha="c" * 40,
            release_tag="v1.1.0",
            release_published_at="2026-09-29T00:00:00Z",
            readme_sha="b" * 40,
            repository_updated_at="2026-09-29T00:00:00Z",
            repository_pushed_at="2026-09-29T00:00:00Z",
            release_notes="Adds isolated execution controls",
        )
        check_upstream(self.store, StaticProvider(changed), now="2026-09-29T01:00:00Z", force=True)
        review = self.store.list_delta_reviews("PENDING")[0]
        with self.assertRaises(ValueError):
            self.store.complete_delta_review(review["id"], "REVALIDATION_REQUIRED", "", "2026-09-29T02:00:00Z")
        self.store.complete_delta_review(
            review["id"], "REVALIDATION_REQUIRED",
            "Release adds isolation controls, but rollback and credential boundaries still need an isolated test.",
            "2026-09-29T02:00:00Z",
        )
        freshness = self.store.get_source_freshness("github:1")
        self.assertEqual(self.store.list_delta_reviews("PENDING"), [])
        self.assertEqual(freshness["reviewed_release_tag"], "v1.1.0")
        self.assertEqual(freshness["review_freshness"], "CURRENT")
        self.assertEqual(freshness["last_review"], "2026-09-29T02:00:00Z")

    def test_github_provider_uses_cheap_metadata_when_unchanged(self):
        class Client:
            budget = RequestBudget(10)

            def __init__(self):
                self.calls = []

            def get_repository(self, owner, repo):
                self.calls.append("repository")
                self.budget.consume()
                return ApiResult(raw={
                    "id": 1,
                    "updated_at": "2026-09-20T00:00:00Z",
                    "pushed_at": "2026-09-20T00:00:00Z",
                })

        client = Client()
        provider = GitHubFingerprintProvider(client=client)
        current = provider.fetch(self.store.list_monitor_sources()[0], self.base)
        self.assertEqual(current, self.base)
        self.assertEqual(client.calls, ["repository"])

    def test_github_rate_limit_is_reported_without_mutating_fingerprint(self):
        class Client:
            budget = RequestBudget(10)

            def get_repository(self, owner, repo):
                self.budget.consume()
                return ApiResult(failure=ApiFailure("HTTP_403", "rate limit"))

        provider = GitHubFingerprintProvider(client=Client())
        result = check_upstream(self.store, provider, now="2026-09-29T01:00:00Z", force=True)
        self.assertEqual(result["failure_class"], "RATE_LIMIT")
        self.assertEqual(self.store.get_source_freshness("github:1")["last_error_class"], "RATE_LIMIT")

    def test_existing_radar_schedule_launches_upstream_check_separately(self):
        root = Path(__file__).resolve().parents[1]
        radar = (root / "run_scheduled_scan.ps1").read_text(encoding="utf-8")
        upstream = (root / "run_scheduled_upstream.ps1").read_text(encoding="utf-8")
        self.assertIn("run_scheduled_upstream.ps1", radar)
        self.assertIn("-WindowStyle Hidden", radar)
        self.assertIn("check-upstream", upstream)
        self.assertIn("upstream-check.error.log", upstream)
        self.assertNotIn("git pull", upstream.lower())


if __name__ == "__main__":
    unittest.main()
