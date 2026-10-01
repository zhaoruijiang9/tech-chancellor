"""Bounded executable adapter helpers used by the existing activation worker."""

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from .secure_execution import DockerWSL2Backend, ExecutionContract, SandboxRejected, _tree_hashes
from .static_analysis import analyze_tree


ADAPTER = 'DOCKER_BOUNDED_OFFLINE'


def load_execution_plan(root: Path, repository_id: int) -> dict | None:
    path = root / 'state/secure_execution/plans' / f'repo-{repository_id}.json'
    if not path.exists():
        return None
    if path.resolve() != path.absolute() or path.stat().st_size > 100_000:
        raise SandboxRejected('LOCAL_PLAN_LINK_OR_SIZE_LIMIT')
    return validate_plan(json.loads(path.read_text(encoding='utf-8')))


def validate_plan(plan: dict) -> dict:
    if not isinstance(plan, dict) or set(plan) != {'execution', 'target_capability', 'evaluation'}:
        raise SandboxRejected('EXPLICIT_BOUNDED_EXECUTION_PLAN_REQUIRED')
    spec = ExecutionContract.from_dict(plan['execution'])
    if plan['target_capability'] != 'CONTEXT_COMPRESSION':
        raise SandboxRejected('NO_EXECUTABLE_EVALUATOR_FOR_TARGET_CAPABILITY')
    evaluation = plan['evaluation']
    if not isinstance(evaluation, dict) or set(evaluation) != {'kind', 'input_text', 'required_facts', 'minimum_reduction'}:
        raise SandboxRejected('EXPLICIT_SYNTHETIC_EVALUATION_REQUIRED')
    text, facts, minimum = evaluation['input_text'], evaluation['required_facts'], evaluation['minimum_reduction']
    if (evaluation['kind'] != 'BOUNDED_TEXT_COMPRESSION' or not isinstance(text, str)
            or not 20 <= len(text.encode('utf-8')) <= 65_536
            or not isinstance(facts, list) or not 1 <= len(facts) <= 20
            or any(not isinstance(f, str) or not f or len(f) > 200 or f not in text for f in facts)
            or isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not 0.1 <= minimum <= 0.9
            or len(spec.expected_outputs) != 1):
        raise SandboxRejected('INVALID_BOUNDED_TEXT_EVALUATION')
    return {**plan, 'execution': spec.to_dict()}


def plan_digest(plan: dict) -> str:
    return hashlib.sha256(json.dumps(validate_plan(plan), sort_keys=True).encode()).hexdigest()


def extract_reviewed_source(payload: bytes, scope: Path) -> dict:
    # Existing archive validator runs first. This adds Windows filename and
    # full-source restrictions before any candidate file is written.
    from .activation_worker import safe_readme_from_archive
    safe_readme_from_archive(payload)
    scope = scope.absolute()
    if scope.resolve() != scope or scope.name != 'source':
        raise SandboxRejected('SOURCE_SCOPE_LINK_FORBIDDEN')
    contents = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        prefix = None
        for member in archive.infolist():
            path = PurePosixPath(member.filename.replace('\\', '/'))
            if not path.parts:
                raise SandboxRejected('EMPTY_ARCHIVE_PATH')
            prefix = prefix or path.parts[0]
            if path.parts[0] != prefix:
                raise SandboxRejected('SINGLE_SOURCE_ROOT_REQUIRED')
            for part in path.parts:
                if (part.lower() in {'.', '..', '.git'} or not re.fullmatch(r'[A-Za-z0-9_.+@ ()-]+', part)
                        or part.endswith((' ', '.')) or part.split('.')[0].upper() in
                        {'CON', 'PRN', 'AUX', 'NUL', *('COM'+str(i) for i in range(1, 10)),
                         *('LPT'+str(i) for i in range(1, 10))}):
                    raise SandboxRejected('UNSAFE_WINDOWS_ARCHIVE_PATH')
            if member.is_dir():
                continue
            if len(path.parts) < 2 or member.file_size > 200_000:
                raise SandboxRejected('BOUNDED_FULL_STATIC_REVIEW_REQUIRED')
            relative = PurePosixPath(*path.parts[1:]).as_posix()
            if relative.lower() in {key.lower() for key in contents}:
                raise SandboxRejected('DUPLICATE_ARCHIVE_PATH')
            raw = archive.read(member)
            try:
                raw.decode('utf-8', errors='strict')
            except UnicodeError as error:
                raise SandboxRejected('V01_TEXT_SOURCE_ONLY_NO_OPAQUE_BINARIES') from error
            contents[relative] = raw
    scope.mkdir(parents=True, exist_ok=True)
    expected = {key: hashlib.sha256(raw).hexdigest() for key, raw in contents.items()}
    existing = _tree_hashes(scope)
    if existing and existing != expected:
        raise SandboxRejected('REVIEWED_SOURCE_CONFLICT')
    for relative, raw in contents.items():
        path = scope / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    analysis = analyze_tree(scope)
    forbidden = {'symlink', 'oversized_file', 'credential_access', 'service_install',
                 'privilege_escalation', 'protected_path', 'postinstall', 'malformed_manifest'}
    if set(analysis['findings']) & forbidden:
        raise SandboxRejected('EXECUTABLE_STATIC_REVIEW_REQUIRES_HUMAN')
    analysis.update(reviewed_surface='entire bounded UTF-8 source snapshot', source_hashes=expected,
                    upstream_code_executed=False, documentation_commands_executed=False)
    return analysis


def functional_execution(root: Path, job_id: int, contract: dict, review: dict) -> tuple[dict, dict]:
    plan = validate_plan(contract['execution_plan'])
    if plan_digest(plan) != contract['execution_plan_sha256']:
        raise SandboxRejected('EXECUTION_PLAN_INTEGRITY_FAILURE')
    spec = ExecutionContract.from_dict(plan['execution'])
    source = root / 'state/activation_work' / str(job_id) / 'source'
    if source.resolve() != source.absolute() or _tree_hashes(source) != review['source_hashes']:
        raise SandboxRejected('SOURCE_CHANGED_AFTER_STATIC_REVIEW')
    backend = DockerWSL2Backend(root)
    workspace = backend.prepare(spec, source, plan['evaluation']['input_text'], job_id)
    result = backend.run(spec, workspace)
    if (result.get('timed_out') or result.get('exit_code') != 0
            or result.get('cleanup') != 'CONTAINER_DESTROYED' or not result.get('filesystem_input_unchanged')):
        raise SandboxRejected('SANDBOX_FUNCTIONAL_EXECUTION_FAILED')
    output = result.pop('outputs')[spec.expected_outputs[0]]
    task = plan['evaluation']
    if not all(fact in output for fact in task['required_facts']):
        raise SandboxRejected('REQUIRED_SYNTHETIC_FACTS_NOT_RETAINED')
    baseline, candidate = len(task['input_text'].encode()), len(output.encode())
    reduction = 1 - candidate / baseline
    evaluation = {'outcome': 'IMPROVED' if reduction >= task['minimum_reduction'] else 'NO_MEANINGFUL_DELTA',
                  'metric': 'UTF8_BYTES_WITH_REQUIRED_LITERAL_FACT_RETENTION', 'baseline_bytes': baseline,
                  'candidate_bytes': candidate, 'reduction_ratio': round(reduction, 6),
                  'required_facts_retained': len(task['required_facts']),
                  'scope': 'single synthetic task only; no general semantic quality claim'}
    result.update(output_sha256=hashlib.sha256(output.encode()).hexdigest(), upstream_code_executed=True)
    return result, evaluation
