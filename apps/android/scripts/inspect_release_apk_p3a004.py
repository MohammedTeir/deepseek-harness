"""Audit the exact locally built release APK for P3A-004 native closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ANDROID = ROOT / "apps/android"
SDK = Path(os.environ["ANDROID_HOME"])
BUILD_TOOLS = SDK / "build-tools/36.0.0"
READELF = SDK / "ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(*args: object) -> str:
    return subprocess.check_output([str(x) for x in args], text=True, stderr=subprocess.STDOUT)


def readelf_report(path: Path) -> str:
    return run(READELF, "-h", "-l", "-d", "-W", path)


def parse_elf(path: Path) -> dict:
    report = readelf_report(path)
    loads = []
    for line in report.splitlines():
        fields = line.split()
        if fields and fields[0] == "LOAD" and fields[-1].startswith("0x"):
            loads.append(int(fields[-1], 16))
    needed = sorted(set(re.findall(r"\(NEEDED\).*?\[([^]]+)\]", report)))
    interpreter_match = re.search(r"Requesting program interpreter:\s*([^]]+)", report)
    machine_match = re.search(r"^\s*Machine:\s*(.+)$", report, re.MULTILINE)
    type_match = re.search(r"^\s*Type:\s*(.+)$", report, re.MULTILINE)
    api_match = re.search(r"Android.*API(?: level)?\s*:?\s*(\d+)", report, re.IGNORECASE)
    return {
        "machine": machine_match.group(1).strip() if machine_match else None,
        "type": type_match.group(1).strip() if type_match else None,
        "interpreter": interpreter_match.group(1).strip() if interpreter_match else None,
        "neededLibraries": needed,
        "loadSegmentAlignmentsBytes": loads,
        "minimumAndroidApiNote": int(api_match.group(1)) if api_match else None,
        "androidIdentNotePresent": "Android" in report,
        "allLoadSegments16KiBAligned": bool(loads) and min(loads) >= 16384,
        "readelfSha256": sha256_bytes(report.encode()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    apk = args.apk.resolve()
    if not apk.is_file():
        raise SystemExit(f"Missing APK: {apk}")

    checks = []
    try:
        output = run(BUILD_TOOLS / "zipalign", "-c", "-P", "16", "4", apk)
        checks.append({"name": "zipalign_16k", "passed": True, "output": output})
    except subprocess.CalledProcessError as exc:
        checks.append({"name": "zipalign_16k", "passed": False, "output": exc.output})
    try:
        output = run(BUILD_TOOLS / "apksigner", "verify", "--verbose", apk)
        checks.append({"name": "apksigner", "passed": True, "output": output})
    except subprocess.CalledProcessError as exc:
        checks.append({"name": "apksigner", "passed": False, "output": exc.output, "expectedForUnsignedApk": True})
    badging = run(BUILD_TOOLS / "aapt", "dump", "badging", apk)
    checks.append({"name": "aapt_badging", "passed": True, "output": badging})
    min_sdk = int(re.search(r"sdkVersion:'(\d+)'", badging).group(1))
    target_sdk = int(re.search(r"targetSdkVersion:'(\d+)'", badging).group(1))
    native_code = sorted(re.search(r"native-code: '([^']+)'", badging).group(1).split())

    with zipfile.ZipFile(apk) as archive:
        names = sorted(name for name in archive.namelist() if name.startswith("lib/"))
        native_names = [name for name in names if name.startswith("lib/arm64-v8a/") and not name.endswith("/")]
        other_native = [name for name in names if not name.startswith("lib/arm64-v8a/") and not name.endswith("/")]
        if not native_names:
            raise SystemExit("No arm64-v8a native libraries packaged in APK")
        with tempfile.TemporaryDirectory(prefix="p3a004-apk-audit-") as temp:
            temp_dir = Path(temp)
            artifacts = []
            for name in native_names:
                data = archive.read(name)
                path = temp_dir / Path(name).name
                path.write_bytes(data)
                elf = parse_elf(path)
                artifacts.append({
                    "apkPath": name,
                    "artifact": path.name,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                    "elf": elf,
                    "classification": (
                        "process-proof-executable-carrier" if path.name == "libharness_process_probe.so" else
                        "pty-proof-fixture" if path.name == "libharness_pty_fixture.so" else
                        "android-runtime-bridge" if path.name == "libharness_probe.so" else
                        "runtime-jni-or-addon"
                    ),
                    "proofOnlyReviewRequired": path.name in {"libharness_process_probe.so", "libharness_pty_fixture.so"},
                })

        runtime_assets = sorted(name for name in archive.namelist() if name.startswith("assets/runtime/") and not name.endswith("/"))
        third_party_assets = sorted(name for name in archive.namelist() if name.startswith("assets/third-party/") and not name.endswith("/"))
        license_hashes = {name: sha256_bytes(archive.read(name)) for name in runtime_assets + third_party_assets}

    runtime_build = json.loads((ANDROID / "runtime/out/runtime-build.json").read_text())
    pty_build = json.loads((ANDROID / "runtime/out/node-pty/build.json").read_text())
    expected_build_hashes = dict(runtime_build.get("sha256", {}))
    expected_build_hashes["libharness_node_pty.so"] = pty_build["binarySha256"]
    expected_build_hashes["libharness_pty_fixture.so"] = pty_build["fixtureSha256"]
    comparisons = []
    for artifact in artifacts:
        expected = expected_build_hashes.get(artifact["artifact"])
        comparisons.append({
            "artifact": artifact["artifact"],
            "buildRecordSha256": expected,
            "matchesBuildRecord": expected == artifact["sha256"] if expected else None,
        })

    report = {
        "schemaVersion": 1,
        "task": "P3A-004",
        "scope": "exact locally assembled unsigned release APK; package inspection only, no device execution",
        "apk": {"path": str(apk.relative_to(ROOT)), "bytes": apk.stat().st_size, "sha256": sha256_file(apk)},
        "package": {
            "applicationId": re.search(r"package: name='([^']+)'", badging).group(1),
            "versionCode": int(re.search(r"versionCode='(\d+)'", badging).group(1)),
            "versionName": re.search(r"versionName='([^']+)'", badging).group(1),
            "minimumSdk": min_sdk,
            "targetSdk": target_sdk,
            "nativeCode": native_code,
            "allNativeEntries": names,
            "nonArm64NativeEntries": other_native,
        },
        "checks": checks,
        "nativeArtifacts": artifacts,
        "buildRecordComparisons": comparisons,
        "licenseAssets": {"runtimeAndThirdPartyCount": len(license_hashes), "sha256": license_hashes},
        "sourceBuild": {
            "nodeVersion": runtime_build.get("nodeVersion"),
            "nodeArchiveSha256": runtime_build.get("nodeArchiveSha256"),
            "ndk": pty_build.get("ndk"),
            "compileApi": pty_build.get("api"),
            "abi": pty_build.get("arch"),
            "profileImageSha256": sha256_file(ANDROID / "runtime/out/profile-v9/profile-image.zip"),
            "profileQualificationSha256": sha256_file(ANDROID / "runtime/out/profile-v9/profile-qualification.json"),
        },
        "acceptance": {
            "exactApkNativeClosureInspected": True,
            "allArm64ArtifactsAligned16KiB": all(a["elf"]["allLoadSegments16KiBAligned"] for a in artifacts),
            "allBuildHashesMatchedWhereRecorded": all(x["matchesBuildRecord"] for x in comparisons if x["matchesBuildRecord"] is not None),
            "proofOnlyArtifactsRequireProductionScopeDecision": any(a["proofOnlyReviewRequired"] for a in artifacts),
            "androidExecutionVerified": False,
            "p3a004Complete": False,
            "remaining": "Resolve production scope of proof-only process/PTY artifacts and perform Android device execution; package closure is now hash-bound for this APK.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"apkSha256": report["apk"]["sha256"], "nativeCount": len(artifacts), "native": [(a["artifact"], a["sha256"], a["elf"]["allLoadSegments16KiBAligned"]) for a in artifacts], "acceptance": report["acceptance"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
