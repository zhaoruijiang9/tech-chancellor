import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from pti.packet_lifecycle import claim_packet, complete_packet, list_active_pending_packets, recover_stale_processing
from pti.runtime_lock import CrashSafeLock, LockState
from pti.packet_lifecycle import active_pending_count


def packet(path: Path, repository_id: int = 7):
    path.write_text(json.dumps({
        "repository_identity": {"github_repository_id": repository_id, "canonical_owner_repo": "example/project", "url": "https://github.com/example/project"},
        "status": "PENDING_CODEX_REVIEW",
    }), encoding="utf-8")


class PacketLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.pending = self.root / "chancellor_pending"
        self.pending.mkdir()

    def tearDown(self):
        self.directory.cleanup()

    def test_only_valid_unprocessed_packets_are_active(self):
        packet(self.pending / "active.json")
        packet(self.pending / "done.processed.json", 8)
        packet(self.pending / "done-again.json", 9)
        (self.pending / "done-again.processed.json").write_text("{}", encoding="utf-8")
        (self.pending / "bad.json").write_text("not json", encoding="utf-8")
        (self.pending / "raw.chancellor.raw.json").write_text("{}", encoding="utf-8")
        self.assertEqual([p.name for p in list_active_pending_packets(self.pending)], ["active.json"])

    def test_claim_and_complete_are_atomic_lifecycle_steps(self):
        source = self.pending / "active.json"
        packet(source)
        claimed = claim_packet(source)
        self.assertEqual(claimed.name, "active.processing.json")
        self.assertFalse(source.exists())
        completed = complete_packet(claimed)
        self.assertEqual(completed.name, "active.processed.json")
        self.assertEqual(list_active_pending_packets(self.pending), [])

    def test_complete_is_idempotent_when_processed_marker_already_exists(self):
        source = self.pending / "active.json"
        packet(source)
        claimed = claim_packet(source)
        claimed.with_name("active.processed.json").write_text("{}", encoding="utf-8")
        completed = complete_packet(claimed)
        self.assertEqual(completed.name, "active.processed.json")
        self.assertFalse(claimed.exists())

    def test_stale_processing_packet_returns_to_retryable_active_state(self):
        processing = self.pending / "crashed.processing.json"
        packet(processing)
        old = time.time() - 3600
        os.utime(processing, (old, old))
        recovered = recover_stale_processing(self.pending, max_age_seconds=60)
        self.assertEqual([p.name for p in recovered], ["crashed.json"])
        self.assertEqual([p.name for p in list_active_pending_packets(self.pending)], ["crashed.json"])

    def test_active_pending_count_uses_pending_directory(self):
        packet(self.pending / "active.json")
        self.assertEqual(active_pending_count(self.pending), 1)


class LockTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "worker.lock"

    def tearDown(self):
        self.directory.cleanup()

    def test_current_owner_is_active_and_cleanup_is_safe(self):
        first = CrashSafeLock(self.path, "test-runner")
        self.assertEqual(first.acquire(), LockState.ACQUIRED)
        second = CrashSafeLock(self.path, "test-runner")
        self.assertEqual(second.acquire(), LockState.ACTIVE_VALID_LOCK)
        first.release()
        self.assertFalse(self.path.exists())

    def test_dead_owner_is_recovered(self):
        self.path.write_text(json.dumps({"pid": 99999999, "process_start_time": "never", "runner_type": "test-runner"}), encoding="utf-8")
        lock = CrashSafeLock(self.path, "test-runner")
        self.assertEqual(lock.acquire(), LockState.ACQUIRED)
        lock.release()

    def test_empty_legacy_lock_is_not_treated_as_live(self):
        self.path.write_text("", encoding="utf-8")
        old = time.time() - 3600
        os.utime(self.path, (old, old))
        lock = CrashSafeLock(self.path, "test-runner", legacy_stale_after_seconds=60)
        self.assertEqual(lock.acquire(), LockState.ACQUIRED)
        lock.release()
