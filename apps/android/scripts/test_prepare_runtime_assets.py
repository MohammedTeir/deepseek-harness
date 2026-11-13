"""Host metadata rejection, not Android loading evidence."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class AssetGuardTest(unittest.TestCase):
    def test_old_manifest_cannot_package_an_unlinked_addon(self):
        with tempfile.TemporaryDirectory(prefix="harness-old-runtime-") as directory:
            android = Path(directory)
            script = android / "scripts/prepare_runtime_assets.py"
            script.parent.mkdir()
            shutil.copy2(Path(__file__).with_name("prepare_runtime_assets.py"), script)
            metadata = android / "runtime/out"
            metadata.mkdir(parents=True)
            (metadata / "runtime-build.json").write_text(json.dumps({"sha256": {"libnode.so": "0" * 64}}))
            result = subprocess.run([sys.executable, str(script), str(android / "assets")],
                                    capture_output=True, text=True, timeout=30, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing verified Android addon Node dependency", result.stderr)
            self.assertFalse((android / "assets").exists())

    def test_manifest_without_atomic_binding_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="harness-no-atomic-") as directory:
            android = Path(directory)
            script = android / "scripts/prepare_runtime_assets.py"
            script.parent.mkdir()
            shutil.copy2(Path(__file__).with_name("prepare_runtime_assets.py"), script)
            metadata = android / "runtime/out"
            metadata.mkdir(parents=True)
            (metadata / "runtime-build.json").write_text(json.dumps({
                "sha256": {"libnode.so": "0" * 64, "libnode_executable.so": "1" * 64,
                           "libharness_require_builtin.so": "2" * 64},
                "systemNodeDependency": "libnode.so", "requireBuiltinNodeDependency": "libnode.so",
                "packagedNodeExecutable": "libnode_executable.so"}))
            result = subprocess.run([sys.executable, str(script), str(android / "assets")],
                                    capture_output=True, text=True, timeout=30, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing inspected atomic publication binding", result.stderr)
            self.assertFalse((android / "assets").exists())

    def test_changed_atomic_source_cannot_reuse_inspected_binary(self):
        with tempfile.TemporaryDirectory(prefix="harness-stale-atomic-") as directory:
            root = Path(directory)
            android = root / "apps/android"
            script = android / "scripts/prepare_runtime_assets.py"
            script.parent.mkdir(parents=True)
            shutil.copy2(Path(__file__).with_name("prepare_runtime_assets.py"), script)
            source = root / "native/system/packages/entry/src/atomic_publish.c"
            source.parent.mkdir(parents=True)
            source.write_text("changed after native compilation")
            metadata = android / "runtime/out"
            metadata.mkdir(parents=True)
            (metadata / "runtime-build.json").write_text(json.dumps({
                "sha256": {"libnode.so": "0" * 64, "libnode_executable.so": "1" * 64,
                           "libharness_require_builtin.so": "2" * 64, "libharness_atomic.so": "3" * 64},
                "systemNodeDependency": "libnode.so", "requireBuiltinNodeDependency": "libnode.so",
                "atomicNodeDependency": "libnode.so", "atomicSourceSha256": "0" * 64,
                "packagedNodeExecutable": "libnode_executable.so"}))
            result = subprocess.run([sys.executable, str(script), str(android / "assets")],
                                    capture_output=True, text=True, timeout=30, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Atomic publication source changed", result.stderr)
            self.assertFalse((android / "assets").exists())

    def test_manifest_without_inspected_executable_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="harness-no-executable-") as directory:
            android = Path(directory)
            script = android / "scripts/prepare_runtime_assets.py"
            script.parent.mkdir()
            shutil.copy2(Path(__file__).with_name("prepare_runtime_assets.py"), script)
            metadata = android / "runtime/out"
            metadata.mkdir(parents=True)
            (metadata / "runtime-build.json").write_text(json.dumps({
                "sha256": {"libnode.so": "0" * 64}, "systemNodeDependency": "libnode.so"}))
            result = subprocess.run([sys.executable, str(script), str(android / "assets")],
                                    capture_output=True, text=True, timeout=30, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing inspected Node executable", result.stderr)
            self.assertFalse((android / "assets").exists())


if __name__ == "__main__":
    unittest.main()
