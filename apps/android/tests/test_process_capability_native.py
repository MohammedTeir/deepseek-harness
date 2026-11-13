"""Real host fork/exec/pipe/PTY tests, not Android Bionic or device evidence."""
import json
import os
from pathlib import Path
import signal
import select
import re
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == 'posix' and Path('/proc/self').exists() and os.getuid() != 0, 'Non-root POSIX procfs host required')
class ProcessCapabilityNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='harness-process-native-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.exe = cls.root / 'probe'
        source = Path(__file__).parents[1] / 'execution/process-proof/process_probe.cpp'
        subprocess.run(['c++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', str(source), '-lutil', '-o', str(cls.exe)], check=True, timeout=60)

    def test_real_suite_streaming_exit_backpressure_and_pty(self):
        with tempfile.TemporaryDirectory(prefix='harness-cap-work-') as root:
            result = subprocess.run([str(self.exe), '--suite', root], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(value['platform'], 'linux-host-only')
            self.assertEqual(value['status'], 'PASS')
            self.assertFalse(value['gate3Passed'])
            self.assertEqual(value['cases']['streaming']['stdout'], 'OUT-1\nOUT-2\n')
            self.assertEqual(value['cases']['streaming']['stderr'], 'ERR-1\nERR-2\n')
            self.assertEqual(value['cases']['streaming']['exitCode'], 7)
            self.assertTrue(value['cases']['streaming']['streamObservedBeforeAckAndExit'])
            self.assertTrue(value['cases']['backpressure']['completeBytesVerified'])
            self.assertEqual(value['cases']['missingExecutable']['exitCode'], 127)
            self.assertEqual(value['cases']['cancellation']['signal'], signal.SIGTERM)
            self.assertEqual(value['cases']['timeoutAndKill']['signal'], signal.SIGKILL)
            self.assertTrue(value['cases']['descendantGroup']['descendantReaped'])
            self.assertTrue(value['pty']['resizeAndInputVerified'])

    def test_suite_term_cancels_and_reaps_actual_live_worker(self):
        with tempfile.TemporaryDirectory(prefix='harness-cap-cancel-') as root:
            with subprocess.Popen([str(self.exe), '--suite', root], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as suite:
                observed = None
                try:
                    deadline = time.monotonic() + 10
                    notes = b''
                    while time.monotonic() < deadline:
                        ready, _, _ = select.select([suite.stderr], [], [], max(0, deadline - time.monotonic()))
                        if not ready:
                            break
                        chunk = os.read(suite.stderr.fileno(), 4096)
                        if not chunk:
                            break
                        notes += chunk
                        match = re.search(rb'HARNESS_PROCESS_READY pid=(\d+) mode=--ignore-term', notes)
                        if match:
                            observed = int(match[1])
                            break
                    self.assertIsNotNone(observed, 'No actual worker readiness event: ' + notes.decode())
                    suite.send_signal(signal.SIGTERM)
                    out, err = suite.communicate(timeout=8)
                    self.assertNotEqual(suite.returncode, 0, err)
                    self.assertEqual(json.loads(out)['status'], 'CANCELLED')
                    self.assertIn('HARNESS_PROCESS_REAPED pid=' + str(observed), notes.decode() + err)
                finally:
                    if suite.poll() is None:
                        suite.kill()
                        suite.communicate(timeout=5)

    def test_refuses_nonprivate_workspace_and_unknown_roles(self):
        with tempfile.TemporaryDirectory(prefix='harness-cap-invalid-') as root:
            os.chmod(root, 0o755)
            result = subprocess.run([str(self.exe), '--suite', root], capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Private owned workspace', json.loads(result.stdout)['failure'])
        result = subprocess.run([str(self.exe), '--arbitrary-command'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 125)


if __name__ == '__main__':
    unittest.main()
