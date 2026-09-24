import unittest
from pathlib import Path


class DashboardAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = Path(__file__).parents[1] / "src" / "pti" / "dashboard_assets"
        cls.html = (cls.assets / "index.html").read_text(encoding="utf-8")
        cls.script = (cls.assets / "app.js").read_text(encoding="utf-8")
        cls.styles = (cls.assets / "app.css").read_text(encoding="utf-8")

    def test_capabilities_have_a_dedicated_detail_view(self):
        self.assertIn("renderCapabilityDetail", self.script)
        self.assertIn("data-capability-id", self.script)
        self.assertIn("data-capability-id=\"' + esc(item.repository)", self.script)
        self.assertNotIn("data-capability-id=\"' + esc(item.repository_id)", self.script)
        self.assertNotIn('<details class="details">', self.script)

    def test_dashboard_has_product_shell_and_quiet_state_styles(self):
        self.assertIn("app-rail", self.html)
        self.assertIn("overview-grid", self.styles)
        self.assertIn("quiet-state", self.styles)
        self.assertIn("focus-visible", self.styles)

    def test_normal_ui_keeps_machine_labels_out_of_primary_cards(self):
        card_start = self.script.index("function capabilityCard")
        card_end = self.script.index("function listRow", card_start)
        card_source = self.script[card_start:card_end]
        self.assertNotIn("activation_tier", card_source)
        self.assertNotIn("semantic_action", card_source)

    def test_second_pass_humanizes_system_and_detail_copy(self):
        self.assertIn("CHANCELLOR_SUCCESS_NO_PENDING':'处理完成，无待办", self.script)
        self.assertIn("function taskResultLabel", self.script)
        self.assertIn("function collectionReason", self.script)
        self.assertIn("primaryStatusLabel(item)", self.script)
        self.assertNotIn("esc(item.capability_delta ||", self.script)


if __name__ == "__main__":
    unittest.main()
