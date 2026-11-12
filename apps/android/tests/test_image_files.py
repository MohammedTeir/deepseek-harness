"""Real host JVM path/symlink tests; no Android filesystem claim."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ImageFilesTest(unittest.TestCase):
    def test_rejects_escape_and_cleanup_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            android=Path(__file__).resolve().parents[1]
            jdk=Path(os.environ['JAVA_HOME'])/'bin'
            subprocess.run([str(jdk/'javac'),'-d',directory,
                            str(android/'app/src/main/java/io/github/mohammedteir/deepseekharness/ImageFiles.java'),
                            str(android/'tests/ImageFilesFixture.java')],check=True,timeout=30)
            result=subprocess.run([str(jdk/'java'),'-cp',directory,'io.github.mohammedteir.deepseekharness.ImageFilesFixture'],
                                  capture_output=True,text=True,timeout=15,check=True)
            self.assertIn('outside file retained',result.stdout)
