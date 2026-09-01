import unittest
from dataclasses import replace

from pti.models import RepositoryRecord
from pti.review_queue import material_evidence_projection, review_eligibility, allocate_review_slots
from pti.chancellor_contract import REQUIRED_FIELDS


def repo(**changes):
    base = RepositoryRecord(github_repository_id=1, canonical_owner_repo="owner/repo",
                            url="https://github.com/owner/repo", description="An agent framework",
                            topics=["agents", "python"], stars=100)
    return replace(base, **changes)


class ReviewEligibilityTests(unittest.TestCase):
    def test_contract_contains_schema_required_maintenance_and_problem_fields(self):
        self.assertIn("MAINTENANCE_RISK", REQUIRED_FIELDS)
        self.assertIn("WHAT_PROBLEM_DOES_IT_SOLVE", REQUIRED_FIELDS)
    def test_first_review_is_eligible(self):
        result = review_eligibility(repo(), None)
        self.assertEqual(result.reason, "FIRST_REVIEW")

    def test_stars_only_change_is_observation_only(self):
        old = repo(previous_decision="REFERENCE_ONLY")
        new = repo(stars=1000)
        self.assertIsNone(review_eligibility(new, old).reason)

    def test_material_description_change_is_eligible(self):
        old = repo(previous_decision="REFERENCE_ONLY")
        new = repo(description="An agent framework with durable workflow memory")
        self.assertEqual(review_eligibility(new, old).reason, "MATERIAL_EVIDENCE_CHANGED")

    def test_format_only_readme_change_does_not_change_projection(self):
        old = material_evidence_projection(repo(), ["Capabilities", "Tools"])
        new = material_evidence_projection(repo(description=" An   agent framework "), ["Capabilities", "Tools"])
        self.assertEqual(old, new)

    def test_user_request_has_highest_priority(self):
        result = review_eligibility(repo(), repo(), user_requested=True, material_changed=True, watch_due=True)
        self.assertEqual(result.reason, "USER_REQUESTED")

    def test_reviewed_unchanged_repo_is_not_eligible(self):
        existing = repo(previous_decision="REFERENCE_ONLY", material_evidence_fingerprint="same")
        current = repo(material_evidence_fingerprint="same")
        self.assertIsNone(review_eligibility(current, existing).reason)

    def test_allocation_is_quality_first_and_not_input_order(self):
        low = repo(github_repository_id=2, previous_decision=None)
        high = repo(github_repository_id=3, previous_decision=None, current_need=4) if False else repo(github_repository_id=3, previous_decision=None)
        from pti.policy import score_candidate, decide_candidate
        low_eval = decide_candidate(score_candidate(low and __import__('pti.policy', fromlist=['Candidate']).Candidate('low','low', ['AI_AGENT'], 1, 0, 1, 1, 1), {}))
        high_eval = decide_candidate(score_candidate(__import__('pti.policy', fromlist=['Candidate']).Candidate('high','agent workflow', ['AI_AGENT'], 100, 0, 5, 5, 1), {}))
        low_eval.review_reason = "FIRST_REVIEW"
        high_eval.review_reason = "FIRST_REVIEW"
        low_eval.semantic_review = {"ok": "low"}
        high_eval.semantic_review = {"ok": "high"}
        self.assertEqual([item.candidate.name for item in allocate_review_slots([low_eval, high_eval], 1)], ["high"])
