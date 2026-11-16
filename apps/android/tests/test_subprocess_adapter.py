"""Original-service adapter tests on Linux; never Android compatibility evidence."""
from pathlib import Path
import subprocess
import unittest

class SubprocessAdapterTest(unittest.TestCase):
    def test_original_runtime_exact_binding_and_real_host_execution(self):
        result = subprocess.run(['node', str(Path(__file__).with_name('subprocess-adapter-reference.mjs'))], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('NOT Android evidence', result.stdout)
