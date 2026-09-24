import tempfile
import unittest
import importlib.util
from pathlib import Path
from unittest.mock import patch


class WindowsShortcutTests(unittest.TestCase):
    def test_installer_uses_portable_powershell_script(self):
        self.assertIsNotNone(importlib.util.find_spec("pti.windows_shortcut"))
        from pti.windows_shortcut import install_desktop_shortcut

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "scripts" / "install_shortcut.ps1"
            script.parent.mkdir()
            script.write_text("Write-Output shortcut", encoding="utf-8")
            completed = type("Completed", (), {"stdout": "C:/Users/Test/Desktop/技术丞相.lnk\n"})()
            with patch("pti.windows_shortcut.subprocess.run", return_value=completed) as run:
                result = install_desktop_shortcut(root)

        command = run.call_args.args[0]
        self.assertIn("-ProjectRoot", command)
        self.assertIn(str(root.resolve()), command)
        self.assertTrue(run.call_args.kwargs["check"])
        self.assertEqual(result["status"], "SHORTCUT_CREATED")
        self.assertTrue(result["path"].endswith("技术丞相.lnk"))

    def test_public_script_resolves_desktop_and_project_dynamically(self):
        script = Path(__file__).parents[1] / "scripts" / "install_shortcut.ps1"
        text = script.read_text(encoding="utf-8")
        self.assertIn("GetFolderPath", text)
        self.assertIn("$ProjectRoot", text)
        self.assertNotIn("C:\\Users\\25654", text)

    def test_public_script_is_windows_powershell_51_encoding_safe(self):
        script = Path(__file__).parents[1] / "scripts" / "install_shortcut.ps1"
        source = script.read_text(encoding="utf-8")
        self.assertTrue(source.isascii())


if __name__ == "__main__":
    unittest.main()
