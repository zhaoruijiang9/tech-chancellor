import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from pti.bootstrap import initialize_project
from pti.dashboard_server import DashboardServer, render_markdown


class DashboardServerTests(unittest.TestCase):
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
                with self.assertRaises(HTTPError):
                    urlopen(url + "/api/document?path=../README.md")
            finally:
                server.stop()

    def test_markdown_escapes_html_and_rejects_script_links(self):
        rendered = render_markdown("# Title\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))")
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("javascript:", rendered)
        self.assertIn("&lt;script&gt;", rendered)


if __name__ == "__main__":
    unittest.main()
