import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pti.capability_search import search_capabilities


def decision(route="AI_AGENT", action="REFERENCE_ONLY"):
    return json.dumps({"WHAT_IS_IT":"Agent workflow framework", "WHY_NOW":"review", "WHY_USER_MIGHT_CARE":"agent workflow",
        "WHAT_PROBLEM_DOES_IT_SOLVE":"orchestrating agents", "WHAT_USER_ALREADY_HAS":"native tools", "CAPABILITY_DELTA":"role orchestration",
        "IS_IT_ACTUALLY_BETTER":"UNPROVEN", "DUPLICATION":"LOW", "CURRENT_NEED_MATCH":"HIGH", "INTEGRATION_COST":"LOW",
        "SECURITY_RISK":"UNTRUSTED", "MATURITY":"REVIEWED", "MAINTENANCE_RISK":"UNKNOWN", "BEST_ROUTE":route, "ACTION":action})


class CapabilitySearchTests(unittest.TestCase):
    def test_search_is_read_only_and_returns_reference_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); db = root / "intelligence.db"
            c = sqlite3.connect(db)
            c.executescript("create table repositories (github_repository_id integer primary key, canonical_owner_repo text, url text, description text, stars integer, topics text, last_seen text); create table chancellor_decisions (github_repository_id integer primary key, decision_json text, packet_name text, imported_at text);")
            c.execute("insert into repositories values (1,'owner/repo','https://github.com/owner/repo','agent workflow',100,'[\"agents\"]','2026-09-01')")
            c.execute("insert into chancellor_decisions values (1,?,?,?)", (decision(), 'p.json', '2026-09-01'))
            c.commit(); c.close(); before=db.read_bytes()
            result = search_capabilities(db, problem="agent workflow", task_context="orchestrate agents", project_context="", current_capabilities=["native tools"], constraints=["low cost"], limit=3, project_label="D:\\money")
            self.assertEqual(result["status"], "MATCH")
            self.assertLessEqual(len(result["results"]), 3)
            self.assertEqual(result["results"][0]["consumption_form"], "KNOWLEDGE")
            self.assertEqual(before, db.read_bytes())

    def test_search_returns_no_match_without_fabricating_a_result(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "intelligence.db"; c=sqlite3.connect(db)
            c.executescript("create table repositories (github_repository_id integer primary key, canonical_owner_repo text, url text, description text, stars integer, topics text, last_seen text); create table chancellor_decisions (github_repository_id integer primary key, decision_json text, packet_name text, imported_at text);")
            c.commit(); c.close()
            self.assertEqual(search_capabilities(db, problem="quantum compiler", task_context="", project_context="", current_capabilities=[], constraints=[], limit=3)["status"], "NO_MATCH")
