import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pti.capability_library import build_library


DECISION = {"WHAT_IS_IT":"Agent framework", "WHY_NOW":"Review", "WHY_USER_MIGHT_CARE":"workflow",
"WHAT_PROBLEM_DOES_IT_SOLVE":"agent workflow", "WHAT_USER_ALREADY_HAS":"Codex", "CAPABILITY_DELTA":"patterns",
"IS_IT_ACTUALLY_BETTER":"UNPROVEN", "DUPLICATION":"HIGH", "CURRENT_NEED_MATCH":"MODERATE",
"INTEGRATION_COST":"HIGH", "SECURITY_RISK":"UNTRUSTED", "MATURITY":"REVIEWED", "MAINTENANCE_RISK":"UNKNOWN",
"BEST_ROUTE":"AI_AGENT", "ACTION":"REFERENCE_ONLY"}


class CapabilityLibraryTests(unittest.TestCase):
    def test_library_rebuilds_cards_from_current_semantic_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "intelligence.db"
            c = sqlite3.connect(db)
            c.executescript("""
                create table repositories (github_repository_id integer primary key, canonical_owner_repo text, url text, description text, stars integer, topics text, last_seen text);
                create table chancellor_decisions (github_repository_id integer primary key, decision_json text, packet_name text, imported_at text);
            """)
            c.execute("insert into repositories values (1,'owner/repo','https://github.com/owner/repo','agent workflow',100,'[\"agents\"]','2026-09-01T00:00:00Z')")
            c.execute("insert into chancellor_decisions values (1,?,?,?)", (json.dumps(DECISION), 'owner-repo-x.json', '2026-09-01T00:00:00Z'))
            c.commit(); c.close()
            result = build_library(root, db)
            self.assertEqual(result["count"], 1)
            self.assertTrue((root / "library/generated/index.md").exists())
            card = json.loads((root / "library/generated/repositories/owner--repo.json").read_text())
            self.assertEqual(card["evidence_maturity"], "REVIEWED")
            self.assertEqual(card["consumption_form"], "KNOWLEDGE")
