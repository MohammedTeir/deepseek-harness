"""ELF rejection cases use synthetic readelf output, not runtime execution."""
import unittest
from pathlib import Path
from unittest.mock import patch

from package_node import inspect


class ElfInspectionTests(unittest.TestCase):
    report = """Type: DYN (Shared object file)
Machine: AArch64
  LOAD 0x000000 0x000000 0x000000 0x100 0x100 R E 0x4000
  0x0001 (NEEDED) Shared library: [libc.so]
"""

    def inspect_report(self, report):
        with patch("package_node.subprocess.check_output", return_value=report):
            return inspect(Path("readelf"), Path("libnode.so"))

    def test_android_dependency(self):
        self.assertEqual(self.inspect_report(self.report), {"libc.so"})

    def test_foreign_abi(self):
        with self.assertRaisesRegex(ValueError, "ARM64"):
            self.inspect_report(self.report.replace("AArch64", "Advanced Micro Devices X86-64"))

    def test_linux_dependency(self):
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            self.inspect_report(self.report.replace("libc.so", "libc.so.6"))

    def test_small_page_alignment(self):
        with self.assertRaisesRegex(ValueError, "16 KB"):
            self.inspect_report(self.report.replace("0x4000", "0x1000"))


if __name__ == "__main__":
    unittest.main()
