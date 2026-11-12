"""Host JVM process ownership tests, not Android loader/permission evidence."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class OwnedProcessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="harness-process-owner-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        android = Path(__file__).resolve().parents[1]
        jdk = Path(os.environ["JAVA_HOME"]) / "bin"
        cls.java = str(jdk / "java")
        subprocess.run([str(jdk / "javac"), "-d", str(cls.root),
                        str(android / "app/src/main/java/io/github/mohammedteir/deepseekharness/OwnedProcess.java"),
                        str(android / "tests/OwnedProcessFixture.java")], check=True, timeout=60)

    def run_mode(self, mode):
        result = subprocess.run([self.java, "-cp", str(self.root),
                                 "io.github.mohammedteir.deepseekharness.OwnedProcessFixture", mode],
                                capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_real_exit_status_is_observed(self):
        self.assertIn("child reaped", self.run_mode("normal"))

    def test_close_terminates_and_reaps_a_live_child(self):
        self.assertIn("child reaped", self.run_mode("close"))

    def test_interrupted_cleanup_reaps_and_restores_interruption(self):
        self.assertIn("child reaped", self.run_mode("interrupted"))

    def test_cancellation_before_start_rejects_launch(self):
        self.assertIn("launch rejected", self.run_mode("preclosed"))


if __name__ == "__main__":
    unittest.main()
