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
        self.assertIn("app-chrome", self.html)
        self.assertIn("home-stage", self.styles)
        self.assertIn("capability-gallery", self.styles)
        self.assertIn("quiet-state", self.styles)
        self.assertIn("focus-visible", self.styles)

    def test_art_direction_uses_local_assets_and_real_html(self):
        self.assertIn("advisor-studio-v2.png", self.styles)
        self.assertIn("capability-studio-v2.png", self.styles)
        self.assertIn("deskmat-stage", self.styles)
        self.assertIn("intelligence-veil", self.styles)
        self.assertIn("home-focus", self.script)
        self.assertIn("gallery-card", self.script)
        self.assertNotIn("https://", self.styles)

    def test_motion_is_subtle_restartable_and_non_looping(self):
        self.assertIn("function restartViewEntrance", self.script)
        self.assertIn("stage-intro", self.styles)
        self.assertIn('body[data-view="home"] .content', self.styles)
        self.assertNotIn("animation: pulse", self.styles)
        self.assertNotIn("home-focus glass-panel", self.script)

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
