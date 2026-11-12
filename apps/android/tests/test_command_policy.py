"""Native qualification hook policy unit test; no Android or end-to-end evidence."""
from pathlib import Path
import subprocess
import unittest


class CommandPolicyTest(unittest.TestCase):
    def test_downstream_original_policies_cannot_be_replaced_by_ask(self):
        script = Path(__file__).with_name('command-policy-reference.mjs')
        result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('downstream deny/cancel/ask', result.stdout)


if __name__ == '__main__':
    unittest.main()
