"""Client authority contract cases; doubles are not Android broker evidence."""
from pathlib import Path
import subprocess
import unittest

class TerminalAuthorizationTest(unittest.TestCase):
    def test_denial_mutation_receipt_and_late_answer(self):
        source = Path(__file__).with_name('terminal-authorization-negative.mjs')
        result = subprocess.run(['node', str(source)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('doubles only, no Android evidence', result.stdout)
