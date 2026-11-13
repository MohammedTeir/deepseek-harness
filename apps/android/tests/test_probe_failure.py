"""Actual Linux Node failure reporting; no Android compatibility claim."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class ProbeFailureTest(unittest.TestCase):
    def test_real_worker_denial_retains_stage_and_error_without_success(self):
        script = Path(__file__).resolve().parents[1] / "runtime/smoke.mjs"
        with tempfile.TemporaryDirectory(prefix="harness-probe-failure-") as directory:
            output = Path(directory) / "result.json"
            result = subprocess.run(["node", "--permission", "--allow-fs-read=" + str(script),
                                     "--allow-fs-read=" + directory, "--allow-fs-write=" + directory,
                                     str(script), str(output)],
                                    capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(result.returncode, 1, result.stderr)
            evidence = json.loads(output.read_text())
            self.assertEqual(evidence["stage"], "worker")
            self.assertIn("--allow-worker", evidence["failure"])
            self.assertIn(evidence["failure"], result.stderr)
            self.assertFalse(evidence["harnessStarted"])
            self.assertNotIn("worker", evidence)


if __name__ == "__main__":
    unittest.main()
