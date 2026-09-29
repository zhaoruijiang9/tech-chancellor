import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from pti.activation_worker import (run_activation_worker, search_active_index, safe_readme_from_archive,
                                   select_pilot_candidates, rollback_activation)
from pti.capability_intelligence import CapabilityStore
from pti.models import RepositoryRecord
from pti.storage import Database


class FakeProvider:
    def __init__(self, archive):
        self.archive = archive
        self.pins = 0
        self.fetches = 0

    def pin(self, owner_repo):
        self.pins += 1
        return "a" * 40

    def fetch(self, owner_repo, sha):
        self.fetches += 1
        return self.archive


def archive_with_readme(readme):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("repo-sha/README.md", readme)
    return output.getvalue()


class ActivationWorkerTests(unittest.TestCase):
    def setup_candidate(self, root):
        db = Database(root / "state" / "intelligence.db")
        db.initialize()
        db.upsert_repository(RepositoryRecord(7, "example/skill-index", "https://github.com/example/skill-index"))
        db.record_evaluation(7, 0, "REFERENCE_ONLY", [], None, None)
        store = CapabilityStore(db.path)
        store.upsert_source("github:7", "GITHUB_REPOSITORY", "example/skill-index", "https://github.com/example/skill-index", 7)
        store.upsert_implementation("impl:example/skill-index", "github:7", "skill-index", "TOOL_OR_WORKFLOW")
        store.upsert_capability("SKILL_ECOSYSTEM_DISCOVERY", "Skill discovery", "Direct sources")
        store.link_implementation_capability("impl:example/skill-index", "SKILL_ECOSYSTEM_DISCOVERY", "COMPLEMENT", "review")
        store.set_personal_state("IMPLEMENTATION", "impl:example/skill-index", "WATCHLIST", "review")
        db.enqueue_activation(7, "TIER_1_DECLARATIVE_SKILL", "QUARANTINED", "low-risk validation")
        return db, store

    def test_real_archive_is_pinned_installed_evaluated_and_projected(self):
        readme = """# Skills\n- [pdf](https://github.com/one/pdf-skill)\n- [pptx](https://github.com/two/slide-skill)\n- [xlsx](https://github.com/three/sheet-skill)\n"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, store = self.setup_candidate(root)
            provider = FakeProvider(archive_with_readme(readme))
            result = run_activation_worker(root, db, provider=provider)
            self.assertEqual(result[0]["status"], "SUCCEEDED")
            self.assertEqual(db.get_activation(7)["activation_state"], "TRIAL_ENABLED")
            job = db.list_activation_queue()[0]
            self.assertEqual(job["phase"], "AVAILABLE")
            self.assertEqual(json.loads(job["evidence_json"])["evaluation"]["outcome"], "IMPROVED")
            self.assertEqual(provider.pins, 1)
            self.assertEqual(provider.fetches, 1)
            self.assertEqual(select_pilot_candidates(db), [])
            self.assertEqual(search_active_index(root, "pdf")[0]["name"], "pdf")
            self.assertIn("AVAILABLE", [item["state"] for item in store.get_implementation("impl:example/skill-index")["personal_states"]])

            rolled_back = rollback_activation(root, 7, job["id"], db=db)
            self.assertEqual(rolled_back["status"], "ROLLED_BACK")
            self.assertEqual(search_active_index(root, "pdf"), [])
            self.assertEqual(db.get_activation(7)["activation_state"], "ROLLED_BACK")
            self.assertNotIn("AVAILABLE", [item["state"] for item in store.get_implementation("impl:example/skill-index")["personal_states"]])
            self.assertEqual(run_activation_worker(root, db, provider=provider), [])
            self.assertEqual(provider.fetches, 1)

    def test_crash_recovery_reuses_pinned_archive(self):
        readme = "- [pdf](https://github.com/one/pdf-skill)\n- [pptx](https://github.com/two/slide-skill)\n- [xlsx](https://github.com/three/sheet-skill)"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, _ = self.setup_candidate(root)
            provider = FakeProvider(archive_with_readme(readme))
            job = db.list_activation_queue()[0]
            db.claim_activation(job["id"])
            db.update_activation_job(job["id"], "SOURCE_PINNED", {"pin": "a" * 40})
            result = run_activation_worker(root, db, provider=provider)
            self.assertEqual(result[0]["status"], "SUCCEEDED")
            self.assertEqual(provider.pins, 0)

    def test_crash_after_available_phase_reconciles_queue_without_download(self):
        readme = "- [pdf](https://github.com/one/pdf-skill)\n- [pptx](https://github.com/two/slide-skill)\n- [xlsx](https://github.com/three/sheet-skill)"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, _ = self.setup_candidate(root)
            provider = FakeProvider(archive_with_readme(readme))
            self.assertEqual(run_activation_worker(root, db, provider=provider)[0]["status"], "SUCCEEDED")
            with db._connect() as connection:
                connection.execute("UPDATE activation_queue SET status='PROCESSING' WHERE id=1")
            self.assertEqual(run_activation_worker(root, db, provider=provider)[0]["status"], "SUCCEEDED")
            self.assertEqual(provider.fetches, 1)
            self.assertEqual(db.list_activation_queue()[0]["status"], "SUCCEEDED")

    def test_network_failure_is_retryable_and_keeps_same_job(self):
        class FlakyProvider(FakeProvider):
            def pin(self, owner_repo):
                self.pins += 1
                if self.pins == 1:
                    raise OSError("temporary network error")
                return "a" * 40

        readme = "- [pdf](https://github.com/one/pdf-skill)\n- [pptx](https://github.com/two/slide-skill)\n- [xlsx](https://github.com/three/sheet-skill)"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, _ = self.setup_candidate(root)
            provider = FlakyProvider(archive_with_readme(readme))
            self.assertEqual(run_activation_worker(root, db, provider=provider)[0]["status"], "RETRYABLE")
            existing_id = db.list_activation_queue()[0]["id"]
            self.assertEqual(db.enqueue_activation(7, "TIER_1_DECLARATIVE_SKILL", "QUARANTINED", "duplicate"), existing_id)
            self.assertEqual(run_activation_worker(root, db, provider=provider)[0]["status"], "SUCCEEDED")
            self.assertEqual(len(db.list_activation_queue()), 1)
            self.assertEqual(db.list_activation_queue()[0]["attempt_count"], 2)

    def test_only_explicit_real_use_projects_used(self):
        readme = "- [pdf](https://github.com/one/pdf-skill)\n- [pptx](https://github.com/two/slide-skill)\n- [xlsx](https://github.com/three/sheet-skill)"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db, store = self.setup_candidate(root)
            run_activation_worker(root, db, provider=FakeProvider(archive_with_readme(readme)))
            with self.assertRaises(ValueError):
                db.record_real_use(7, "fixture", "lookup", "ok", "smoke", real_task_evidence=False)
            self.assertNotIn("USED", [item["state"] for item in store.get_implementation("impl:example/skill-index")["personal_states"]])
            db.record_real_use(7, "real task", "lookup", "success", "explicit receipt", real_task_evidence=True)
            self.assertIn("USED", [item["state"] for item in store.get_implementation("impl:example/skill-index")["personal_states"]])

    def test_archive_rejects_path_traversal(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("../README.md", "bad")
        with self.assertRaises(ValueError):
            safe_readme_from_archive(payload.getvalue())

    def test_legacy_activation_queue_schema_migrates_without_losing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.db"
            connection = sqlite3.connect(path)
            try:
                connection.execute("""CREATE TABLE activation_queue(id INTEGER PRIMARY KEY,repository_id INTEGER,
                    activation_tier TEXT,desired_next_state TEXT,reason TEXT,created_at TEXT,
                    attempt_count INTEGER,last_attempt_at TEXT,status TEXT,failure_class TEXT)""")
                connection.execute("""INSERT INTO activation_queue VALUES
                    (5,7,'TIER_2_LOW_PRIVILEGE_LOCAL_TOOL','QUARANTINED','legacy','2026-01-01',1,NULL,'FAILED_TERMINAL','OLD_REASON')""")
                connection.commit()
            finally:
                connection.close()
            db = Database(path)
            db.initialize()
            row = db.list_activation_queue()[0]
            self.assertEqual((row["id"], row["status"], row["failure_class"]), (5, "FAILED_TERMINAL", "OLD_REASON"))
            self.assertEqual(row["phase"], "QUEUED")
