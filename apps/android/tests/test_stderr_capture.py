"""Real host POSIX descriptor tests, not Android or Node execution evidence."""
from pathlib import Path
import subprocess
import tempfile
import unittest
import os


@unittest.skipUnless(os.name == "posix", "Requires POSIX descriptor and symlink semantics")
class StderrCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="harness-stderr-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        cls.binary = cls.root / "capture"
        android = Path(__file__).resolve().parents[1]
        subprocess.run(["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-I", str(android / "native"), str(android / "tests/stderr_capture.cpp"),
                        "-o", str(cls.binary)], check=True, timeout=30)

    def test_capture_and_restore_on_explicit_and_scope_exit(self):
        for mode in ["explicit", "scope"]:
            log = self.root / (mode + ".log")
            result = subprocess.run([str(self.binary), str(log), mode],
                                    capture_output=True, text=True, timeout=10, check=True)
            self.assertEqual(log.read_text(), "startup failed before JS\n")
            self.assertEqual(result.stderr, "original stderr restored\n")

    def test_unavailable_log_preserves_original_stderr(self):
        result = subprocess.run([str(self.binary), str(self.root / "missing/log"), "failure"],
                                capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(result.stderr, "capture unavailable\n")

    def test_symlink_log_is_rejected_without_overwriting_target(self):
        target = self.root / "protected"
        target.write_text("unchanged")
        link = self.root / "link"
        link.symlink_to(target)
        subprocess.run([str(self.binary), str(link), "failure"],
                       capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(target.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
