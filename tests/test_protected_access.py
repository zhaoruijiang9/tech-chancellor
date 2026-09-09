import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pti.protected_access import AuthorizationDenied, validate_authorization


class ProtectedAccessTests(unittest.TestCase):
    def _receipt(self, root: Path, **overrides):
        data = {
            "schema_version": 1,
            "authorization_source": "DIRECT_USER_TASK_AUTHORIZATION",
            "capability": "Archify",
            "target_path": str(root / "protected"),
            "access_mode": "READ_ONLY",
            "purpose": "ARCHITECTURE_ANALYSIS",
            "output_boundary": "OUTSIDE_TARGET_PROJECT",
            "task_id": "task-123",
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            "nonce": "n" * 32,
        }
        data.update(overrides)
        receipt = root / "authorization.json"
        receipt.write_text(json.dumps(data), encoding="utf-8")
        return receipt, data

    def test_explicit_read_only_authorization_allows_external_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, data = self._receipt(root)
            result = validate_authorization(receipt, capability="Archify", target_path=data["target_path"], purpose="ARCHITECTURE_ANALYSIS", output_path=root / "output.html")
            self.assertEqual(result["access_mode"], "READ_ONLY")

    def test_missing_authorization_denies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(AuthorizationDenied):
                validate_authorization(root / "missing.json", capability="Archify", target_path=root / "protected", purpose="ARCHITECTURE_ANALYSIS", output_path=root / "out.html")

    def test_write_and_expired_authorizations_deny(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, data = self._receipt(root, access_mode="READ_WRITE")
            with self.assertRaises(AuthorizationDenied):
                validate_authorization(receipt, capability="Archify", target_path=data["target_path"], purpose="ARCHITECTURE_ANALYSIS", output_path=root / "out.html")
            receipt, data = self._receipt(root, expires_at="2000-01-01T00:00:00+00:00")
            with self.assertRaises(AuthorizationDenied):
                validate_authorization(receipt, capability="Archify", target_path=data["target_path"], purpose="ARCHITECTURE_ANALYSIS", output_path=root / "out.html")

    def test_wrong_path_and_inside_output_deny(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            receipt, data = self._receipt(root)
            with self.assertRaises(AuthorizationDenied):
                validate_authorization(receipt, capability="Archify", target_path=root / "other", purpose="ARCHITECTURE_ANALYSIS", output_path=root / "out.html")
            with self.assertRaises(AuthorizationDenied):
                validate_authorization(receipt, capability="Archify", target_path=data["target_path"], purpose="ARCHITECTURE_ANALYSIS", output_path=Path(data["target_path"]) / "out.html")
