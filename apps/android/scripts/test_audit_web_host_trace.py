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

    def test_isolates_web_process_and_descendants(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'trace.10').write_text(
                f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web"], 0) = 0\n'
                f'openat(AT_FDCWD, "{ROOT}/app.js", O_RDONLY) = 3\n'
                'clone(flags=0) = 11\n')
            (directory / 'trace.11').write_text(f'openat(AT_FDCWD, "{ROOT}/child.js", O_RDONLY) = 3\n')
            (directory / 'trace.12').write_text(f'openat(AT_FDCWD, "{ROOT}/runner.js", O_RDONLY) = 3\n')
            output = directory / 'result.json'
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--root-pid', '10', '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            result = json.loads(output.read_text())
            self.assertEqual(result['traceFiles'], 2)
            self.assertEqual(result['distinctSuccessfulAbsoluteCheckoutPaths'], 2)
            self.assertFalse(result['runnerAndProfileNotSeparated'])
            (directory / 'trace.11').unlink()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_overlay_must_be_present_in_root_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            overlay = ROOT / 'apps/android/tests/fixtures/web-host-bounded.patch.yml'
            trace = directory / 'trace.10'
            trace.write_text(
                f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web", "--patch", "{overlay}"], 0) = 0\n'
                f'openat(AT_FDCWD, "{ROOT}/app.js", O_RDONLY) = 3\n')
            output = directory / 'result.json'
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--root-pid', '10', '--overlay', str(overlay), '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            result = json.loads(output.read_text())
            self.assertEqual(result['qualificationOverlay']['path'], overlay.relative_to(ROOT).as_posix())
            trace.write_text(trace.read_text().replace(str(overlay), '/other.patch.yml'))
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_rejects_root_that_is_not_original_web_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'trace.10').write_text('execve("/node", ["/node", "runner.js"], 0) = 0\n')
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--root-pid', '10', '--output', str(directory / 'result.json')]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_missing_trace_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = subprocess.run([sys.executable, str(SCRIPT), '--trace-glob', str(Path(temporary) / 'missing.*'),
                                      '--output', str(Path(temporary) / 'out.json')], capture_output=True)
            self.assertNotEqual(process.returncode, 0)


if __name__ == '__main__':
    unittest.main()
