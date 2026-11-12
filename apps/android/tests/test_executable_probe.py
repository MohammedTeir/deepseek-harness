"""Real Linux Node parent/child proof; Android executable loading remains untested."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == "posix" and hasattr(os, "getuid") and os.getuid() != 0,
                     "Requires a non-root POSIX host with its own procfs")
class ExecutableProbeTest(unittest.TestCase):
    def test_real_child_stdout_exit_identity_and_original_apis(self):
        script = Path(__file__).resolve().parents[1] / "runtime/executable-smoke.mjs"
        with tempfile.TemporaryDirectory(prefix="harness-executable-probe-") as directory:
            output = Path(directory) / "result.json"
            with subprocess.Popen(["node", str(script), str(output)], cwd=directory,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                try:
                    _, stderr = process.communicate(timeout=45)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try: process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.communicate()
                    raise
                self.assertEqual(process.returncode, 0, stderr)
                evidence = json.loads(output.read_text())
                self.assertEqual(evidence["pid"], process.pid)
            self.assertEqual(evidence["kernelIdentity"]["uid"], os.getuid())
            self.assertEqual(evidence["kernelIdentity"]["parentPid"], os.getpid())
            self.assertEqual(evidence["childNode"]["parentPid"], evidence["pid"])
            self.assertNotEqual(evidence["childNode"]["pid"], evidence["pid"])
            self.assertEqual(evidence["childNode"]["uid"], os.getuid())
            self.assertEqual(evidence["childResult"]["exitCode"], 0)
            self.assertEqual(json.loads(evidence["childResult"]["stdout"]), evidence["childNode"])
            self.assertEqual(evidence["childNodeLaunch"], "passed")
            for api in ["sqlite", "worker", "esm"]: self.assertTrue(evidence[api])
            self.assertFalse(evidence["harnessStarted"])


if __name__ == "__main__":
    unittest.main()
