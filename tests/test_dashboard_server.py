import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pti.bootstrap import initialize_project
from pti.dashboard_server import DashboardServer, open_desktop_window, render_markdown
from pti.models import RepositoryRecord
from pti.storage import Database


class DashboardServerTests(unittest.TestCase):
    def test_desktop_window_uses_dedicated_app_profile(self):
        process = object()
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory) / "browser-profile"
            with patch("pti.dashboard_server._find_browser_app", return_value="C:/Edge/msedge.exe"):
                with patch("pti.dashboard_server.subprocess.Popen", return_value=process) as popen:
                    result = open_desktop_window("http://127.0.0.1:43210", profile)

        command = popen.call_args.args[0]
        self.assertIn("--app=http://127.0.0.1:43210", command)
        self.assertIn(f"--user-data-dir={profile.resolve()}", command)
        self.assertIn("--no-first-run", command)
        self.assertIs(result, process)

    def test_server_is_loopback_only_and_serves_read_apis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "discovery.json").write_text("{}", encoding="utf-8")
            (root / "config" / "local_capability_profile.json").write_text("{}", encoding="utf-8")
            initialize_project(root, root / "config" / "discovery.json", root / "config" / "local_capability_profile.json")
            server = DashboardServer(root, port=0)
            httpd, url = server.start()
            try:
                self.assertEqual(httpd.server_address[0], "127.0.0.1")
                with urlopen(url + "/api/summary") as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["counts"]["total"], 0)
                with urlopen(url + "/api/documents") as response:
                    self.assertIn("items", json.loads(response.read().decode("utf-8")))
                for asset in ("advisor-studio-v2.png", "capability-studio-v2.png"):
                    with self.subTest(asset=asset):
                        with urlopen(url + "/assets/" + asset) as response:
                            self.assertEqual(response.headers.get_content_type(), "image/png")
                            self.assertGreater(len(response.read()), 1000)
                with self.assertRaises(HTTPError):
                    urlopen(url + "/api/document?path=../README.md")
            finally:
                server.stop()

    def test_markdown_escapes_html_and_rejects_script_links(self):
        rendered = render_markdown("# Title\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))")
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_feedback_endpoint_records_only_allowlisted_human_choices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "discovery.json").write_text("{}", encoding="utf-8")
            (root / "config" / "local_capability_profile.json").write_text("{}", encoding="utf-8")
            initialize_project(root, root / "config" / "discovery.json", root / "config" / "local_capability_profile.json")
            db = Database(root / "state" / "intelligence.db")
            db.upsert_repository(RepositoryRecord(7, "owner/repo", "https://github.com/owner/repo"))
            server = DashboardServer(root, port=0)
            httpd, url = server.start()
            try:
                payload = json.dumps({"repository": "owner/repo", "label": "WATCH"}).encode("utf-8")
                request = Request(url + "/api/feedback", data=payload, method="POST", headers={
                    "Content-Type": "application/json",
                    "Origin": url,
                })
                with urlopen(request) as response:
                    result = json.loads(response.read().decode("utf-8"))
                self.assertEqual(result["status"], "FEEDBACK_RECORDED")
                self.assertEqual(db.get_feedback(7)[0]["label"], "WATCH")

                bad = Request(url + "/api/feedback", data=json.dumps({
                    "repository": "owner/repo", "label": "INSTALL_NOW"
                }).encode("utf-8"), method="POST", headers={
                    "Content-Type": "application/json",
                    "Origin": url,
                })
                with self.assertRaises(HTTPError) as error:
                    urlopen(bad)
                self.assertEqual(error.exception.code, 400)
            finally:
                server.stop()


if __name__ == "__main__":
    unittest.main()
