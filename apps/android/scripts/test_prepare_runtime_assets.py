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


if __name__ == "__main__":
    unittest.main()
