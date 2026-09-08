import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pti.human_toolbox import build_human_toolbox


class HumanToolboxTests(unittest.TestCase):
    def test_toolbox_is_derived_from_current_cards_and_has_human_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "human_capability_usage.json").write_text(json.dumps({
                "owner/tool": {
                    "human_summary": "用于测试的工具",
                    "when_to_use": ["需要测试"],
                    "how_to_ask_codex": ["用测试工具"],
                    "expected_outputs": ["结果"],
                    "user_entrypoint": "直接说目标",
                    "automatic_use_policy": "明确要求",
                    "main_limitations": ["测试限制"],
                }
            }), encoding="utf-8")
            db_path = root / "state.db"
            db = sqlite3.connect(db_path)
            db.executescript("""
                create table repositories (github_repository_id integer primary key, canonical_owner_repo text, url text, description text, stars integer, topics text, previous_decision text, previous_routes text);
                create table chancellor_decisions (github_repository_id integer primary key, decision_json text, packet_name text, imported_at text);
            """)
            db.execute("insert into repositories values (1,'owner/tool','https://example.test','tool',1,'[]','REFERENCE_ONLY','[]')")
            db.execute("insert into chancellor_decisions values (1,?,?,?)", (json.dumps({"ACTION":"REFERENCE_ONLY","WHAT_IS_IT":"tool","WHAT_PROBLEM_DOES_IT_SOLVE":"test"}), "review.json", "2026"))
            db.commit(); db.close()
            result = build_human_toolbox(root, db_path)
            text = (root / "MY_CAPABILITIES.md").read_text(encoding="utf-8")
            self.assertEqual(result["count"], 1)
            self.assertIn("# 我现在能用什么？", text)
            self.assertIn("用于测试的工具", text)
            payload = json.loads((root / "library" / "generated" / "human_toolbox.json").read_text(encoding="utf-8"))
            self.assertIn("human_summary", payload["cards"][0])


if __name__ == "__main__":
    unittest.main()
