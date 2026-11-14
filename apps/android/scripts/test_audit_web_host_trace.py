"""Trace parser tests use synthetic lines, never Android compatibility evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'apps/android/scripts/audit_web_host_trace.py'


class WebHostTraceAuditTest(unittest.TestCase):
    def test_records_only_successful_absolute_checkout_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.1'
            trace.write_text('\n'.join([
                f'openat(AT_FDCWD, "{ROOT}/example/a.node", O_RDONLY|O_CLOEXEC) = 8',
                f'openat(AT_FDCWD, "{ROOT}/example/missing.node", O_RDONLY) = -1 ENOENT',
                'openat(AT_FDCWD, "relative.node", O_RDONLY) = 9',
                'openat(AT_FDCWD, "/outside/foreign.node", O_RDONLY) = 10',
                f'openat(AT_FDCWD, "{ROOT}/example/output.node", O_WRONLY) = 11',
            ]) + '\n')
            output = directory / 'evidence.json'
            subprocess.run([sys.executable, str(SCRIPT), '--trace-glob', str(trace), '--output', str(output)], check=True, capture_output=True)
            result = json.loads(output.read_text())
            self.assertEqual(result['distinctSuccessfulAbsoluteCheckoutPaths'], 1)
            self.assertEqual(result['observedNativeAddons'], ['example/a.node'])
            self.assertFalse(result['androidExecuted'])
            self.assertFalse(result['completeAndroidGraph'])

    def test_missing_trace_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = subprocess.run([sys.executable, str(SCRIPT), '--trace-glob', str(Path(temporary) / 'missing.*'),
                                      '--output', str(Path(temporary) / 'out.json')], capture_output=True)
            self.assertNotEqual(process.returncode, 0)


if __name__ == '__main__':
    unittest.main()
