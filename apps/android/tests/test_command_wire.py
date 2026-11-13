"""Host transport cancellation with actual child ownership; not Android socket evidence."""
from pathlib import Path
import subprocess
import unittest


class CommandWireTest(unittest.TestCase):
    def test_lost_response_waits_for_real_child_cleanup(self):
        script = Path(__file__).parents[1] / 'tests/command-wire-reference.mjs'
        result = subprocess.run(['node', str(script)], capture_output=True, text=True, timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('real child reaped', result.stdout)


if __name__ == '__main__':
    unittest.main()
