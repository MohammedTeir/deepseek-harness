"""Reject APKs that substitute or omit the original frontend payload."""
import hashlib
from pathlib import Path
import sys
import zipfile

repo = Path(__file__).resolve().parents[3]
apk = Path(sys.argv[1])
web = repo / "apps/web/dist"
with zipfile.ZipFile(apk) as archive:
    count = 0
    for source in web.rglob("*"):
        relative = source.relative_to(web)
        if not source.is_file() or source.suffix == ".map" or relative.parts[0] == "preview" or str(relative) == "preview.html":
            continue
        packed = archive.read(f"assets/web/{relative.as_posix()}")
        assert packed == source.read_bytes(), f"Frontend changed in APK: {relative}"
        count += 1
    assert count > 0 and "assets/web/index.html" in archive.namelist()
    assert archive.read("assets/web/licenses/harness/LICENSE") == (repo / "LICENSE").read_bytes()
    assert not any(name.endswith(".map") for name in archive.namelist())
    assert not any(name.startswith("assets/web/preview/") for name in archive.namelist())
print(f"Verified {count} original frontend files; license retained; preview and sourcemaps excluded")
print(f"APK SHA256 {hashlib.sha256(apk.read_bytes()).hexdigest()}")
