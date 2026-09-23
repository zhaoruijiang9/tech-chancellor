import unittest
from pathlib import Path
from unittest.mock import patch

import run


class DashboardCliTests(unittest.TestCase):
    def test_dashboard_defaults_to_loopback_and_no_browser_can_be_requested(self):
        with patch.object(run, "serve_dashboard", return_value=0) as serve:
            with patch("sys.argv", ["run.py", "dashboard", "--no-browser"]):
                self.assertEqual(run.main(), 0)
        serve.assert_called_once()
        self.assertEqual(serve.call_args.kwargs["host"], "127.0.0.1")
        self.assertFalse(serve.call_args.kwargs["open_browser"])

    def test_dashboard_rejects_non_loopback_binding(self):
        with patch("sys.argv", ["run.py", "dashboard", "--host", "0.0.0.0"]):
            with self.assertRaises(SystemExit):
                run.main()

    def test_windows_entry_uses_relative_root(self):
        launcher = Path(__file__).parents[1] / "打开技术丞相.cmd"
        text = launcher.read_text(encoding="utf-8")
        self.assertIn("%~dp0", text)
        self.assertIn("dashboard", text)
        self.assertNotIn("D:\\personal-tech-intelligence", text)


if __name__ == "__main__":
    unittest.main()
