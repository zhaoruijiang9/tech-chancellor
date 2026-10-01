import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pti.secure_execution import (ExecutionContract, SandboxRejected, DockerWSL2Backend,
                                  secure_execution_status, REQUIRED_CHECKS, register_verified_backend)


IMAGE = 'busybox@sha256:' + 'a' * 64


class SecureExecutionTests(unittest.TestCase):
    def spec(self, **changes):
        return ExecutionContract.from_dict({
            'sandbox_backend': 'DOCKER_WSL2_LINUX', 'sandbox_image': IMAGE,
            'source_pin': 'b' * 40, 'runtime_type': 'CLI',
            'command': ['/bin/sh', '/candidate/main.sh'],
            'expected_outputs': ['result.txt'], **changes})

    def test_contract_roundtrip_and_conservative_defaults(self):
        spec = self.spec()
        self.assertEqual(ExecutionContract.from_dict(spec.to_dict()), spec)
        self.assertEqual(spec.network_policy, 'NONE')
        self.assertEqual(spec.timeout_seconds, 30)

    def test_rejects_floating_image(self):
        with self.assertRaises(SandboxRejected):
            self.spec(sandbox_image='busybox:latest')

    def test_rejects_unpinned_source(self):
        with self.assertRaises(SandboxRejected):
            self.spec(source_pin='main')

    def test_rejects_network(self):
        with self.assertRaises(SandboxRejected):
            self.spec(network_policy='HOST')

    def test_rejects_credentials_and_arbitrary_mounts(self):
        for extra in ({'environment': {'GH_TOKEN': 'synthetic'}}, {'mounts': ['D:\\money']},
                      {'privileged': True}, {'docker_socket': True}, {'service_behavior': 'DAEMON'}):
            with self.subTest(extra=extra), self.assertRaises(SandboxRejected):
                self.spec(**extra)

    def test_rejects_invalid_outputs_and_runtime(self):
        for changes in ({'expected_outputs': ['../secret']}, {'expected_outputs': ['/etc/passwd']},
                        {'expected_outputs': ['nested/file']}, {'runtime_type': 'MCP'},
                        {'command': []}, {'command': ['x' * 2000]}):
            with self.subTest(changes=changes), self.assertRaises(SandboxRejected):
                self.spec(**changes)

    def test_rejects_unbounded_resources(self):
        for changes in ({'timeout_seconds': 0}, {'timeout_seconds': 10000}, {'memory_mb': 4096},
                        {'pids_limit': 0}, {'cpus': 100}, {'timeout_seconds': True}):
            with self.subTest(changes=changes), self.assertRaises(SandboxRejected):
                self.spec(**changes)

    def test_fresh_install_is_unconfigured_without_docker_call(self):
        with tempfile.TemporaryDirectory() as d, patch('subprocess.Popen') as popen:
            self.assertEqual(secure_execution_status(d)['status'], 'UNCONFIGURED')
            with self.assertRaises(SandboxRejected):
                DockerWSL2Backend(d)
            popen.assert_not_called()

    def test_host_environment_is_stripped(self):
        with patch.dict('os.environ', {'GH_TOKEN': 'fake', 'OPENAI_API_KEY': 'fake',
                                      'SSH_AUTH_SOCK': 'fake', 'PATH': 'unsafe'}, clear=False):
            env = DockerWSL2Backend.client_environment(Path('isolated-config'))
        self.assertFalse({'GH_TOKEN', 'OPENAI_API_KEY', 'SSH_AUTH_SOCK'} & env.keys())
        self.assertEqual(env['DOCKER_CONFIG'], str(Path('isolated-config')))
        self.assertNotEqual(env['PATH'], 'unsafe')

    def test_profile_has_only_readonly_inputs_and_bounded_tmpfs_output(self):
        backend = object.__new__(DockerWSL2Backend)
        args = backend.create_arguments(self.spec(), 'test', Path('scope/source'), Path('scope/input'))
        joined = ' '.join(args)
        for flag in ('--read-only', '--network none', '--cap-drop ALL', '--user 65534:65534',
                     '--security-opt no-new-privileges=true', '--pids-limit 32', '--cpus 0.5'):
            self.assertIn(flag, joined)
        mounts = [args[i+1] for i, arg in enumerate(args) if arg == '--mount']
        self.assertEqual(len(mounts), 2)
        self.assertTrue(all(m.endswith(',readonly') for m in mounts))
        self.assertIn('/output:rw', joined)
        self.assertNotIn('--privileged', args)
        self.assertNotIn('--pid', args)

    def test_verification_receipt_cannot_be_a_mock_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'state').mkdir()
            (root/'state/secure_execution.local.json').write_text(json.dumps({
                'docker_path': str(root/'docker.exe'), 'approved_images': [IMAGE],
                'verification_sha256': 'a'*64}))
            (root/'state/containment-evidence.json').write_text('{"phase_c":"PASS"}')
            self.assertEqual(secure_execution_status(root)['status'], 'NOT_VERIFIED')

    def receipt_fixture(self, root):
        # Synthetic receipt is for parser unit tests only, never host qualification.
        (root/'state').mkdir()
        proof = {'phase_c': 'PASS_VERIFIED_FOR_BOUNDED_EVALUATION',
                 'fixture_checks': ['PASS:'+c for c in REQUIRED_CHECKS],
                 'observed_process_ids_removed': [999], 'host_service_scheduler_path_check': 'PASS_UNCHANGED_INVENTORY',
                 'fixture_exit_code': 0, 'background_children_observed': True, 'timeout_observed': True,
                 'timeout_cleanup': 'PASS_CONTAINER_REMOVED_WITH_CHILDREN', 'host_secret_unchanged': True,
                 'residual_container_check': 'PASS', 'secret_sentinel_removed': True,
                 'd_money_accessed': False, 'd_money_mounted': False, 'd_money_container_paths_visible': False,
                 'image_digest': IMAGE}
        raw = json.dumps(proof).encode()
        (root/'state/containment-evidence.json').write_bytes(raw)
        config = {'docker_path': str(root/'missing/docker.exe'), 'approved_images': [IMAGE],
                  'verification_sha256': hashlib.sha256(raw).hexdigest()}
        (root/'state/secure_execution.local.json').write_text(json.dumps(config))
        return config

    def test_qualified_receipt_does_not_claim_engine_health_and_missing_cli_blocks(self):
        with tempfile.TemporaryDirectory() as d, patch('subprocess.Popen') as popen:
            root = Path(d)
            self.receipt_fixture(root)
            status = secure_execution_status(root)
            self.assertEqual(status['status'], 'VERIFIED_RECEIPT')
            self.assertEqual(status['runtime_health'], 'CHECKED_AT_EXECUTION')
            with self.assertRaisesRegex(SandboxRejected, 'DOCKER_EXECUTABLE_UNAVAILABLE'):
                DockerWSL2Backend(root)
            popen.assert_not_called()

    def test_untested_image_cannot_be_added_to_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            config = self.receipt_fixture(root)
            config['approved_images'].append('busybox@sha256:'+'c'*64)
            (root/'state/secure_execution.local.json').write_text(json.dumps(config))
            self.assertEqual(secure_execution_status(root)['status'], 'NOT_VERIFIED')

    def test_explicit_registration_updates_fresh_db_without_real_use_claim(self):
        from pti.storage import Database
        from pti.capability_intelligence import CapabilityStore
        with tempfile.TemporaryDirectory() as d, patch('pti.secure_execution.DockerWSL2Backend') as mocked:
            db = Database(Path(d)/'state/intelligence.db')
            db.initialize()
            cap = 'SECURE_THIRD_PARTY_EXECUTION_SANDBOX'
            store = CapabilityStore(db.path)
            store.upsert_capability(cap, 'sandbox', 'gap')
            store.set_personal_state('CAPABILITY', cap, 'MISSING_CAPABILITY', 'unit-fixture')
            mocked.return_value.proof = {'run_id': 'unit-test-only'}
            register_verified_backend(d, db)
            with db._connect() as c:
                states = {r[0] for r in c.execute('SELECT state FROM personal_states WHERE subject_id=?', (cap,))}
            self.assertEqual(states, {'VERIFIED', 'AVAILABLE'})


if __name__ == '__main__':
    unittest.main()
