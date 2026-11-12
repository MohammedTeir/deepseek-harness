"""Real host JVM grant-policy tests; not Android UI, IPC or process evidence."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class CommandGrantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="harness-command-grant-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        android = Path(__file__).resolve().parents[1]
        jdk = Path(os.environ["JAVA_HOME"]) / "bin"
        cls.java = str(jdk / "java")
        subprocess.run([str(jdk / "javac"), "--release", "17", "-d", str(cls.root),
                        str(android / "app/src/main/java/io/github/mohammedteir/deepseekharness/CommandGrant.java"),
                        str(android / "app/src/main/java/io/github/mohammedteir/deepseekharness/FixedPwdExecution.java"),
                        str(android / "app/src/main/java/io/github/mohammedteir/deepseekharness/OwnedProcess.java"),
                        str(android / "tests/CommandGrantFixture.java")], check=True, timeout=60)

    def test_policy(self):
        for mode in ("approval", "mutation", "expiry", "revocation", "concurrency", "immutable", "process", "failed-launch"):
            with self.subTest(mode=mode):
                result = subprocess.run([self.java, "-cp", str(self.root),
                                         "io.github.mohammedteir.deepseekharness.CommandGrantFixture", mode, str(self.root)],
                                        capture_output=True, text=True, timeout=15, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), mode + " PASS")


if __name__ == "__main__":
    unittest.main()
