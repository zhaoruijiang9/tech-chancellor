import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from pti.activation_worker import run_activation_worker, rollback_activation
from pti.activation_readiness import audit_current_library
from pti.execution_adapter import extract_reviewed_source, validate_plan
from pti.secure_execution import DockerWSL2Backend, SandboxRejected
import test_activation_worker as legacy

FakeProvider = legacy.FakeProvider


def fixture_archive(script='printf "KEEP\\n" > /output/result.txt\n'):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('fixture/README.md', '# Synthetic compression fixture\n')
        archive.writestr('fixture/main.sh', script)
    return output.getvalue()


def fixture_candidate(root, image='busybox@sha256:' + 'a' * 64):
    db, store = legacy.ActivationWorkerTests().setup_candidate(root)
    store.upsert_capability('CONTEXT_COMPRESSION', 'Compression', 'synthetic test only')
    store.link_implementation_capability('impl:example/skill-index', 'CONTEXT_COMPRESSION', 'COMPLEMENT', 'review')
    plan = {'target_capability': 'CONTEXT_COMPRESSION', 'execution': {
        'sandbox_backend': 'DOCKER_WSL2_LINUX', 'sandbox_image': image, 'source_pin': 'b'*40,
        'runtime_type': 'CLI', 'command': ['/bin/sh', '/candidate/main.sh'],
        'expected_outputs': ['result.txt'], 'timeout_seconds': 3},
        'evaluation': {'kind': 'BOUNDED_TEXT_COMPRESSION', 'input_text': 'KEEP\n' + 'noise '*100,
                       'required_facts': ['KEEP'], 'minimum_reduction': 0.2}}
    path = root / 'state/secure_execution/plans/repo-7.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan), encoding='utf-8')
    with db._connect() as connection:
        connection.execute("UPDATE activation_queue SET activation_tier='TIER_2_LOW_PRIVILEGE_LOCAL_TOOL'")
    return db, store, plan


