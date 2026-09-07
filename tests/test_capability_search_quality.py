import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pti.capability_search import search_capabilities


def _decision(route, action="REFERENCE_ONLY"):
    return json.dumps({"WHAT_IS_IT":"Agent workflow and repository context tool", "WHY_NOW":"review", "WHY_USER_MIGHT_CARE":"agent context",
        "WHAT_PROBLEM_DOES_IT_SOLVE":"agent workflow semantic code search context compression persistent memory quant research backtesting",
        "WHAT_USER_ALREADY_HAS":"Codex native tools", "CAPABILITY_DELTA":"reference patterns", "IS_IT_ACTUALLY_BETTER":"UNPROVEN",
        "DUPLICATION":"UNKNOWN", "CURRENT_NEED_MATCH":"UNKNOWN", "INTEGRATION_COST":"UNKNOWN", "SECURITY_RISK":"UNTRUSTED",
        "MATURITY":"REVIEWED", "MAINTENANCE_RISK":"UNKNOWN", "BEST_ROUTE":route, "ACTION":action})


class CapabilitySearchQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.db = Path(self.temp.name) / "db.sqlite"
        c=sqlite3.connect(self.db)
        c.executescript("create table repositories (github_repository_id integer primary key, canonical_owner_repo text, url text, description text, stars integer, topics text, last_seen text); create table chancellor_decisions (github_repository_id integer primary key, decision_json text, packet_name text, imported_at text);")
        for i,(name,route) in enumerate([('chunkhound/chunkhound','AI_AGENT'),('headroomlabs-ai/headroom','AI_AGENT'),('volcengine/MineContext','AI_EXPERIENCE'),('nieledran/backtesting-engine','QUANT_DATA')],1):
            c.execute('insert into repositories values (?,?,?,?,?,?,?)',(i,name,'https://github.com/'+name,'Agent workflow semantic code search context compression persistent memory quant research backtesting',100,'[]','2026-09-01'))
            c.execute('insert into chancellor_decisions values (?,?,?,?)',(i,_decision(route),'p.json','2026-09-01'))
        c.commit(); c.close()

    def tearDown(self): self.temp.cleanup()

    def test_fixture_contracts_and_search_limits(self):
        cases=json.loads(Path('tests/fixtures/capability_search_cases.json').read_text())
        for case in cases:
            result=search_capabilities(self.db, problem=case['problem'], task_context=case['task_context'], project_context='', current_capabilities=case.get('current_capabilities',[]), constraints=case['constraints'], limit=3)
            self.assertLessEqual(len(result['results']),3,case['name'])
            self.assertTrue(result['status'] in {'MATCH','NO_MATCH'},case['name'])
        self.assertEqual(search_capabilities(self.db, problem='quantum compiler verification', task_context='formal quantum circuit compiler', project_context='', current_capabilities=[], constraints=['no network'], limit=3)['status'],'NO_MATCH')

    def test_same_snapshot_and_query_are_deterministic(self):
        args=dict(problem='semantic code search',task_context='find symbols',project_context='',current_capabilities=['native tools'],constraints=[],limit=3)
        self.assertEqual(search_capabilities(self.db,**args),search_capabilities(self.db,**args))

    def test_local_typo_request_does_not_retrieve_capability_cards(self):
        result = search_capabilities(
            self.db,
            problem='fix a typo in a known file',
            task_context='simple local maintenance',
            project_context='known repository',
            current_capabilities=['text editor'],
            constraints=['direct edit'],
            limit=3,
        )
        self.assertEqual(result['status'], 'NO_MATCH')
        self.assertEqual(result['results'], [])
