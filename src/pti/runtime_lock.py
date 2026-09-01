import json
import os
import socket
import subprocess
import sys
import time
from enum import Enum
from pathlib import Path


class LockState(str, Enum):
    ACQUIRED = "ACQUIRED"
    ACTIVE_VALID_LOCK = "ACTIVE_VALID_LOCK"
    STALE_LOCK = "STALE_LOCK"
    MALFORMED_LOCK = "MALFORMED_LOCK"
    UNKNOWN_LOCK_OWNER = "UNKNOWN_LOCK_OWNER"


def _process_info(pid: int) -> dict | None:
    if pid <= 0:
        return None
    command = ("$p=Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(pid) + "'; "
               "if($p){$p | Select-Object ProcessId,CreationDate,CommandLine,ExecutablePath "
               "| ConvertTo-Json -Compress}")
    try:
        completed = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                                   capture_output=True, text=True, encoding="utf-8", timeout=3, check=False)
        if completed.returncode != 0 or not completed.stdout.strip():
            return None
        value = json.loads(completed.stdout)
        return value if isinstance(value, dict) else None
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None


class CrashSafeLock:
    def __init__(self, path: str | Path, runner_type: str, legacy_stale_after_seconds: int = 900):
        self.path = Path(path)
        self.runner_type = runner_type
        self.legacy_stale_after_seconds = legacy_stale_after_seconds
        self.acquired = False

    def _metadata(self) -> dict:
        info = _process_info(os.getpid())
        return {"pid": os.getpid(), "process_start_time": info.get("CreationDate") if info else str(time.time()),
                "lock_created_at": time.time(), "runner_type": self.runner_type,
                "host": socket.gethostname(), "command_line": " ".join(sys.argv),
                "executable_path": info.get("ExecutablePath") if info else sys.executable}

    def acquire(self) -> LockState:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._metadata(), handle)
            self.acquired = True
            return LockState.ACQUIRED
        except FileExistsError:
            try:
                metadata = json.loads(self.path.read_text(encoding="utf-8"))
                pid = int(metadata["pid"])
                runner_type = metadata["runner_type"]
            except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                age = time.time() - self.path.stat().st_mtime
                if age >= self.legacy_stale_after_seconds:
                    self.path.unlink(missing_ok=True)
                    return self.acquire()
                return LockState.MALFORMED_LOCK
            if runner_type != self.runner_type:
                return LockState.UNKNOWN_LOCK_OWNER
            info = _process_info(pid)
            if info is None:
                self.path.unlink(missing_ok=True)
                return self.acquire()
            actual_command = " ".join(str(info.get("CommandLine", "")).replace('"', '').split())
            recorded_command = " ".join(str(metadata.get("command_line", "")).replace('"', '').split())
            command_matches = actual_command == recorded_command or actual_command.endswith(" " + recorded_command)
            if (str(info.get("CreationDate")) == str(metadata.get("process_start_time"))
                    and str(info.get("ExecutablePath")) == str(metadata.get("executable_path"))):
                return LockState.ACTIVE_VALID_LOCK
            return LockState.UNKNOWN_LOCK_OWNER

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False
