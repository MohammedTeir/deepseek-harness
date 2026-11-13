"""Pure parser fixtures; these are not Android runtime or session evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('profile_validator', Path(__file__).parents[1] / 'scripts/validate_profile_result.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ProfileEvidenceTest(unittest.TestCase):
    def fixture(self):
        build = {'apkSha256': {'app-debug.apk': 'a' * 64},
                 'packagedLibraries': {'libharness_atomic.so': {'sha256': 'b' * 64}}}
        value = {'schemaVersion': 1, 'apkSha256': 'a' * 64, 'nativePublicationSha256': 'b' * 64,
                 'platform': 'android', 'arch': 'arm64', 'node': 'v24.22.1',
                 'device': {'api': 30, 'model': 'synthetic parser fixture'}, 'profile': 'sdk-minimal',
                 'serverInfo': {'name': 'deepseek-harness-sdk-runtime'},
                 'nativeInternalLoader': {'product': 'require-builtin', 'abi': 'napi-v9'},
                 'harnessStarted': True, 'sessionRecoveredAcrossRuntimeRestart': True, 'recoveredNondefaultDirectory': True,
                 'modelRequestExecuted': False, 'approvedCommandExecuted': False, 'appRestartVerified': False,
                 'gate2Passed': False, 'installedPublicationBindingWritable': False,
                 'supervisorUid': 10001, 'supervisorPid': 100, 'pid': 101,
                 'kernelIdentity': {'uid': 10001, 'pid': 101, 'parentPid': 100},
                 'persistedJsonlSha256': {'project/session/session.v4.jsonl': 'c' * 64},
                 'previousRunSessionRecovered': False,
                 'persistenceDiagnostics': {'shutdownAcknowledgements': 2, 'sessionIntegrityAfterRejectedRecovery': True,
                    'missingSessionFailure': {'name': 'JsonRpcResponseError'}, 'storage': {
                        'publicationStrategy': 'renameat2-noreplace', 'directorySync': True, 'fileSync': True,
                        'exclusivePreparedFilePublish': True, 'existingPathRejected': True}}}
        return value, build

    def test_previous_invocation_is_separate_from_runtime_restart(self):
        value, build = self.fixture()
        validator.validate(value, build)
        with self.assertRaises(ValueError):
            validator.validate(value, build, require_previous_invocation=True)
        value['previousRunSessionRecovered'] = True
        validator.validate(value, build, require_previous_invocation=True)

    def test_rejects_changed_artifacts_and_weakened_assertions(self):
        value, build = self.fixture()
        mutations = [
            lambda v: v.update(apkSha256='d' * 64),
            lambda v: v.update(nativePublicationSha256='d' * 64),
            lambda v: v.update(gate2Passed=True),
            lambda v: v.update(appRestartVerified=True),
            lambda v: v.update(approvedCommandExecuted=True),
            lambda v: v.update(sessionRecoveredAcrossRuntimeRestart=False),
            lambda v: v.update(persistedJsonlSha256={}),
            lambda v: v['kernelIdentity'].update(uid=0),
            lambda v: v['persistenceDiagnostics'].update(shutdownAcknowledgements=1),
            lambda v: v['persistenceDiagnostics'].update(sessionIntegrityAfterRejectedRecovery=False),
            lambda v: v['persistenceDiagnostics']['storage'].update(directorySync=False),
            lambda v: v['persistenceDiagnostics']['storage'].update(publicationStrategy='ordinary-rename'),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                altered = copy.deepcopy(value)
                mutate(altered)
                with self.assertRaises(ValueError):
                    validator.validate(altered, build)


if __name__ == '__main__':
    unittest.main()
