import json
import tempfile
import unittest
from pathlib import Path

from pti.chancellor import LocalSemanticChancellor, build_review_packet
from pti.github_api import GitHubClient, RequestBudget, TransportResponse
from pti.models import RepositoryRecord
from pti.storage import Database


class FakeTransport:
    def __init__(self, responses):
        self.responses = iter(responses)

    def get(self, path, params):
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return value


class Phase15Tests(unittest.TestCase):
    def test_standard_enrichment_collects_bounded_readme_release_commit_and_tree(self):
        transport = FakeTransport([
            TransportResponse({"content": "IyBOb3RlcyBmb3IgdGhlIHByb2plY3Q=", "encoding": "base64"}),
            TransportResponse({"tag_name": "v2.0.0", "published_at": "2026-08-20T00:00:00Z", "name": "release"}),
            TransportResponse([{"sha": "abc123", "commit": {"committer": {"date": "2026-08-21T00:00:00Z"}}}]),
            TransportResponse({"tree": [{"path": "README.md", "type": "blob"}, {"path": "src", "type": "tree"}]}),
        ])
        client = GitHubClient(transport, RequestBudget(4))
        evidence = client.enrich_repository("a", "b", level="STANDARD", text_limit=1000)
        self.assertEqual(evidence.readme, "# Notes for the project")
        self.assertEqual(evidence.release["tag_name"], "v2.0.0")
        self.assertEqual(evidence.latest_commit["sha"], "abc123")
        self.assertEqual(evidence.tree_paths, ["README.md", "src"])
        self.assertEqual(client.budget.used, 4)

    def test_partial_enrichment_does_not_discard_successful_evidence(self):
        from pti.github_api import HttpFailure
        client = GitHubClient(FakeTransport([
            TransportResponse({"content": "IyBPSw==", "encoding": "base64"}),
            HttpFailure(403, "rate limit token=secret"),
        ]), RequestBudget(2))
        evidence = client.enrich_repository("a", "b", level="STANDARD")
        self.assertEqual(evidence.readme, "# OK")
        self.assertTrue(evidence.failures)
        self.assertNotIn("secret", json.dumps(evidence.to_dict()))

    def test_feedback_schema_is_explicit_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.upsert_repository(RepositoryRecord(1, "a/b", "https://github.com/a/b"))
            db.record_feedback(1, "ALREADY_HAVE", "overlaps local capability")
            self.assertEqual(db.get_feedback(1)[0]["label"], "ALREADY_HAVE")

    def test_semantic_packet_is_separate_from_deterministic_score_and_prompt_is_untrusted(self):
        candidate = {"name": "a/b", "description": "context memory", "domains": ["AI_EXPERIENCE"], "stars": 20}
        packet = build_review_packet(candidate, {"score_total": 12}, {"AI_EXPERIENCE": "existing memory"}, [])
        result = LocalSemanticChancellor().review(packet)
        self.assertEqual(result["review_type"], "SEMANTIC_CHANCELLOR_REVIEW")
        self.assertIn("WHAT_IS_IT", result)
        self.assertEqual(result["system_instruction_effect"], "IGNORED_AS_UNTRUSTED_INPUT")
        self.assertIn("CAPABILITY_DELTA", result)

    def test_discovered_code_execution_is_not_an_available_client_operation(self):
        self.assertFalse(hasattr(GitHubClient, "clone_repository"))
        self.assertFalse(hasattr(GitHubClient, "execute_repository"))


if __name__ == "__main__":
    unittest.main()
