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
        self.assertIn('href="#capability/\' + encodeURIComponent(item.repository)', self.script)
        self.assertNotIn("data-capability-id", self.script)
        self.assertNotIn('<details class="details">', self.script)

    def test_dashboard_has_product_shell_and_quiet_state_styles(self):
        self.assertIn("app-chrome", self.html)
        self.assertIn("app.css?v=0.9.0", self.html)
        self.assertIn("app.js?v=0.9.0", self.html)
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

    def test_body_view_state_does_not_shadow_clickable_view_targets(self):
        self.assertIn("document.body.dataset.currentView = state.view", self.script)
        self.assertNotIn("document.body.dataset.view = state.view", self.script)
        self.assertIn('body[data-current-view="home"]', self.styles)

    def test_navigation_uses_native_hash_routes_separate_from_dynamic_content(self):
        self.assertIn('href="#capabilities"', self.html)
        self.assertIn('href="#capability/', self.script)
        self.assertIn('href="#document/', self.script)
        self.assertIn("window.addEventListener('hashchange'", self.script)
        self.assertIn("app.addEventListener('click'", self.script)
        self.assertNotIn("document.addEventListener('click'", self.script)

    def test_capability_art_preserves_source_aspect_ratio(self):
        self.assertIn('url("/assets/capability-studio-v2.png") var(--art-pos) center / cover no-repeat', self.styles)
        self.assertNotIn('/ 500% 100% no-repeat', self.styles)

    def test_human_gated_capabilities_have_bounded_feedback_controls(self):
        self.assertIn("function submitFeedback", self.script)
        self.assertIn("APPROVE_FOR_REVIEW", self.script)
        self.assertIn("只记录你的处理意见", self.script)
        self.assertIn("data-feedback-label", self.script)
        self.assertIn("item.human_action_required", self.script)

    def test_library_uses_four_human_sections_with_my_capabilities_as_default(self):
        self.assertIn("我的能力", self.script)
        self.assertIn("方法库", self.script)
        self.assertIn("待处理", self.script)
        self.assertIn("观察与归档", self.script)
        self.assertIn("librarySection: 'mine'", self.script)
        self.assertIn("data-library-section", self.script)
        self.assertIn("human_category", self.script)
        self.assertIn("capability_entities", self.script)
        self.assertIn("method_entities", self.script)
        self.assertIn("#ability/", self.script)
        self.assertIn("#method/", self.script)
        self.assertIn("source_freshness", self.script)
        self.assertIn("stale_reviews", self.script)

    def test_home_counts_real_capabilities_methods_waiting_and_watchlist(self):
        self.assertIn("可用能力", self.script)
        self.assertIn("已采用方法", self.script)
        self.assertIn("等待验证", self.script)
        self.assertIn("观察清单", self.script)
        self.assertIn("已评审项目总数", self.script)
        self.assertNotIn("项能力已进入本地能力库", self.script)

    def test_details_explain_classification_and_next_step(self):
        self.assertIn("classification_reason", self.script)
        self.assertIn("next_step", self.script)
        self.assertIn("installed", self.script)
        self.assertIn("runnable", self.script)

    def test_motion_is_subtle_restartable_and_non_looping(self):
        self.assertIn("function restartViewEntrance", self.script)
        self.assertIn("stage-intro", self.styles)
        self.assertIn('body[data-current-view="home"] .content', self.styles)
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
