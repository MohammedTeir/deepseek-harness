"""Real production controller/profile/PTY on Linux; native broker is a contract double."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ANDROID = Path(__file__).parents[1]
ROOT = ANDROID.parents[1]

@unittest.skipUnless(sys.platform.startswith('linux') and os.getuid() != 0, 'Non-root Linux PTY required')
class TerminalRuntimeTest(unittest.TestCase):
    def test_real_controller_original_profile_registry_and_recovery(self):
        self.qualify(False)

    def test_original_terminal_wait_timeout_and_explicit_cancellation(self):
        self.qualify(True)

    def qualify(self, lifecycle):
        subprocess.run(['node',str(ANDROID/'scripts/build_terminal_bundle.mjs')],cwd=ROOT,check=True,capture_output=True,timeout=30)
        with tempfile.TemporaryDirectory(prefix='harness-terminal-runtime-') as temporary:
            work=Path(temporary)
            fixture=work/'libharness_pty_fixture.so'
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',str(ANDROID/'runtime/node-pty-proof/fixture.cpp'),'-o',str(fixture)],check=True,timeout=30)
            result=work/'result.json'
            run=subprocess.run(['node',str(ANDROID/'tests/terminal-profile-reference.mjs'),str(result)],
                               env={**os.environ,'HARNESS_TERMINAL_FIXTURE':str(fixture), 'HARNESS_TERMINAL_LIFECYCLE': '1' if lifecycle else '0'},capture_output=True,text=True,timeout=130)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            value=json.loads(result.read_text())
            self.assertTrue(value['sessionRecoveredAcrossRuntimeRestart'])
            self.assertEqual(value['report']['starts'],1)
            self.assertEqual(value['report']['concurrentConsumers'],2)
            self.assertEqual(value['report']['concurrentRejections'],1)
            self.assertTrue(value['hostQualification']['nativeTransportIsDouble'])
            self.assertFalse(value['hostQualification']['androidExecuted'])
            if lifecycle:
                report = value['report']
                self.assertEqual(report['qualification'], 'lifecycle')
                self.assertEqual(report['lifecycle']['timeout']['waitReason'], 'timeout')
                self.assertEqual(report['lifecycle']['timeout']['sessionStatus']['kind'], 'running')
                self.assertTrue(report['lifecycle']['childNoLongerObservable'])
                self.assertEqual(report['result']['sessionStatus'], {'kind': 'exited', 'exitCode': None, 'signal': 'SIGINT'})
            if lifecycle and os.environ.get('HARNESS_TERMINAL_LIFECYCLE_HOST_EVIDENCE'):
                Path(os.environ['HARNESS_TERMINAL_LIFECYCLE_HOST_EVIDENCE']).write_text(result.read_text())
            if not lifecycle and os.environ.get('HARNESS_TERMINAL_RUNTIME_HOST_EVIDENCE'):
                Path(os.environ['HARNESS_TERMINAL_RUNTIME_HOST_EVIDENCE']).write_text(result.read_text())
