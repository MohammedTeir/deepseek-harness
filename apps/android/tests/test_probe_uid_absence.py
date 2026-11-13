"""Linux feature-absence regression; the preloader is not Android test evidence."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class ProbeUidAbsenceTest(unittest.TestCase):
    def test_missing_getuid_is_reported_without_fabricating_identity(self):
        script = Path(__file__).resolve().parents[1] / "runtime/smoke.mjs"
        with tempfile.TemporaryDirectory(prefix="harness-no-uid-") as directory:
            root = Path(directory)
            preload = root / "missing-uid.mjs"
            preload.write_text("process.getuid = undefined;\n")
            output = root / "result.json"
            result = subprocess.run(["node", "--import", str(preload), str(script), str(output)],
                                    capture_output=True, text=True, timeout=45, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads(output.read_text())
            self.assertFalse(evidence["uidApiAvailable"])
            self.assertIsNone(evidence["uid"])
            self.assertNotIn("androidUid", evidence)
            self.assertTrue(evidence["sqlite"])
            self.assertTrue(evidence["worker"])
            self.assertTrue(evidence["esm"])
            self.assertEqual(evidence["crypto"], "ba9c736f19e7f60b7f6764adb0b7908c0a2b394e09b6c09863528c7f2bc86095")
            self.assertFalse(evidence["harnessStarted"])


if __name__ == "__main__":
    unittest.main()
