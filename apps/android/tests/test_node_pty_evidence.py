"""Synthetic parser regressions based on real host data; NOT Android evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
ANDROID=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('node_pty_validator',ANDROID/'scripts/validate_node_pty_result.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class NodePtyEvidenceTest(unittest.TestCase):
    def fixture(self):
        value=json.loads((ANDROID/'evidence/node-pty-host-source-reference.json').read_text())['result']
        value.update(platform='android',arch='arm64',nativeExitCode=0,apkSha256='test-apk',nodePtyAddonSha256='test-addon',fixtureSha256='test-fixture',nodeSha256='test-node',installedCodeWritable=False,supervisorUid=value['kernelIdentity']['uid'],supervisorPid=value['kernelIdentity']['parentPid'],device={'api':30},expectedWorkspace=value['cwd'],fixtureExecutable='/synthetic/libharness_pty_fixture.so')
        build={'apkSha256':{'app-debug.apk':'test-apk'},'packagedLibraries':{name:{'sha256':sha} for name,sha in [('libharness_node_pty.so','test-addon'),('libharness_pty_fixture.so','test-fixture'),('libnode_executable.so','test-node')]}}
        return value,build
    def test_complete_fixture_and_rejects_changed_identity_artifact_scope(self):
        value,build=self.fixture();module.validate(value,build)
        for key,bad in [('apkSha256','wrong'),('platform','linux'),('installedCodeWritable',True),('gate3Passed',True),('originalTerminalIntegrated',True)]:
            candidate=copy.deepcopy(value);candidate[key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError):module.validate(candidate,build)
    def test_rejects_missing_exit_input_signal_and_timeout(self):
        value,build=self.fixture()
        for mutation in [lambda v:v['cases'][0].update(output=''),lambda v:v['cases'][2].update(signal=0),lambda v:v['cases'][4].update(timedOut=False),lambda v:v['cases'][0]['nativeIdentity'].update(uid=0),lambda v:v['cases'][0].update(childNoLongerObservable=False)]:
            candidate=copy.deepcopy(value);mutation(candidate)
            with self.assertRaises(ValueError):module.validate(candidate,build)
