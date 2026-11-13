"""Synthetic parser fixtures derived from host output; never Android execution evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('command_validator', ROOT / 'scripts/validate_command_result.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class CommandEvidenceTest(unittest.TestCase):
    def fixture(self):
        value = json.loads((ROOT / 'evidence/host-command-profile-reference.json').read_text())
        value.pop('hostQualification')
        value.update(platform='android', arch='arm64', device={'api': 30, 'model': 'synthetic parser fixture, not phone'},
                     supervisorUid=10001, supervisorPid=10, kernelIdentity={'uid': 10001, 'parentPid': 10, 'pid': 11},
                     apkSha256='a' * 64, nativeNodeSha256='b' * 64, nativePublicationSha256='c' * 64)
        value['nativeBroker'] = {'uid': 10001, 'sessionId': value['sessionId'], 'callIds': ['deny-host', 'allow-host'],
                                 'cwd': value['commandResult']['cwd'], 'processLaunches': 1,
                                 'audit': [{'code': 'EXECUTED', 'uid': 10001, 'peerPid': 12}]}
        build = {'apkSha256': {'app-debug.apk': 'a' * 64}, 'packagedLibraries': {
            'libnode_executable.so': {'sha256': 'b' * 64}, 'libharness_atomic.so': {'sha256': 'c' * 64}}}
        return value, build

    def test_complete_fixture(self):
        value, build = self.fixture()
        validator.validate(value, build)

    def test_rejects_missing_or_changed_proof(self):
        value, build = self.fixture()
        changes = [
            lambda r: r.update(apkSha256='d' * 64),
            lambda r: r.update(originalRegistryAndPipeline=False),
            lambda r: r.update(gate2Passed=True),
            lambda r: r.update(modelRequestExecuted=True),
            lambda r: r['nativeBroker'].update(processLaunches=2),
            lambda r: r['kernelIdentity'].update(uid=0),
            lambda r: r['negative']['replay'].update(ok=True),
            lambda r: r['negative']['uid'].update(code='IGNORED'),
            lambda r: r['commandResult'].update(stdout='manufactured'),
            lambda r: r.update(recoveredHistory=[]),
            lambda r: r['nativeBroker'].update(audit=[]),
            lambda r: r.update(persistedJsonlSha256={}),
        ]
        for change in changes:
            with self.subTest(change=change):
                candidate = copy.deepcopy(value)
                change(candidate)
                with self.assertRaises(ValueError):
                    validator.validate(candidate, build)


if __name__ == '__main__':
    unittest.main()