class ExecutionAdapterTests(unittest.TestCase):
    def mock_backend(self, output='KEEP\n', **changes):
        result = {'exit_code': 0, 'timed_out': False, 'outputs': {'result.txt': output},
                  'cleanup': 'CONTAINER_DESTROYED', 'filesystem_input_unchanged': True, **changes}
        mock = patch('pti.execution_adapter.DockerWSL2Backend').start()
        self.addCleanup(patch.stopall)
        mock.return_value.run.return_value = result
        patch('pti.activation_worker.DockerWSL2Backend').start()
        return mock

    def test_worker_uses_existing_queue_phases_pin_and_rollback(self):
        self.mock_backend()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db, store, _ = fixture_candidate(root)
            provider = FakeProvider(fixture_archive())
            result = run_activation_worker(root, db, provider=provider)
            self.assertEqual(result[0]['status'], 'SUCCEEDED')
            self.assertEqual(provider.pins, 0)
            self.assertEqual(provider.fetches, 1)
            job = db.list_activation_queue()[0]
            self.assertEqual(job['phase'], 'AVAILABLE')
            evidence = json.loads(job['evidence_json'])
            self.assertEqual(evidence['static_review']['reviewed_surface'], 'entire bounded UTF-8 source snapshot')
            self.assertEqual(evidence['evaluation']['outcome'], 'IMPROVED')
            self.assertNotIn('outputs', evidence['functional'])
            self.assertEqual(db.get_activation(7)['activation_tier'], 'TIER_2_LOW_PRIVILEGE_LOCAL_TOOL')
            self.assertNotIn('USED', [p['state'] for p in store.get_implementation('impl:example/skill-index')['personal_states']])
            self.assertEqual(rollback_activation(root, 7, job['id'], db=db)['status'], 'ROLLED_BACK')

    def test_success_without_meaningful_delta_does_not_promote(self):
        self.mock_backend('KEEP\n' + 'noise '*100)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db, _, _ = fixture_candidate(root)
            result = run_activation_worker(root, db, provider=FakeProvider(fixture_archive()))
            self.assertEqual(result[0]['reason'], 'NO_MEANINGFUL_DELTA')
            self.assertFalse((root/'managed_capabilities/repo-7/active.json').exists())

    def test_missing_fact_or_failed_cleanup_is_not_functional_pass(self):
        for output, changes in [('lost', {}), ('KEEP', {'cleanup': 'FAILED'}),
                                ('KEEP', {'timed_out': True}), ('KEEP', {'filesystem_input_unchanged': False})]:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as d:
                self.mock_backend(output, **changes)
                root = Path(d)
                db, _, _ = fixture_candidate(root)
                result = run_activation_worker(root, db, provider=FakeProvider(fixture_archive()))
                self.assertEqual(result[0]['status'], 'BLOCKED_HUMAN')
                self.assertFalse((root/'managed_capabilities/repo-7/active.json').exists())
                patch.stopall()

    def test_unverified_backend_blocks_before_source_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db, _, _ = fixture_candidate(root)
            provider = FakeProvider(fixture_archive())
            result = run_activation_worker(root, db, provider=provider)
            self.assertEqual(result[0]['status'], 'BLOCKED_HUMAN')
            self.assertEqual(provider.fetches, 0)

    def test_static_credential_behavior_blocks_before_execution(self):
        mock = self.mock_backend()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db, _, _ = fixture_candidate(root)
            result = run_activation_worker(root, db, provider=FakeProvider(fixture_archive('sudo dangerous\n')))
            self.assertEqual(result[0]['status'], 'BLOCKED_HUMAN')
            mock.return_value.run.assert_not_called()

    def test_excluded_trading_candidate_and_existing_failure_stay_gated(self):
        for mutation in ("UPDATE repositories SET canonical_owner_repo='example/TradingAgents'",
                         "INSERT INTO activation_records(github_repository_id,activation_tier,activation_state) VALUES(7,'TIER_2_LOW_PRIVILEGE_LOCAL_TOOL','FAILED_WITH_EXPLAINED_REASON')"):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                db, _, _ = fixture_candidate(root)
                with db._connect() as connection:
                    connection.execute(mutation)
                result = run_activation_worker(root, db, provider=FakeProvider(fixture_archive()))
                self.assertEqual(result[0]['status'], 'BLOCKED_HUMAN')
                if mutation.startswith('INSERT'):
                    self.assertEqual(db.get_activation(7)['activation_state'], 'FAILED_WITH_EXPLAINED_REASON')

    def test_plan_rejects_unbounded_or_unsupported_evaluation(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, plan = fixture_candidate(Path(d))
            for change in ({'target_capability': 'TRADING'}, {'mounts': ['host']},
                           {'evaluation': {'kind': 'LLM'}}):
                with self.subTest(change=change), self.assertRaises(SandboxRejected):
                    validate_plan({**plan, **change})

    def test_full_source_rejects_windows_aliases_and_opaque_binary(self):
        for filename, data in [('NUL.txt', 'bad'), ('main.sh', b'\xff\x00'), ('x.', 'bad')]:
            with tempfile.TemporaryDirectory() as d:
                raw = io.BytesIO()
                with zipfile.ZipFile(raw, 'w') as archive:
                    archive.writestr('fixture/README.md', '# Fixture')
                    archive.writestr('fixture/'+filename, data)
                with self.assertRaises(SandboxRejected):
                    extract_reviewed_source(raw.getvalue(), Path(d)/'source')

    def test_prepare_cannot_mount_arbitrary_protected_path(self):
        backend = object.__new__(DockerWSL2Backend)
        with tempfile.TemporaryDirectory() as d:
            backend.root = Path(d)
            _, _, plan = fixture_candidate(backend.root)
            from pti.secure_execution import ExecutionContract
            with patch('pti.secure_execution._tree_hashes') as hashes, self.assertRaises(SandboxRejected):
                backend.prepare(ExecutionContract.from_dict(plan['execution']), Path('D:/money'), 'synthetic', 7)
            hashes.assert_not_called()

    def test_readiness_audit_does_not_recreate_verified_platform_gap(self):
        with tempfile.TemporaryDirectory() as d:
            db, store, _ = fixture_candidate(Path(d))
            store.upsert_source('extra', 'GITHUB_REPOSITORY', 'example/extra', 'https://github.com/example/extra')
            store.upsert_implementation('extra', 'extra', 'extra', 'TOOL_OR_WORKFLOW')
            cap = 'SECURE_THIRD_PARTY_EXECUTION_SANDBOX'
            store.upsert_capability(cap, 'sandbox', 'verified fixture')
            store.set_personal_state('CAPABILITY', cap, 'VERIFIED', 'unit-test-only')
            audit_current_library(db, {i: {'category': 'REQUIRES_OS_SANDBOX', 'blocker': 'historical evidence'}
                                       for i in ('impl:example/skill-index', 'extra')})
            with db._connect() as connection:
                states = [r[0] for r in connection.execute('SELECT state FROM personal_states WHERE subject_id=?', (cap,))]
            self.assertNotIn('MISSING_CAPABILITY', states)

    def test_teardown_does_not_mistake_daemon_failure_for_cleanup(self):
        backend = object.__new__(DockerWSL2Backend)
        with patch.object(backend, '_call', side_effect=[(1, '', 'offline'), (1, '', 'daemon unavailable')]):
            with self.assertRaises(SandboxRejected):
                backend.teardown('synthetic')

    def test_semantic_pipeline_queues_only_explicit_plan_when_platform_verified(self):
        from pti.activation_runtime import postprocess_semantic_decision
        with tempfile.TemporaryDirectory() as d:
            db, store, _ = fixture_candidate(Path(d))
            with db._connect() as c:
                c.execute("DELETE FROM implementation_capabilities WHERE capability_id='SKILL_ECOSYSTEM_DISCOVERY'")
                c.execute('DELETE FROM activation_queue')
            cap = 'SECURE_THIRD_PARTY_EXECUTION_SANDBOX'
            store.upsert_capability(cap, 'sandbox', 'unit-test-only')
            store.set_personal_state('CAPABILITY', cap, 'VERIFIED', 'unit-test-only')
            result = postprocess_semantic_decision(db, 7, {'ACTION': 'CANDIDATE_FOR_QUARANTINE',
                                                         'BEST_ROUTE': 'GENERAL'}, packet={})
            self.assertEqual(result['tier'], 'TIER_2_LOW_PRIVILEGE_LOCAL_TOOL')
            self.assertEqual(len(db.list_activation_queue()), 1)

    def test_verified_platform_without_plan_is_still_adapter_blocked(self):
        from pti.activation_runtime import postprocess_semantic_decision
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db, store, _ = fixture_candidate(root)
            (root/'state/secure_execution/plans/repo-7.json').unlink()
            with db._connect() as c:
                c.execute("DELETE FROM implementation_capabilities WHERE capability_id='SKILL_ECOSYSTEM_DISCOVERY'")
                c.execute('DELETE FROM activation_queue')
            cap = 'SECURE_THIRD_PARTY_EXECUTION_SANDBOX'
            store.upsert_capability(cap, 'sandbox', 'unit-test-only')
            store.set_personal_state('CAPABILITY', cap, 'VERIFIED', 'unit-test-only')
            result = postprocess_semantic_decision(db, 7, {'ACTION': 'CANDIDATE_FOR_QUARANTINE',
                                                         'BEST_ROUTE': 'GENERAL'}, packet={})
            self.assertEqual(result['reason'], 'NEEDS_SAFE_ADAPTER')
            self.assertEqual(db.list_activation_queue(), [])

    def test_resume_rejects_changed_managed_source_and_revokes_availability(self):
        self.mock_backend()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db, store, _ = fixture_candidate(root)
            self.assertEqual(run_activation_worker(root, db, provider=FakeProvider(fixture_archive()))[0]['status'], 'SUCCEEDED')
            (root/'managed_capabilities/repo-7/versions'/('b'*40)/'source/main.sh').write_text('changed')
            with db._connect() as c:
                c.execute("UPDATE activation_queue SET status='PROCESSING'")
            result = run_activation_worker(root, db, provider=FakeProvider(fixture_archive()))
            self.assertEqual(result[0]['reason'], 'MANAGED_SOURCE_CHANGED_AFTER_REVIEW')
            self.assertNotIn('AVAILABLE', [p['state'] for p in store.get_implementation('impl:example/skill-index')['personal_states']])

    def test_resume_rejects_changed_execution_plan(self):
        self.mock_backend()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db, _, plan = fixture_candidate(root)
            self.assertEqual(run_activation_worker(root, db, provider=FakeProvider(fixture_archive()))[0]['status'], 'SUCCEEDED')
            plan['execution']['command'] = ['/bin/true']
            (root/'state/secure_execution/plans/repo-7.json').write_text(json.dumps(plan))
            with db._connect() as c:
                c.execute("UPDATE activation_queue SET status='PROCESSING'")
            result = run_activation_worker(root, db, provider=FakeProvider(fixture_archive()))
            self.assertEqual(result[0]['reason'], 'EXECUTION_PLAN_CHANGED_ON_RESUME')


if __name__ == '__main__':
    unittest.main()
