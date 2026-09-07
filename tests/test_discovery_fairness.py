import tempfile
import unittest
from pathlib import Path

from pti.discovery import run_discovery
from pti.github_api import ApiResult
from pti.models import RepositoryRecord
from pti.storage import Database


def repo(repository_id: int, name: str, stars: int = 100) -> RepositoryRecord:
    return RepositoryRecord(
        github_repository_id=repository_id,
        canonical_owner_repo=name,
        url=f"https://github.com/{name}",
        stars=stars,
        description=f"Useful capability {name}",
    )


class QueryClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def search_repositories(self, query, page=1, per_page=10):
        self.calls.append(query)
        return ApiResult(items=list(self.responses.get(query, [])))


class DiscoveryFairnessTests(unittest.TestCase):
    def run_case(self, responses, queries, total_cap=20):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "state.db")
            db.initialize()
            db.start_scan_run("fairness-run", "2026-09-06T00:00:00Z")
            client = QueryClient(responses)
            result = run_discovery(
                {
                    "query_groups": [{"domain": "AI_AGENT", "queries": queries}],
                    "per_query_cap": 5,
                    "total_candidate_cap": total_cap,
                    "enrichment_candidate_cap": 0,
                },
                client,
                db,
                {},
                run_id="fairness-run",
            )
            with db._connect() as connection:
                observations = connection.execute(
                    "SELECT source_query FROM candidate_observations WHERE scan_run_id = ? ORDER BY source_query",
                    ("fairness-run",),
                ).fetchall()
            return result, client, [row[0] for row in observations]

    def test_all_configured_queries_receive_first_pass_before_candidate_cap(self):
        queries = [f"query-{index}" for index in range(8)]
        responses = {query: [repo(index + 1, f"owner/repo-{index}")] for index, query in enumerate(queries)}
        result, client, _ = self.run_case(responses, queries, total_cap=3)

        self.assertEqual(client.calls, queries)
        self.assertEqual(result.request_count, 8)
        self.assertEqual(len(result.decisions), 3)

    def test_duplicate_identity_is_counted_once_but_query_observations_are_preserved(self):
        shared = repo(1, "owner/shared", stars=1000)
        result, client, observations = self.run_case(
            {"first": [shared], "second": [shared], "third": [repo(2, "owner/other")]},
            ["first", "second", "third"],
        )

        self.assertEqual(client.calls, ["first", "second", "third"])
        self.assertEqual(len(result.decisions), 2)
        self.assertEqual(observations, ["first", "second", "third"])

    def test_final_candidates_are_ranked_deterministically_after_merge(self):
        responses = {
            "a": [repo(2, "owner/low", stars=100)],
            "b": [repo(1, "owner/high", stars=100)],
        }
        result, _, _ = self.run_case(responses, ["a", "b"], total_cap=1)

        self.assertEqual(len(result.decisions), 1)
        self.assertEqual(result.decisions[0].candidate.github_repository_id, 1)


if __name__ == "__main__":
    unittest.main()
