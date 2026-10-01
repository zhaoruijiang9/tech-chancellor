"""Bounded, resumable activation of explicitly supported low-risk capabilities."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from .activation_policy import TIER_1, TIER_2, evaluate_activation_policy, evaluate_validation_eligibility, transition_activation
from .execution_adapter import ADAPTER, load_execution_plan, plan_digest, extract_reviewed_source, functional_execution
from .secure_execution import DockerWSL2Backend, SandboxRejected, _tree_hashes
from .capability_intelligence import project_activation_state, revoke_activation_availability
from .quarantine import quarantine_public_repo_archive
from .runtime_lock import CrashSafeLock, LockState
from .static_analysis import analyze_tree

MAX_ARCHIVE_BYTES = 12 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 40 * 1024 * 1024
MAX_ARCHIVE_FILES = 3000
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
LINK = re.compile(r"(?m)^\s*[-*]\s+\[([^\]]{1,120})\]\((https://github\.com/[^\s)]+)\)")
EVALUATION_QUERIES = ("pdf", "pptx", "xlsx")


class HumanGate(Exception):
    pass


class TerminalFailure(Exception):
    pass


class GitHubSourceProvider:
    def pin(self, owner_repo: str) -> str:
        if not REPO.fullmatch(owner_repo):
            raise HumanGate("INVALID_GITHUB_REPOSITORY")
        completed = subprocess.run(
            ["git", "-c", "credential.helper=", "-c", "core.askPass=", "ls-remote",
             f"https://github.com/{owner_repo}.git", "HEAD"],
            capture_output=True, text=True, timeout=30, check=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"},
        )
        if completed.returncode != 0:
            raise OSError("GITHUB_PIN_UNAVAILABLE")
        parts = completed.stdout.strip().split()
        sha = parts[0].lower() if len(parts) == 2 and parts[1] == "HEAD" else ""
        if not SHA.fullmatch(sha):
            raise OSError("GITHUB_PIN_INVALID")
        return sha

    def fetch(self, owner_repo: str, sha: str) -> bytes:
        if not REPO.fullmatch(owner_repo) or not SHA.fullmatch(sha):
            raise HumanGate("INVALID_PINNED_SOURCE")
        request = urllib.request.Request(
            f"https://codeload.github.com/{owner_repo}/zip/{sha}",
            headers={"User-Agent": "TechChancellor-activation/1"},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.status != 200:
                raise OSError("GITHUB_ARCHIVE_UNAVAILABLE")
            payload = response.read(MAX_ARCHIVE_BYTES + 1)
        if len(payload) > MAX_ARCHIVE_BYTES:
            raise TerminalFailure("ARCHIVE_SIZE_LIMIT")
        return payload


def safe_readme_from_archive(payload: bytes) -> tuple[str, dict]:
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("ARCHIVE_SIZE_LIMIT")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
        members = archive.infolist()
        if len(members) > MAX_ARCHIVE_FILES or sum(member.file_size for member in members) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("ARCHIVE_EXPANSION_LIMIT")
        readmes = []
        for member in members:
            path = Path(member.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts or ":" in member.filename:
                raise ValueError("ARCHIVE_PATH_TRAVERSAL")
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ARCHIVE_SYMLINK")
            if len(path.parts) == 2 and path.name.lower() == "readme.md" and member.file_size <= 2_000_000:
                readmes.append(member)
        if len(readmes) != 1:
            raise ValueError("ROOT_README_NOT_UNIQUE")
        text = archive.read(readmes[0]).decode("utf-8", errors="strict")
        return text, {"archive_file_count": len(members), "readme_path": readmes[0].filename,
                      "readme_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    except (zipfile.BadZipFile, UnicodeError) as error:
        raise ValueError("INVALID_ARCHIVE_OR_README") from error


def index_entries(text: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for name, url in LINK.findall(text):
        if not ("/tree/" in url or "/blob/" in url or "-skill" in url.lower()):
            continue
        url = url.rstrip("/.,")
        if url in seen:
            continue
        seen.add(url)
        entries.append({"name": name.strip(), "url": url})
    return entries


def _version_root(root: Path, repository_id: int, sha: str) -> Path:
    return root / "managed_capabilities" / f"repo-{repository_id}" / "versions" / sha


def _active_pointer(root: Path, repository_id: int) -> Path:
    return root / "managed_capabilities" / f"repo-{repository_id}" / "active.json"


def _search_file(path: Path, query: str) -> list[dict[str, str]]:
    term = query.strip().lower()
    if not term or len(term) > 100:
        return []
    return [entry for entry in index_entries(path.read_text(encoding="utf-8"))
            if term in entry["name"].lower()][:20]


def search_active_index(root: str | Path, query: str, repository_id: int | None = None) -> list[dict[str, str]]:
    root = Path(root).resolve()
    bases = ([root / "managed_capabilities" / f"repo-{repository_id}"] if repository_id is not None
             else sorted((root / "managed_capabilities").glob("repo-*")))
    matches = []
    for base in bases:
        pointer = base / "active.json"
        if not pointer.is_file():
            continue
        try:
            sha = json.loads(pointer.read_text(encoding="utf-8"))["sha"]
        except (OSError, KeyError, json.JSONDecodeError):
            continue
        if not SHA.fullmatch(str(sha)):
            continue
        readme = base / "versions" / sha / "README.md"
        if readme.is_file():
            matches.extend(_search_file(readme, query))
    return matches[:20]


def _contract(db, repository_id: int, job_id: int, root: Path) -> dict:
    repository = db.get_repository(repository_id)
    if repository is None or not REPO.fullmatch(repository.canonical_owner_repo):
        raise HumanGate("SOURCE_NOT_FOUND_OR_INVALID")
    feedback = db.get_feedback(repository_id)
    if feedback and feedback[-1]["label"] in {"WATCH", "NOT_USEFUL", "TOO_RISKY"}:
        raise HumanGate("OWNER_FEEDBACK_PREVENTS_AUTO_ACTIVATION")
    plan = load_execution_plan(root, repository_id)
    if plan is not None:
        existing = db.get_activation(repository_id) or {}
        if (any(marker in repository.canonical_owner_repo.lower() for marker in
                ('trading', 'backtesting-engine', 'minecontext'))
                or repository.previous_decision not in {'REFERENCE_ONLY', 'WATCH', 'CANDIDATE_FOR_QUARANTINE'}
                or existing.get('activation_state') in {'BLOCKED_HUMAN', 'FAILED_WITH_EXPLAINED_REASON'}
                or existing.get('activation_tier') not in {None, TIER_1, TIER_2, 'TIER_0_KNOWLEDGE_PATTERN'}):
            raise HumanGate('EXECUTABLE_CANDIDATE_BOUNDARY_PREVENTS_ACTIVATION')
        with db._connect() as connection:
            row = connection.execute('''SELECT i.implementation_id,s.source_id
                FROM capability_implementations i JOIN capability_sources s USING(source_id)
                JOIN implementation_capabilities m USING(implementation_id)
                WHERE s.github_repository_id=? AND m.capability_id=?''',
                (repository_id, plan['target_capability'])).fetchone()
        if row is None:
            raise HumanGate('REVIEWED_EXECUTABLE_CAPABILITY_MAPPING_REQUIRED')
        DockerWSL2Backend(root).health()
        return {'implementation_id': row['implementation_id'], 'source_id': row['source_id'],
                'target_capability': plan['target_capability'], 'source_url': repository.url,
                'source_version': plan['execution']['source_pin'], 'adapter': ADAPTER,
                'activation_tier': TIER_2, 'execution_plan': plan, 'execution_plan_sha256': plan_digest(plan),
                'fetch_strategy': 'GITHUB_COMMIT_ARCHIVE', 'install_strategy': 'PINNED_SOURCE_DATA_ONLY',
                'dependency_behavior': 'NONE_HOST_OR_RUNTIME', 'network_requirements': 'FETCH_ONLY',
                'credential_requirements': 'NONE', 'service_behavior': 'NONE',
                'filesystem_scope': 'RO_CANDIDATE_RO_SYNTHETIC_INPUT_TMPFS_OUTPUT',
                'environment_allowlist': ['PATH', 'HOME', 'LANG', 'PYTHONDONTWRITEBYTECODE'],
                'rollback_strategy': 'RESTORE_PREVIOUS_ACTIVE_POINTER'}
    with db._connect() as connection:
        rows = connection.execute("""SELECT i.implementation_id,s.source_id,m.capability_id
            FROM capability_implementations i JOIN capability_sources s ON s.source_id=i.source_id
            JOIN implementation_capabilities m ON m.implementation_id=i.implementation_id
            JOIN personal_states p ON p.subject_type='IMPLEMENTATION' AND p.subject_id=i.implementation_id
            WHERE s.github_repository_id=? AND p.state='WATCHLIST'
            AND m.capability_id='SKILL_ECOSYSTEM_DISCOVERY'""", (repository_id,)).fetchall()
    if not rows:
        raise HumanGate("WATCHLIST_IMPLEMENTATION_MAPPING_REQUIRED")
    capabilities = {row["capability_id"] for row in rows}
    if "SKILL_ECOSYSTEM_DISCOVERY" not in capabilities:
        raise HumanGate("EXECUTABLE_ADAPTER_REQUIRES_OS_SANDBOX")
    if repository.previous_decision not in {"REFERENCE_ONLY", "WATCH", "CANDIDATE_FOR_QUARANTINE", "USER_REVIEW_RECOMMENDED"}:
        raise HumanGate("UNREVIEWED_SOURCE_DECISION")
    implementation = rows[0]
    return {
        "implementation_id": implementation["implementation_id"], "source_id": implementation["source_id"],
        "target_capability": "SKILL_ECOSYSTEM_DISCOVERY", "source_url": repository.url,
        "source_version": None, "fetch_strategy": "GITHUB_COMMIT_ARCHIVE",
        "install_strategy": "PINNED_README_INDEX_ONLY", "adapter": "READ_ONLY_MARKDOWN_INDEX",
        "quarantine_path": str(root / "quarantine" / "activation" / str(job_id)),
        "managed_install_path": str(root / "managed_capabilities" / f"repo-{repository_id}"),
        "dependency_behavior": "NONE", "network_requirements": "FETCH_ONLY", "credential_requirements": "NONE",
        "service_behavior": "NONE", "filesystem_scope": "OWN_MANAGED_DIRECTORY_ONLY",
        "rollback_strategy": "RESTORE_PREVIOUS_ACTIVE_POINTER", "functional_test": "BOUNDED_LOCAL_INDEX_SEARCH",
        "evaluation_task": {"queries": list(EVALUATION_QUERIES), "metric": "unique_direct_source_links"},
    }


def _record(db, repository_id: int, tier: str, state: str, **changes) -> None:
    existing = db.get_activation(repository_id) or {}
    db.upsert_activation({**existing, "github_repository_id": repository_id, "activation_tier": tier,
                          "activation_state": state, **changes})


def _rollback_test(pointer: Path, sha: str) -> dict:
    pointer.parent.mkdir(parents=True, exist_ok=True)
    previous = pointer.read_bytes() if pointer.exists() else None
    trial = pointer.with_name("rollback-test.json")
    trial.write_text(json.dumps({"sha": sha}), encoding="utf-8")
    if json.loads(trial.read_text(encoding="utf-8"))["sha"] != sha:
        raise TerminalFailure("ACTIVE_POINTER_WRITE_FAILED")
    if previous is None:
        trial.unlink()
    else:
        trial.write_bytes(previous)
    if (trial.read_bytes() if trial.exists() else None) != previous:
        raise TerminalFailure("ROLLBACK_TEST_FAILED")
    trial.unlink(missing_ok=True)
    return {"strategy": "RESTORE_PREVIOUS_ACTIVE_POINTER", "tested": True,
            "previous_pointer_sha256": hashlib.sha256(previous).hexdigest() if previous else None}


def _promote_pointer(pointer: Path, sha: str, job_id: int) -> Path:
    receipts = pointer.parent / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    previous_path = receipts / f"{job_id}.previous-active.json"
    if not previous_path.exists():
        previous_tmp = previous_path.with_suffix(".tmp")
        previous_tmp.write_bytes(pointer.read_bytes() if pointer.exists() else b"")
        previous_tmp.replace(previous_path)
    temporary = pointer.with_name("active.pending.json")
    temporary.write_text(json.dumps({"sha": sha, "activation_job_id": job_id}), encoding="utf-8")
    temporary.replace(pointer)
    return previous_path


def rollback_activation(root: str | Path, repository_id: int, job_id: int, *, db) -> dict:
    with db._connect() as connection:
        job = connection.execute("SELECT repository_id FROM activation_queue WHERE id=?", (job_id,)).fetchone()
    if job is None or job["repository_id"] != repository_id:
        raise ValueError("rollback job does not belong to this repository")
    pointer = _active_pointer(Path(root).resolve(), repository_id)
    previous = None
    if pointer.is_file():
        active = json.loads(pointer.read_text(encoding="utf-8"))
        if active.get("activation_job_id") != job_id:
            raise ValueError("a newer activation owns the active pointer")
        previous_path = pointer.parent / "receipts" / f"{job_id}.previous-active.json"
        if not previous_path.is_file():
            raise ValueError("rollback receipt missing")
        previous = previous_path.read_bytes()
        if previous:
            temporary = pointer.with_name("active.rollback.json")
            temporary.write_bytes(previous)
            temporary.replace(pointer)
        else:
            pointer.unlink()
    record = db.get_activation(repository_id)
    if record and record["activation_state"] in {"TRIAL_ENABLED", "USED"}:
        transition_activation(db, repository_id, "ROLLED_BACK")
        _record(db, repository_id, record["activation_tier"], "ROLLED_BACK", trial_status="DISABLED")
        revoke_activation_availability(db.path, repository_id)
    return {"status": "ROLLED_BACK", "previous_pointer_restored": bool(previous)}


def _evaluate(root: Path, repository_id: int, readme: Path) -> dict:
    candidate = {item["url"] for query in EVALUATION_QUERIES for item in _search_file(readme, query)}
    baseline = {item["url"] for query in EVALUATION_QUERIES for item in search_active_index(root, query, repository_id)}
    gained = candidate - baseline
    outcome = "IMPROVED" if len(gained) >= 2 else "NO_MEANINGFUL_DELTA"
    return {"outcome": outcome, "queries": list(EVALUATION_QUERIES), "baseline_links": len(baseline),
            "candidate_links": len(candidate), "new_links": len(gained),
            "scope": "direct skill-source discovery only; linked skills are not trusted or installed"}


def _advance(root: Path, db, job: dict, provider) -> dict:
    job_id, repository_id = job["id"], job["repository_id"]
    if any(code in job["reason"] for code in ("CREDENTIAL_REQUIRED", "ADMIN_REQUIRED", "TRADING_SCOPE",
          "SERVICE_REQUIRED", "PERSISTENT_NETWORK_LISTENER", "SYSTEM_MODIFICATION_REQUIRED",
          "PATH_MODIFICATION_REQUIRED", "BROWSER_EXTENSION_REQUIRED", "PROTECTED_PROJECT")):
        raise HumanGate("QUEUED_HAZARD_REQUIRES_HUMAN")
    phase = job["phase"]
    evidence = json.loads(job["evidence_json"] or "{}")
    contract = json.loads(job["contract_json"] or "{}")
    executable = contract.get('adapter') == ADAPTER
    tier = TIER_2 if executable else TIER_1
    if executable:
        current = _contract(db, repository_id, job_id, root)
        if (current['execution_plan_sha256'] != contract.get('execution_plan_sha256')
                or contract.get('source_version') != current['source_version']):
            raise HumanGate('EXECUTION_PLAN_CHANGED_ON_RESUME')
    repository = db.get_repository(repository_id)
    if phase == "EVALUATION_NO_DELTA":
        raise TerminalFailure("NO_MEANINGFUL_DELTA")
    if phase == "AVAILABLE":
        pointer = _active_pointer(root, repository_id)
        if not pointer.is_file() or json.loads(pointer.read_text(encoding="utf-8")).get("activation_job_id") != job_id:
            raise TerminalFailure("AVAILABLE_POINTER_MISSING")
        if executable and _tree_hashes(_version_root(root, repository_id, contract['source_version']) / 'source') != evidence['static_review']['source_hashes']:
            raise SandboxRejected('MANAGED_SOURCE_CHANGED_AFTER_REVIEW')
        _record(db, repository_id, tier, "TRIAL_ENABLED", trial_status="ENABLED_CONTROLLED",
                evidence_maturity="TESTED", rollback_status="READY", isolated_test_status="PASS")
        project_activation_state(db.path, repository_id, "AVAILABLE", f"activation-job:{job_id}:evaluation")
        db.complete_activation(job_id, "SUCCEEDED")
        return {"repository_id": repository_id, "status": "SUCCEEDED", "phase": "AVAILABLE"}
    if phase == "QUEUED":
        contract = _contract(db, repository_id, job_id, root)
        executable = contract.get('adapter') == ADAPTER
        tier = TIER_2 if executable else TIER_1
        gate = evaluate_validation_eligibility({"activation_tier": tier})
        if not gate.eligible:
            raise HumanGate("AUTO_VALIDATION_NOT_ELIGIBLE")
        previous = db.get_activation(repository_id)
        job = db.update_activation_job(job_id, "PLAN_READY", {"prior_activation": previous}, contract)
        _record(db, repository_id, tier, "QUARANTINE_READY", notes="Pinned bounded adapter validation in progress")
        phase = "PLAN_READY"
    if phase == "PLAN_READY":
        sha = contract['source_version'] if executable else provider.pin(repository.canonical_owner_repo)
        if not SHA.fullmatch(sha):
            raise TerminalFailure("INVALID_PIN")
        contract["source_version"] = sha
        job = db.update_activation_job(job_id, "SOURCE_PINNED", {"pin": sha}, contract)
        phase = "SOURCE_PINNED"
    sha = contract.get("source_version") or evidence.get("pin")
    if phase == "SOURCE_PINNED":
        if not SHA.fullmatch(str(sha)):
            raise TerminalFailure("PIN_MISSING_ON_RESUME")
        archive_root = root / "quarantine" / "activation" / str(job_id)
        archive_path = archive_root / (repository.canonical_owner_repo.replace("/", "--") + ".archive")
        manifest_path = archive_path.with_suffix(archive_path.suffix + ".json")
        if archive_path.is_file() and not manifest_path.is_file():
            archive_path.unlink()
        if archive_path.is_file():
            payload = archive_path.read_bytes()
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if hashlib.sha256(payload).hexdigest() != manifest.get("sha256") or manifest.get("commit_sha") != sha:
                raise TerminalFailure("QUARANTINE_INTEGRITY_FAILURE")
        else:
            payload = provider.fetch(repository.canonical_owner_repo, sha)
            safe_readme_from_archive(payload)
            manifest = quarantine_public_repo_archive(archive_root,
                f"https://github.com/{repository.canonical_owner_repo}/archive/{sha}.zip",
                repository_id, repository.canonical_owner_repo, sha, payload)
        job = db.update_activation_job(job_id, "QUARANTINED", {"quarantine": manifest})
        _record(db, repository_id, tier, "QUARANTINED", pinned_version=sha)
        phase = "QUARANTINED"
    if phase == "QUARANTINED":
        _record(db, repository_id, tier, "QUARANTINED", pinned_version=sha)
        manifest = json.loads(job["evidence_json"])["quarantine"]
        archive_path = Path(manifest["path"])
        expected_archive = root / 'quarantine/activation' / str(job_id) / (repository.canonical_owner_repo.replace('/', '--') + '.archive')
        if archive_path.absolute() != expected_archive.absolute() or archive_path.resolve() != archive_path.absolute():
            raise HumanGate('QUARANTINE_PATH_OUTSIDE_JOB_ALLOWLIST')
        payload = archive_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != manifest["sha256"]:
            raise TerminalFailure("QUARANTINE_INTEGRITY_FAILURE")
        text, inventory = safe_readme_from_archive(payload)
        scope = root / "state" / "activation_work" / str(job_id)
        scope.mkdir(parents=True, exist_ok=True)
        (scope / "README.md").write_text(text, encoding="utf-8")
        analysis = extract_reviewed_source(payload, scope / 'source') if executable else analyze_tree(scope)
        if set(analysis["findings"]) & {"symlink", "oversized_file", "credential_access", "service_install",
                                         "privilege_escalation", "protected_path"}:
            raise HumanGate("STATIC_REVIEW_REQUIRES_HUMAN")
        entries = index_entries(text)
        if not executable and len(entries) < 3:
            raise TerminalFailure("INSUFFICIENT_DIRECT_SKILL_LINKS")
        analysis.update(inventory)
        analysis.update({"reviewed_surface": analysis.get('reviewed_surface', "root README.md only"), "indexed_links": len(entries),
                         "upstream_code_executed": False,
                         "documentation_commands_executed": False})
        job = db.update_activation_job(job_id, "STATIC_ANALYSIS_PASS", {"static_review": analysis})
        _record(db, repository_id, tier, "STATIC_ANALYSIS_PASS", pinned_version=sha,
                static_analysis_status="PASS", notes="Static review passed; execution remains adapter-gated")
        phase = "STATIC_ANALYSIS_PASS"
    if phase == "STATIC_ANALYSIS_PASS":
        _record(db, repository_id, tier, "STATIC_ANALYSIS_PASS", pinned_version=sha,
                static_analysis_status="PASS")
        version = _version_root(root, repository_id, sha)
        if version.resolve() != version.absolute():
            raise HumanGate('MANAGED_VERSION_LINK_FORBIDDEN')
        version.mkdir(parents=True, exist_ok=True)
        text, _ = safe_readme_from_archive(Path(json.loads(job["evidence_json"])["quarantine"]["path"]).read_bytes())
        readme = version / "README.md"
        if readme.exists() and readme.read_text(encoding="utf-8") != text:
            raise TerminalFailure("MANAGED_VERSION_CONFLICT")
        readme.write_text(text, encoding="utf-8")
        if executable:
            source = root / 'state/activation_work' / str(job_id) / 'source'
            review = json.loads(job['evidence_json'])['static_review']
            if _tree_hashes(source) != review['source_hashes']:
                raise SandboxRejected('SOURCE_CHANGED_AFTER_STATIC_REVIEW')
            destination = version / 'source'
            if destination.exists() and _tree_hashes(destination) != review['source_hashes']:
                raise SandboxRejected('MANAGED_SOURCE_CONFLICT')
            shutil.copytree(source, destination, dirs_exist_ok=True)
        rollback = _rollback_test(_active_pointer(root, repository_id), sha)
        job = db.update_activation_job(job_id, "ISOLATED_INSTALL_PASS", {
            "install": {"path": str(version), "strategy": "DATA_ONLY_NO_DEPENDENCIES"}, "rollback": rollback})
        _record(db, repository_id, tier, "STATIC_ANALYSIS_PASS", rollback_status="READY")
        phase = "ISOLATED_INSTALL_PASS"
    if phase == "ISOLATED_INSTALL_PASS":
        _record(db, repository_id, tier, "STATIC_ANALYSIS_PASS", rollback_status="READY")
        readme = _version_root(root, repository_id, sha) / "README.md"
        if executable:
            functional, evaluation = functional_execution(root, job_id, contract,
                                                        json.loads(job['evidence_json'])['static_review'])
            functional_evidence = {'functional': functional, 'evaluation': evaluation}
        else:
            sample = index_entries(readme.read_text(encoding="utf-8"))[0]["name"]
            hits = _search_file(readme, sample)
            if not hits:
                raise TerminalFailure("FUNCTIONAL_SEARCH_FAILED")
            functional_evidence = {'functional': {'query': sample, 'hits': len(hits), 'upstream_code_executed': False}}
        job = db.update_activation_job(job_id, "FUNCTIONAL_TEST_PASS", functional_evidence)
        _record(db, repository_id, tier, "ISOLATED_TEST_PASS", isolated_test_status="PASS",
                evidence_maturity="TESTED")
        project_activation_state(db.path, repository_id, "VERIFIED", f"activation-job:{job_id}:functional")
        phase = "FUNCTIONAL_TEST_PASS"
    if phase == "FUNCTIONAL_TEST_PASS":
        _record(db, repository_id, tier, "ISOLATED_TEST_PASS", rollback_status="READY",
                isolated_test_status="PASS", evidence_maturity="TESTED")
        project_activation_state(db.path, repository_id, "VERIFIED", f"activation-job:{job_id}:functional")
        evaluation = (json.loads(job['evidence_json'])['evaluation'] if executable else
                      _evaluate(root, repository_id, _version_root(root, repository_id, sha) / "README.md"))
        job = db.update_activation_job(job_id, "EVALUATION_PASS" if evaluation["outcome"] == "IMPROVED" else "EVALUATION_NO_DELTA",
                                       {"evaluation": evaluation})
        if evaluation["outcome"] != "IMPROVED":
            raise TerminalFailure("NO_MEANINGFUL_DELTA")
        phase = "EVALUATION_PASS"
    if phase == "EVALUATION_PASS":
        _record(db, repository_id, tier, "ISOLATED_TEST_PASS", rollback_status="READY",
                isolated_test_status="PASS", evidence_maturity="TESTED")
        evidence = json.loads(job["evidence_json"])
        policy = evaluate_activation_policy({"activation_tier": tier, "pinned_version": sha,
            "rollback_available": evidence.get("rollback", {}).get("tested")},
            {"static_analysis_pass": True, "isolated_test_pass": True,
             "capability_delta": evidence["evaluation"]["outcome"] == "IMPROVED"})
        if not policy.eligible:
            raise HumanGate("AUTO_PROMOTION_NOT_ELIGIBLE")
        if executable:
            DockerWSL2Backend(root).health()
            if evidence['functional'].get('cleanup') != 'CONTAINER_DESTROYED':
                raise HumanGate('CLEANUP_REQUIRED_BEFORE_PROMOTION')
            if _tree_hashes(_version_root(root, repository_id, sha) / 'source') != evidence['static_review']['source_hashes']:
                raise SandboxRejected('MANAGED_SOURCE_CHANGED_AFTER_REVIEW')
        pointer = _active_pointer(root, repository_id)
        previous_path = _promote_pointer(pointer, sha, job_id)
        _record(db, repository_id, tier, "TRIAL_ENABLED", trial_status="ENABLED_CONTROLLED",
                evidence_maturity="TESTED")
        project_activation_state(db.path, repository_id, "AVAILABLE", f"activation-job:{job_id}:evaluation")
        db.update_activation_job(job_id, "AVAILABLE", {"promotion": {"policy": "AUTO_PROMOTION_ELIGIBLE",
                                                "active_pointer": str(pointer), "rollback_receipt": str(previous_path)}})
        db.complete_activation(job_id, "SUCCEEDED")
    return {"repository_id": repository_id, "status": "SUCCEEDED", "phase": "AVAILABLE"}


def select_pilot_candidates(db, *, limit: int = 3) -> list[dict]:
    """Select only reviewed WATCHLIST implementations with a safe local adapter."""
    with db._connect() as connection:
        rows = connection.execute("""SELECT DISTINCT r.github_repository_id,r.canonical_owner_repo,
            r.previous_decision,i.implementation_id,m.capability_id
            FROM repositories r JOIN capability_sources s ON s.github_repository_id=r.github_repository_id
            JOIN capability_implementations i ON i.source_id=s.source_id
            JOIN implementation_capabilities m ON m.implementation_id=i.implementation_id
            JOIN personal_states p ON p.subject_type='IMPLEMENTATION' AND p.subject_id=i.implementation_id
            WHERE p.state='WATCHLIST' AND m.capability_id='SKILL_ECOSYSTEM_DISCOVERY'
            AND r.previous_decision IN ('REFERENCE_ONLY','WATCH','CANDIDATE_FOR_QUARANTINE','USER_REVIEW_RECOMMENDED')
            AND NOT EXISTS (SELECT 1 FROM activation_queue q WHERE q.repository_id=r.github_repository_id)
            AND NOT EXISTS (SELECT 1 FROM user_feedback f WHERE f.github_repository_id=r.github_repository_id
                AND f.id=(SELECT MAX(f2.id) FROM user_feedback f2 WHERE f2.github_repository_id=r.github_repository_id)
                AND f.label IN ('WATCH','NOT_USEFUL','TOO_RISKY'))
            ORDER BY r.github_repository_id""").fetchall()
    return [{"repository_id": row["github_repository_id"], "repository": row["canonical_owner_repo"],
             "implementation_id": row["implementation_id"], "capability_id": row["capability_id"],
             "reason": "read-only pinned index; no upstream code execution, credentials, or service"}
            for row in rows[:max(0, limit)]]


def enqueue_selected_pilots(db, *, limit: int = 1) -> list[dict]:
    selected = select_pilot_candidates(db, limit=limit)
    for item in selected:
        item["job_id"] = db.enqueue_activation(item["repository_id"], TIER_1, "QUARANTINED",
                                                "AUTO_SELECTED_READ_ONLY_INDEX")
    return selected


def run_activation_worker(root: str | Path, db, *, provider=None, limit: int = 3) -> list[dict]:
    root = Path(root).resolve()
    provider = provider or GitHubSourceProvider()
    lock = CrashSafeLock(root / "state" / "activation-worker.lock", "pti-activation-worker")
    if lock.acquire() != LockState.ACQUIRED:
        return [{"status": "ALREADY_ACTIVE_OR_LOCKED"}]
    results = []
    try:
        jobs = [job for job in db.list_activation_queue()
                if job["status"] in {"PENDING", "RETRYABLE", "PROCESSING"}][:max(0, limit)]
        for job in jobs:
            if job["attempt_count"] >= 3:
                db.complete_activation(job["id"], "FAILED_TERMINAL", "MAX_RETRIES_EXCEEDED")
                results.append({"repository_id": job["repository_id"], "status": "FAILED_TERMINAL",
                                "reason": "MAX_RETRIES_EXCEEDED"})
                continue
            claimed = db.claim_activation(job["id"])
            if not claimed or claimed["status"] != "PROCESSING":
                continue
            try:
                results.append(_advance(root, db, claimed, provider))
            except (HumanGate, SandboxRejected) as error:
                reason = str(error)
                db.complete_activation(job["id"], "BLOCKED_HUMAN", reason)
                prior = db.get_activation(job['repository_id']) or {}
                if json.loads(claimed['contract_json'] or '{}').get('adapter') == ADAPTER:
                    revoke_activation_availability(db.path, job['repository_id'])
                if not (reason == 'EXECUTABLE_CANDIDATE_BOUNDARY_PREVENTS_ACTIVATION'
                        and prior.get('activation_state') == 'FAILED_WITH_EXPLAINED_REASON'):
                    _record(db, job["repository_id"], job["activation_tier"], "BLOCKED_HUMAN",
                            trial_status='DISABLED', notes=reason)
                results.append({"repository_id": job["repository_id"], "status": "BLOCKED_HUMAN", "reason": reason})
            except (TerminalFailure, ValueError) as error:
                reason = str(error)[:200]
                db.complete_activation(job["id"], "FAILED_TERMINAL", reason)
                _record(db, job["repository_id"], job["activation_tier"], "FAILED_WITH_EXPLAINED_REASON", notes=reason)
                results.append({"repository_id": job["repository_id"], "status": "FAILED_TERMINAL", "reason": reason})
            except (OSError, TimeoutError, subprocess.TimeoutExpired) as error:
                reason = str(error)[:200]
                status = "FAILED_TERMINAL" if claimed["attempt_count"] >= 3 else "RETRYABLE"
                db.complete_activation(job["id"], status, reason)
                results.append({"repository_id": job["repository_id"], "status": status, "reason": reason})
            except Exception as error:
                reason = f"UNEXPECTED_{type(error).__name__}"[:200]
                status = "FAILED_TERMINAL" if claimed["attempt_count"] >= 3 else "RETRYABLE"
                db.complete_activation(job["id"], status, reason)
                results.append({"repository_id": job["repository_id"], "status": status, "reason": reason})
    finally:
        lock.release()
    return results
