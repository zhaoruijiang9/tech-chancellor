import json
import tempfile
import unittest
from pathlib import Path

from pti.bootstrap import initialize_project
from pti.dashboard_read_model import DashboardReadModel


class DashboardReadModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "discovery.json").write_text(json.dumps({}), encoding="utf-8")
        (self.root / "config" / "local_capability_profile.json").write_text(json.dumps({}), encoding="utf-8")
        initialize_project(self.root, self.root / "config" / "discovery.json", self.root / "config" / "local_capability_profile.json")
        (self.root / "README.md").write_text("# Hello\n\nA document.", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_database_is_a_valid_empty_state(self):
        model = DashboardReadModel(self.root)
        snapshot = model.snapshot()
        self.assertEqual(snapshot["counts"]["total"], 0)
        self.assertEqual(snapshot["recent_discoveries"], [])
        self.assertEqual(snapshot["validating"], [])
        self.assertTrue(any(item["path"] == "README.md" for item in model.documents()))

    def test_document_path_traversal_is_rejected(self):
        model = DashboardReadModel(self.root)
        with self.assertRaises(ValueError):
            model.document_text("../README.md")
        with self.assertRaises(ValueError):
            model.document_text("C:/Windows/win.ini")


if __name__ == "__main__":
    unittest.main()
