"""ELF rejection cases use synthetic readelf output, not runtime execution."""
import unittest
from pathlib import Path
from unittest.mock import patch

from package_node import inspect, inspect_addon, inspect_executable


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

    def test_addon_requires_explicit_node_dependency(self):
        with patch("package_node.subprocess.check_output", return_value=self.report):
            with self.assertRaisesRegex(ValueError, "DT_NEEDED"):
                inspect_addon(Path("readelf"), Path("addon.so"))

    def test_node_dependency_is_allowed_only_for_addon_inspection(self):
        report = self.report + "  0x0002 (NEEDED) Shared library: [libnode.so]\n"
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            self.inspect_report(report)
        with patch("package_node.subprocess.check_output", return_value=report):
            inspect_addon(Path("readelf"), Path("addon.so"))

    def test_addon_node_dependency_does_not_allow_linux_libc(self):
        report = self.report.replace("libc.so", "libc.so.6") + "  0x0002 (NEEDED) Shared library: [libnode.so]\n"
        with patch("package_node.subprocess.check_output", return_value=report):
            with self.assertRaisesRegex(ValueError, "Unreviewed"):
                inspect_addon(Path("readelf"), Path("addon.so"))

    def test_executable_requires_android_interpreter_and_real_entry(self):
        report = self.report + "  0x0002 (NEEDED) Shared library: [libnode.so]\nEntry point address: 0x01234\n[Requesting program interpreter: /system/bin/linker64]\n(RUNPATH) [$ORIGIN]\n"
        with patch("package_node.subprocess.check_output", return_value=report):
            inspect_executable(Path("readelf"), Path("node.so"))
        for invalid in [report.replace("/system/bin/linker64", "/lib/ld-linux-aarch64.so.1"),
                        report.replace("$ORIGIN", "/tmp"), report.replace("0x01234", "0x0")]:
            with self.subTest(invalid=invalid), patch("package_node.subprocess.check_output", return_value=invalid):
                with self.assertRaises(ValueError):
                    inspect_executable(Path("readelf"), Path("node.so"))


if __name__ == "__main__":
    unittest.main()
