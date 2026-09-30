import importlib.util
import json
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pti.bootstrap import initialize_project
from pti.health import health_report
from pti.local_config import load_usage
from pti.stage_b import run_stage_b, stage_b_model
from pti.storage import Database

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("release_audit", ROOT / "scripts/release_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ReleaseSafetyTests(unittest.TestCase):
    def test_semantic_config_check_is_not_repository_specific(self):
        for value in ({"another/project": {"activation_state": "USED"}},
                      {"owner_approval": True}, {"items": [{"audited_at": "synthetic"}]}):
            self.assertTrue(audit.config_leaks("config/new-defaults.json", json.dumps(value)))
        self.assertEqual(audit.config_leaks("config/policy.json", '{"automatic_actions_allowed":["STATIC_ANALYSIS_ONLY"]}'), [])

    def test_runtime_location_classification_covers_arbitrary_installations(self):
        for path in ("managed_capabilities/new-tool/active.json", "state/usage.db", "user_artifacts/new/receipt.json", "config/anything.local.json"):
            self.assertEqual(audit.classify(path), "PERSONAL_RUNTIME")
        self.assertEqual(audit.classify("templates/tool.example.json"), "PUBLIC_TEMPLATE_EXAMPLE")

    def test_secret_scanner_reports_no_values(self):
        synthetic = "ghp_" + "Z" * 36
        findings = audit.scan_text(synthetic)
        self.assertEqual(findings[0]["kind"], "GITHUB_TOKEN")
        self.assertNotIn(synthetic, json.dumps(findings))

    def test_usage_defaults_and_local_overrides_do_not_create_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "config").mkdir()
            (root / "config/capability_usage_defaults.json").write_text('{"example/tool":{"human_summary":"Generic"}}')
            (root / "config/human_capability_usage.json").write_text('{"example/tool":{"user_entrypoint":"Local only"}}')
            self.assertEqual(load_usage(root)["example/tool"], {"human_summary": "Generic", "user_entrypoint": "Local only"})
            self.assertFalse((root / "state").exists())

    def test_init_creates_unknown_profile_without_overwriting_user_choices(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "config").mkdir()
            config = root / "config/discovery.json"
            config.write_text('{}')
            (root / "config/local_capability_profile.example.json").write_text('{"AI_AGENT":"UNKNOWN"}')
            profile = root / "config/local_capability_profile.json"
            initialize_project(root, config, profile)
            self.assertEqual(json.loads(profile.read_text())["AI_AGENT"], "UNKNOWN")
            profile.write_text('{"AI_AGENT":"User preference"}')
            initialize_project(root, config, profile)
            self.assertEqual(json.loads(profile.read_text())["AI_AGENT"], "User preference")
            with Database(root / "state/intelligence.db")._connect() as connection:
                for table in ("repositories", "personal_states", "capability_sources", "activation_records", "capability_invocations"):
                    self.assertEqual(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)

    def test_model_precedence_preserves_legacy_local_config_and_cli_default(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True):
            root = Path(temp)
            (root / "config").mkdir()
            self.assertIsNone(stage_b_model(root))
            (root / "config/stage_b.json").write_text('{"model":"legacy-local-choice"}')
            self.assertEqual(stage_b_model(root), "legacy-local-choice")
            (root / "config/stage_b.local.json").write_text('{"model":"local-choice"}')
            self.assertEqual(stage_b_model(root), "local-choice")
            os.environ["PTI_STAGE_B_MODEL"] = "explicit-choice"
            self.assertEqual(stage_b_model(root), "explicit-choice")

    def test_optional_components_do_not_break_base_health(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=True):
            root = Path(temp)
            Database(root / "state/intelligence.db").initialize()
            with patch("pti.health.shutil.which", return_value=None), patch("pti.health._task", side_effect=lambda name: {"name": name, "status": "QUERY_FAILED"}):
                result = health_report(root)
            self.assertEqual(result["status"], "HEALTHY")
            self.assertEqual(result["optional_components"], {"codex": "NOT_CONFIGURED", "github": "PUBLIC_ANONYMOUS", "scheduler": "NOT_INSTALLED"})

    def test_no_codex_keeps_pending_packet_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "chancellor_pending").mkdir()
            packet = root / "chancellor_pending/test.json"
            packet.write_text('{"status":"PENDING_CODEX_REVIEW","repository_identity":{"github_repository_id":1}}')
            with patch("pti.stage_b.CODEX_EXE", Path(temp) / "absent-codex"):
                result = run_stage_b(root)
            self.assertEqual(result["failures"][0]["code"], "CODEX_NOT_CONFIGURED")
            self.assertTrue(packet.exists())
            self.assertFalse((root / "state/chancellor.lock").exists())

    def test_codex_auth_failure_is_visible_and_keeps_packet(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "chancellor_pending").mkdir()
            packet = root / "chancellor_pending/test.json"
            packet.write_text('{"status":"PENDING_CODEX_REVIEW","repository_identity":{"github_repository_id":1}}')
            failed = subprocess.CompletedProcess([], 1, stdout="", stderr="Authentication required: run codex login")
            with patch("pti.stage_b.subprocess.run", return_value=failed):
                result = run_stage_b(root)
            self.assertIn("Authentication required", result["failures"][0]["message"])
            self.assertEqual(result["processed"], 0)
            self.assertTrue(packet.exists())
            self.assertFalse((root / "state/chancellor.lock").exists())

    def test_published_v0_1_schema_upgrade_is_non_destructive_and_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "state/intelligence.db"
            path.parent.mkdir()
            connection = sqlite3.connect(path)
            connection.executescript((ROOT / "tests/fixtures/v0_1_schema.sql").read_text())
            connection.execute("INSERT INTO repositories(github_repository_id,canonical_owner_repo,url,first_seen,last_seen) VALUES(1,'example/legacy','https://github.com/example/legacy','2020-01-01','2020-01-01')")
            connection.execute("INSERT INTO user_feedback(github_repository_id,label,note) VALUES(1,'WATCH','synthetic legacy record')")
            from pti.chancellor_contract import REQUIRED_FIELDS
            decision = {field: "Synthetic legacy evidence" for field in REQUIRED_FIELDS}
            decision.update(ACTION="WATCH", BEST_ROUTE="AI_AGENT")
            connection.execute("INSERT INTO chancellor_decisions(github_repository_id,decision_json,packet_name) VALUES(1,?,?)", (json.dumps(decision), 'synthetic.json'))
            before = {table: connection.execute(f"SELECT * FROM {table}").fetchall() for table in ("repositories", "user_feedback", "chancellor_decisions")}
            connection.commit()
            connection.close()
            db = Database(path)
            db.initialize()
            db.initialize()
            with db._connect() as connection:
                for table, rows in before.items():
                    after = connection.execute(f"SELECT * FROM {table}").fetchall()
                    self.assertEqual([tuple(row)[:len(rows[0])] for row in after], rows)
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_public_guidance_has_no_author_approval_defaults(self):
        text = (ROOT / "config/capability_usage_defaults.json").read_text(encoding="utf-8")
        self.assertEqual(audit.config_leaks("config/capability_usage_defaults.json", text), [])
        self.assertNotIn("TRIAL_ENABLED", text)
        self.assertNotIn("GLOBAL_CODEX_CONTROLLED", text)


if __name__ == "__main__":
    unittest.main()
