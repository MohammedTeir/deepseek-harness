"""Genuine host profile/Agent/terminal-registry test; no Android authority evidence."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

ANDROID = Path(__file__).parents[1]

@unittest.skipUnless(sys.platform.startswith('linux') and os.getuid() != 0, 'Non-root Linux host required')
class TerminalRegistryProfileTest(unittest.TestCase):
    def test_real_profile_approval_owners_allocation_cleanup_and_recovery(self):
        self.qualify(False)

    def test_original_approval_at_allocation_with_explicit_transport_double(self):
        self.qualify(True)

    def qualify(self, allocation):
        with tempfile.TemporaryDirectory(prefix='harness-terminal-registry-') as temporary:
            root = Path(temporary)
            fixture = root/'libharness_pty_fixture.so'
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',str(ANDROID/'runtime/node-pty-proof/fixture.cpp'),'-o',str(fixture)],check=True,timeout=30)
            output = root/'result.json'
            env = {**os.environ,'HARNESS_NODE_PTY_FIXTURE':str(fixture)}
            command = ['node',str(ANDROID/'tests/terminal-registry-reference.mjs'),str(output)]
            if allocation: command.append('--allocation-authority')
            process = subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
            try:
                stdout,stderr = process.communicate(timeout=90)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid,signal.SIGTERM)
                    try:process.communicate(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL);process.communicate(timeout=5)
            self.assertEqual(process.returncode,0,stdout+stderr)
            value = json.loads(output.read_text())
            self.assertFalse(value['nativeHumanApprovalVerified'])
            self.assertTrue(value['sessionRecoveredAcrossRuntimeRestart'])
            if allocation:
                self.assertTrue(value['nativeWireIsTestDouble'])
                self.assertEqual(value['result']['starts'],1)
                self.assertEqual(value['result']['consumes'],1)
            else:
                self.assertTrue(value['result']['registryPublicationRollbackObserved'])
                self.assertTrue(value['result']['ownerDisposalObserved'])
            evidence = 'HARNESS_TERMINAL_AUTHORITY_HOST_EVIDENCE' if allocation else 'HARNESS_TERMINAL_REGISTRY_HOST_EVIDENCE'
            if os.environ.get(evidence): Path(os.environ[evidence]).write_text(output.read_text())
