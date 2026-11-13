"""Native Java allocation policy on a host JVM; no Android execution/IPC claim."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform.startswith('linux') and os.getuid() != 0,
                     'Non-root Linux filesystem identity and POSIX mode checks required')
class TerminalAllocationGrantTest(unittest.TestCase):
    def test_exact_terminal_allocation_and_native_resource_revocation(self):
        android = Path(__file__).resolve().parents[1]
        jdk = Path(os.environ['JAVA_HOME']) / 'bin'
        with tempfile.TemporaryDirectory(prefix='harness-terminal-grant-') as temporary:
            root = Path(temporary)
            source = android / 'app/src/main/java/io/github/mohammedteir/deepseekharness'
            subprocess.run([str(jdk/'javac'), '--release', '17', '-d', str(root),
                            str(source/'CommandGrant.java'), str(source/'TerminalAllocationGrant.java'),
                            str(android/'tests/TerminalAllocationGrantFixture.java')], check=True, timeout=30)
            modes = ['approval', 'denial', 'bindings', 'revocation', 'expiry', 'immutable', 'concurrency',
                     'workspace-replacement', 'workspace-symlink', 'executable-replacement',
                     'executable-writable', 'constructor']
            for mode in modes:
                with self.subTest(mode=mode):
                    work = root / mode
                    work.mkdir()
                    result = subprocess.run([str(jdk/'java'), '-cp', str(root),
                                             'io.github.mohammedteir.deepseekharness.TerminalAllocationGrantFixture',
                                             mode, str(work)], capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(result.stdout.strip(), mode + ' PASS')
