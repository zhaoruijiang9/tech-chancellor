"""Optional, fail-closed Docker/WSL2 substrate for bounded offline evaluation."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass


BACKEND = 'DOCKER_WSL2_LINUX'
ENDPOINT = 'npipe:////./pipe/dockerDesktopLinuxEngine'
IMAGE = re.compile(r'^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$')
PIN = re.compile(r'^[0-9a-f]{40}$')
OUTPUT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')
REQUIRED_CHECKS = {'nonroot', 'env_denied', 'secret_denied', 'outside_host_write',
                   'docker_socket_denied', 'credential_paths_absent', 'output_writable',
                   'source_readonly', 'input_readonly', 'root_readonly', 'tmpfs_writable',
                   'caps_dropped', 'no_new_privileges', 'pid_namespace', 'dns_blocked',
                   'http_blocked', 'tcp_blocked'}


class SandboxRejected(ValueError):
    pass


@dataclass(frozen=True)
class ExecutionContract:
    sandbox_backend: str
    sandbox_image: str
    source_pin: str
    runtime_type: str
    command: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    working_directory: str = '/candidate'
    network_policy: str = 'NONE'
    timeout_seconds: int = 30
    memory_mb: int = 128
    cpus: float = 0.5
    pids_limit: int = 32

    @classmethod
    def from_dict(cls, data: dict) -> ExecutionContract:
        fields = cls.__dataclass_fields__
        if not isinstance(data, dict) or set(data) - set(fields):
            raise SandboxRejected('UNSUPPORTED_EXECUTION_CONTRACT_FIELDS')
        value = dict(data)
        for key in ('command', 'expected_outputs'):
            if not isinstance(value.get(key), (list, tuple)):
                raise SandboxRejected('COMMAND_AND_OUTPUT_LIST_REQUIRED')
            value[key] = tuple(value[key])
        try:
            spec = cls(**value)
        except TypeError as error:
            raise SandboxRejected('INCOMPLETE_EXECUTION_CONTRACT') from error
        if spec.sandbox_backend != BACKEND or spec.runtime_type not in {'CLI', 'PYTHON'}:
            raise SandboxRejected('UNSUPPORTED_SANDBOX_RUNTIME')
        if not isinstance(spec.sandbox_image, str) or not IMAGE.fullmatch(spec.sandbox_image):
            raise SandboxRejected('DIGEST_PINNED_IMAGE_REQUIRED')
        if not isinstance(spec.source_pin, str) or not PIN.fullmatch(spec.source_pin):
            raise SandboxRejected('PINNED_SOURCE_REQUIRED')
        if spec.network_policy != 'NONE' or spec.working_directory != '/candidate':
            raise SandboxRejected('OFFLINE_FIXED_WORKDIR_REQUIRED')
        if not 1 <= len(spec.command) <= 24 or any(not isinstance(x, str) or not x or
                len(x) > 1024 or '\x00' in x for x in spec.command):
            raise SandboxRejected('BOUNDED_COMMAND_REQUIRED')
        if not 1 <= len(spec.expected_outputs) <= 4 or any(not isinstance(x, str) or
                not OUTPUT.fullmatch(x) for x in spec.expected_outputs):
            raise SandboxRejected('FLAT_EXPECTED_OUTPUT_ALLOWLIST_REQUIRED')
        if len(set(spec.expected_outputs)) != len(spec.expected_outputs):
            raise SandboxRejected('DUPLICATE_EXPECTED_OUTPUT')
        for key, low, high in (('timeout_seconds', 1, 120), ('memory_mb', 64, 1024), ('pids_limit', 16, 128)):
            number = getattr(spec, key)
            if isinstance(number, bool) or not isinstance(number, int) or not low <= number <= high:
                raise SandboxRejected('INVALID_RESOURCE_BOUND_' + key)
        if isinstance(spec.cpus, bool) or not isinstance(spec.cpus, (int, float)) or not 0.1 <= spec.cpus <= 2:
            raise SandboxRejected('INVALID_CPU_BOUND')
        return spec

    def to_dict(self) -> dict:
        return asdict(self)


def _verified_config(root: Path) -> tuple[dict, dict]:
    config_path = root / 'state/secure_execution.local.json'
    evidence_path = root / 'state/containment-evidence.json'
    if config_path.resolve() != config_path.absolute() or evidence_path.resolve() != evidence_path.absolute():
        raise SandboxRejected('LOCAL_STATE_LINK_FORBIDDEN')
    if not config_path.is_file():
        raise SandboxRejected('SANDBOX_NOT_CONFIGURED')
    try:
        config = json.loads(config_path.read_text(encoding='utf-8'))
        raw = evidence_path.read_bytes()
        proof = json.loads(raw)
        if hashlib.sha256(raw).hexdigest() != config['verification_sha256']:
            raise SandboxRejected('CONTAINMENT_RECEIPT_INTEGRITY_FAILURE')
        checks = {x.removeprefix('PASS:') for x in proof['fixture_checks'] if x.startswith('PASS:')}
        if (proof['phase_c'] != 'PASS_VERIFIED_FOR_BOUNDED_EVALUATION' or
                not REQUIRED_CHECKS <= checks or not proof['observed_process_ids_removed'] or
                proof['fixture_exit_code'] != 0 or not proof['background_children_observed'] or
                not proof['timeout_observed'] or proof['timeout_cleanup'] != 'PASS_CONTAINER_REMOVED_WITH_CHILDREN' or
                not proof['host_secret_unchanged'] or
                proof['host_service_scheduler_path_check'] != 'PASS_UNCHANGED_INVENTORY' or
                proof['residual_container_check'] != 'PASS' or not proof['secret_sentinel_removed'] or
                proof['d_money_accessed'] or proof['d_money_mounted'] or proof['d_money_container_paths_visible']):
            raise SandboxRejected('REAL_CONTAINMENT_EVIDENCE_REQUIRED')
        approved = config['approved_images']
        if not approved or any(not isinstance(x, str) or not IMAGE.fullmatch(x) for x in approved):
            raise SandboxRejected('APPROVED_IMAGE_DIGESTS_REQUIRED')
        if approved != [proof['image_digest']]:
            raise SandboxRejected('ONLY_REAL_TESTED_IMAGE_APPROVED_IN_V01')
        return config, proof
    except (OSError, KeyError, TypeError, AttributeError, UnicodeError, json.JSONDecodeError) as error:
        raise SandboxRejected('CONTAINMENT_RECEIPT_MISSING_OR_INVALID') from error


def secure_execution_status(root: str | Path) -> dict:
    """Read only local evidence; a dashboard request never starts Docker."""
    try:
        _, proof = _verified_config(Path(root))
        return {'status': 'VERIFIED_RECEIPT', 'backend': BACKEND,
                'label': '隔离验证已通过', 'verified_at': proof.get('finished_utc'),
                'runtime_health': 'CHECKED_AT_EXECUTION', 'scope': 'bounded offline execution only'}
    except (SandboxRejected, OSError) as error:
        return {'status': 'UNCONFIGURED' if str(error) == 'SANDBOX_NOT_CONFIGURED' else 'NOT_VERIFIED',
                'backend': None, 'label': '未配置' if str(error) == 'SANDBOX_NOT_CONFIGURED' else '验证证据不可用',
                'reason': str(error)}


def _tree_hashes(directory: Path) -> dict:
    if directory.resolve() != directory.absolute() or not directory.is_dir():
        raise SandboxRejected('SNAPSHOT_ROOT_LINK_OR_MISSING')
    files = {}
    total = 0
    for base, dirs, names in os.walk(directory, followlinks=False):
        for name in dirs + names:
            path = Path(base) / name
            if path.is_symlink() or getattr(path.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise SandboxRejected('SNAPSHOT_LINK_FORBIDDEN')
        for name in names:
            path = Path(base) / name
            size = path.stat().st_size
            total += size
            if len(files) >= 3000 or size > 2_000_000 or total > 40 * 1024 * 1024:
                raise SandboxRejected('SNAPSHOT_SIZE_LIMIT')
            files[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


class DockerWSL2Backend:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.config, self.proof = _verified_config(self.root)
        self.executable = Path(self.config['docker_path'])
        if not self.executable.is_absolute() or not self.executable.is_file() or self.executable.name.lower() != 'docker.exe':
            raise SandboxRejected('DOCKER_EXECUTABLE_UNAVAILABLE')
        self.client_config = self.root / 'state/secure_execution/docker-config'
        self.client_config.mkdir(parents=True, exist_ok=True)
        # No context, credential-helper or authentication configuration is copied here.
        if any(self.client_config.iterdir()):
            raise SandboxRejected('ISOLATED_DOCKER_CONFIG_MUST_BE_EMPTY')
        self.env = self.client_environment(self.client_config)

    @staticmethod
    def client_environment(config: Path) -> dict:
        allowed = {k: os.environ[k] for k in ('SystemRoot', 'WINDIR', 'TEMP', 'TMP') if k in os.environ}
        allowed['PATH'] = str(Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'System32')
        allowed['DOCKER_CONFIG'] = str(config)
        return allowed

    def _call(self, *args: str, timeout: float = 20, check: bool = True, binary: bool = False,
              output_limit: int = 1_048_576):
        # Tempfile capture bounds memory and prevents untrusted stdout flooding the app.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen([str(self.executable), '--host', ENDPOINT, *args],
                                       env=self.env, stdout=stdout, stderr=stderr)
            deadline = time.monotonic() + timeout
            try:
                while process.poll() is None:
                    if time.monotonic() >= deadline:
                        raise subprocess.TimeoutExpired(args, timeout)
                    if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > output_limit:
                        raise SandboxRejected('SANDBOX_OUTPUT_CAPTURE_LIMIT')
                    time.sleep(0.05)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
            if os.fstat(stdout.fileno()).st_size + os.fstat(stderr.fileno()).st_size > output_limit:
                raise SandboxRejected('SANDBOX_OUTPUT_CAPTURE_LIMIT')
            stdout.seek(0)
            stderr.seek(0)
            out, err = stdout.read(output_limit), stderr.read(output_limit)
            if check and process.returncode:
                raise SandboxRejected('DOCKER_COMMAND_FAILED_' + args[0] + ':' + err.decode('utf-8', errors='replace')[:300])
            return process.returncode, out if binary else out.decode('utf-8', errors='replace'), err.decode('utf-8', errors='replace')

    def health(self) -> dict:
        _, text, _ = self._call('info', '--format', '{{json .}}')
        info = json.loads(text)
        if info.get('OSType') != 'linux' or 'WSL2' not in info.get('KernelVersion', ''):
            raise SandboxRejected('WSL2_LINUX_BACKEND_REQUIRED')
        for key in ('KernelVersion', 'ServerVersion'):
            if info.get(key) != self.proof['backend'].get(key):
                raise SandboxRejected('BACKEND_CHANGED_REPEAT_CONTAINMENT_TEST')
        if not all(info.get(key) for key in ('MemoryLimit', 'PidsLimit', 'CpuCfsQuota')):
            raise SandboxRejected('RESOURCE_LIMIT_SUPPORT_REQUIRED')
        return {'status': 'HEALTHY', 'backend': BACKEND,
                'server_version': info['ServerVersion'], 'kernel': info['KernelVersion']}

    def prepare(self, spec: ExecutionContract, snapshot: Path, input_text: str, job_id: int) -> Path:
        ExecutionContract.from_dict(spec.to_dict())
        if isinstance(job_id, bool) or not isinstance(job_id, int) or job_id < 1:
            raise SandboxRejected('VALID_JOB_ID_REQUIRED')
        expected = self.root / 'state/activation_work' / str(job_id) / 'source'
        # Reject arbitrary host/project paths before resolving or reading them.
        if Path(snapshot).absolute() != expected.absolute():
            raise SandboxRejected('ONLY_QUARANTINED_JOB_SNAPSHOT_ALLOWED')
        if expected.resolve() != expected.absolute() or not expected.is_dir():
            raise SandboxRejected('SOURCE_SNAPSHOT_LINK_OR_MISSING')
        _tree_hashes(expected)
        if not isinstance(input_text, str) or len(input_text.encode()) > 1_048_576:
            raise SandboxRejected('SYNTHETIC_INPUT_LIMIT')
        base = self.root / 'state/secure_execution/runs'
        base.mkdir(parents=True, exist_ok=True)
        if base.resolve() != base.absolute():
            raise SandboxRejected('WORKSPACE_LINK_FORBIDDEN')
        workspace = base / (f'job-{job_id}-' + uuid.uuid4().hex)
        shutil.copytree(expected, workspace / 'source')
        (workspace / 'input').mkdir()
        (workspace / 'input/payload.txt').write_text(input_text, encoding='utf-8', newline='\n')
        return workspace

    @staticmethod
    def create_arguments(spec: ExecutionContract, name: str, source: Path, inputs: Path) -> list[str]:
        return ['create', '--pull', 'never', '--name', name, '--label', 'techchancellor.secure-execution=true',
                '--network', 'none', '--read-only', '--user', '65534:65534', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges=true', '--pids-limit', str(spec.pids_limit),
                '--memory', f'{spec.memory_mb}m', '--memory-swap', f'{spec.memory_mb}m',
                '--cpus', str(spec.cpus), '--ipc', 'private', '--init',
                '--log-driver', 'none', '--tmpfs', '/tmp:rw,nosuid,nodev,noexec,size=16m,mode=1777',
                '--tmpfs', '/output:rw,nosuid,nodev,noexec,size=16m,mode=1777',
                '--mount', f'type=bind,source={source},target=/candidate,readonly',
                '--mount', f'type=bind,source={inputs},target=/input,readonly',
                '--workdir', '/candidate', '--entrypoint', '/bin/sh', spec.sandbox_image,
                '-c', f'exec sleep {spec.timeout_seconds + 30}']

    def collect_output(self, name: str, expected: tuple[str, ...]) -> dict[str, str]:
        collected = {}
        for filename in expected:
            # Docker's archive API does not expose tmpfs reliably. Stream an
            # allowlisted tar entry; never extract it to the host filesystem.
            _, raw, _ = self._call('exec', '--user', '65534:65534', name,
                                   '/bin/tar', '-C', '/output', '-cf', '-', '--', filename,
                                   binary=True, output_limit=262_144)
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
                members = archive.getmembers()
                if len(members) != 1 or not members[0].isfile() or members[0].name != filename or members[0].size > 65_536:
                    raise SandboxRejected('EXPECTED_OUTPUT_NOT_BOUNDED_REGULAR_FILE')
                collected[filename] = archive.extractfile(members[0]).read(65_537).decode('utf-8', errors='strict')
        return collected

    def teardown(self, name: str) -> None:
        self._call('rm', '-f', name, check=False)
        code, _, error = self._call('inspect', name, check=False)
        if code == 0 or 'no such' not in error.lower():
            raise SandboxRejected('SANDBOX_TEARDOWN_FAILED')

    def run(self, spec: ExecutionContract, workspace: Path) -> dict:
        spec = ExecutionContract.from_dict(spec.to_dict())
        base = self.root / 'state/secure_execution/runs'
        if workspace.absolute().parent != base.absolute() or workspace.resolve() != workspace.absolute():
            raise SandboxRejected('EXECUTION_WORKSPACE_OUTSIDE_ALLOWLIST')
        source, inputs = workspace / 'source', workspace / 'input'
        before = (_tree_hashes(source), _tree_hashes(inputs))
        name = 'pti-eval-' + uuid.uuid4().hex
        result = {'sandbox_backend': BACKEND, 'sandbox_image': spec.sandbox_image,
                  'source_pin': spec.source_pin, 'network_policy': 'NONE', 'timed_out': False,
                  'host_writable_mounts': 0, 'output_storage': 'BOUNDED_EPHEMERAL_TMPFS'}
        created = False
        started = time.monotonic()
        try:
            self.health()
            if spec.sandbox_image not in self.config['approved_images']:
                raise SandboxRejected('IMAGE_NOT_APPROVED')
            created = True
            self._call(*self.create_arguments(spec, name, source, inputs))
            _, raw, _ = self._call('inspect', name)
            metadata = json.loads(raw)[0]
            mounts, hc = metadata['Mounts'], metadata['HostConfig']
            if ({m['Destination']: m['RW'] for m in mounts} != {'/candidate': False, '/input': False}
                    or len(mounts) != 2 or {m['Source'].lower() for m in mounts} != {str(source).lower(), str(inputs).lower()}
                    or hc['Privileged'] or hc['NetworkMode'] != 'none' or not hc['ReadonlyRootfs']
                    or hc.get('PidMode') or hc['IpcMode'] != 'private' or hc.get('Devices') or hc.get('DeviceRequests')
                    or hc['CapDrop'] != ['ALL'] or hc['SecurityOpt'] != ['no-new-privileges=true']
                    or hc['Memory'] != spec.memory_mb * 1024 * 1024 or hc['PidsLimit'] != spec.pids_limit
                    or hc['NanoCpus'] != int(spec.cpus * 1_000_000_000)
                    or metadata['Config']['User'] != '65534:65534'):
                raise SandboxRejected('ACTUAL_CONTAINER_PROFILE_MISMATCH')
            self._call('start', name)
            command = ['exec', '--user', '65534:65534', name, '/bin/sh', '-c',
                       'exec "$@" > /tmp/pti-stdout 2> /tmp/pti-stderr', '--', '/usr/bin/env', '-i',
                       'PATH=/usr/local/bin:/usr/bin:/bin', 'HOME=/tmp', 'LANG=C.UTF-8',
                       'PYTHONDONTWRITEBYTECODE=1', *spec.command]
            try:
                code, _, _ = self._call(*command, timeout=spec.timeout_seconds, check=False)
                result['exit_code'] = code
            except subprocess.TimeoutExpired:
                result.update(timed_out=True, exit_code=None)
                return result
            if code == 0:
                result['outputs'] = self.collect_output(name, spec.expected_outputs)
            result['filesystem_input_unchanged'] = before == (_tree_hashes(source), _tree_hashes(inputs))
            if not result['filesystem_input_unchanged']:
                raise SandboxRejected('READONLY_INPUT_CHANGED')
            return result
        finally:
            try:
                if created:
                    self.teardown(name)
                    result['cleanup'] = 'CONTAINER_DESTROYED'
            finally:
                result['duration_seconds'] = round(time.monotonic() - started, 3)
                if workspace.absolute().parent == base.absolute():
                    shutil.rmtree(workspace)


def register_verified_backend(root: str | Path, db) -> dict:
    """Explicit local registration after real evidence and live engine validation."""
    from .capability_intelligence import CapabilityStore
    backend = DockerWSL2Backend(root)
    health = backend.health()
    store = CapabilityStore(db.path)
    capability = 'SECURE_THIRD_PARTY_EXECUTION_SANDBOX'
    store.upsert_capability(capability, '安全第三方执行沙箱', '已验证的一次性离线隔离执行；不覆盖平台逃逸漏洞')
    with db._connect() as connection:
        connection.execute("DELETE FROM personal_states WHERE subject_type='CAPABILITY' AND subject_id=? AND state='MISSING_CAPABILITY'", (capability,))
    for state in ('VERIFIED', 'AVAILABLE'):
        store.set_personal_state('CAPABILITY', capability, state, 'host-containment:' + backend.proof['run_id'])
    return health
