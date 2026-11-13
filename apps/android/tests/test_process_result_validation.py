"""Synthetic parser regression inputs only; never Android execution evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ANDROID = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('process_validation', ANDROID/'scripts/validate_process_result.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ProcessResultValidationTest(unittest.TestCase):
    def fixture(self):
        value = json.loads((ANDROID/'evidence/process-host-native.json').read_text())['result']
        value.update(platform='android', architecture='aarch64', nativeExitCode=0, apkSha256='synthetic-apk', nativeProbeSha256='synthetic-native', supervisorUid=value['uid'], supervisorPid=value['parentPid'], installedProbeWritable=False, execPath='/synthetic/libharness_process_probe.so', expectedWorkspace=value['cwd'], device={'api':30}, shellTestPath='/system/bin/sh')
        return value, {'apkSha256':{'app-debug.apk':'synthetic-apk'}, 'processProbe':{'sha256':'synthetic-native'}}

    def test_rejects_mutated_evidence_and_scope(self):
        value, build = self.fixture()
        module.validate(value, build)
        for key, bad in [('apkSha256','wrong'), ('nativeProbeSha256','wrong'), ('platform','linux-host-only'), ('uid',0), ('gate3Passed',True), ('installedProbeWritable',True), ('expectedWorkspace','/outside')]:
            with self.subTest(key=key):
                modified = copy.deepcopy(value); modified[key] = bad
                with self.assertRaises(ValueError): module.validate(modified, build)
        value['cases']['streaming']['exitCode'] = 0
        with self.assertRaises(ValueError): module.validate(value, build)

    def test_partial_preserves_unavailability_without_acceptance(self):
        value, build = self.fixture()
        value['status'] = 'PARTIAL'; value['pty'] = {'status':'UNAVAILABLE','errno':13}
        with self.assertRaises(ValueError): module.validate(value, build)
        module.validate(value, build, allow_partial=True)
        value['pty']['errno'] = 0
        with self.assertRaises(ValueError): module.validate(value, build, allow_partial=True)
