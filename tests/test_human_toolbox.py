import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from pti.human_toolbox import build_human_toolbox
from pti.capability_intelligence import CapabilityStore


class HumanToolboxTests(unittest.TestCase):
    def test_normalized_capability_and_evidence_gated_method_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path = root / "state.db"
            db = sqlite3.connect(db_path)
            db.executescript("""
                create table repositories (github_repository_id integer primary key, canonical_owner_repo text, url text, description text, stars integer, topics text, previous_decision text, previous_routes text);
                create table chancellor_decisions (github_repository_id integer primary key, decision_json text, packet_name text, imported_at text);
            """)
            db.close()
            store = CapabilityStore(db_path)
            store.upsert_source("src:one", "GITHUB_REPOSITORY", "owner/tool", "https://github.com/owner/tool")
            store.upsert_implementation("impl:one", "src:one", "Tool", "CLI")
            store.upsert_capability("cap:one", "架构可视化", "可视化系统结构")
            store.link_implementation_capability("impl:one", "cap:one", "NEW_CAPABILITY", "test")
            store.set_personal_state("CAPABILITY", "cap:one", "USED", "test")
            store.upsert_method("method:one", "src:one", "需求澄清", "用问题定义范围")
            store.record_method_evidence("method:one", "WORKFLOW_MECHANISM", "test:policy", "policy", True)
            store.record_method_evidence("method:one", "VERIFIED_USE", "test:use", "task", True)
            result = build_human_toolbox(root, db_path)
            text = (root / "MY_CAPABILITIES.md").read_text(encoding="utf-8")
            self.assertIn("### 架构可视化", text)
            self.assertIn("### 需求澄清", text)
            self.assertNotIn("### owner/tool：", text)
            self.assertEqual(result["directly_usable"], 1)
            self.assertEqual(result["adopted_methods"], 1)

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
            self.assertIn("## 观察与归档", text)
            self.assertNotIn("## 已安装 / 可以直接用\n\n### owner/tool", text)
            payload = json.loads((root / "library" / "generated" / "human_toolbox.json").read_text(encoding="utf-8"))
            self.assertIn("human_summary", payload["cards"][0])
            self.assertEqual(payload["cards"][0]["human_category"], "WATCHLIST")


if __name__ == "__main__":
    unittest.main()
