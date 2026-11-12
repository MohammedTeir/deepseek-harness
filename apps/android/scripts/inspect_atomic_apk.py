"""Inspect built APK #1 signatures, Android ELF, licenses and source fingerprints."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from package_node import inspect


def main():
    android = Path(__file__).resolve().parents[1]
    root = android.parents[1]
    sdk = Path(os.environ["ANDROID_HOME"])
    ndk = sdk / "ndk/28.2.13676358"
    readelf = ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf"
    tools = sdk / "build-tools/36.0.0"
    apk = android / "atomic-proof/build/outputs/apk/debug/atomic-proof-debug.apk"
    test = android / "atomic-proof/build/outputs/apk/androidTest/debug/atomic-proof-debug-androidTest.apk"
    record = {"schemaVersion": 1, "scope": "APK #1 isolated native proof; not production persistence",
              "environment": "Linux x86_64 cloud; NDK 28.2.13676358; API 29 ARM64; SDK 36; JDK 21; AGP 8.13.2",
              "physicalDeviceTests": "BLOCKED", "productionAdapterIntegrated": False,
              "sessionRecoveryVerified": False, "gate2Passed": False, "checks": []}

    def run(command):
        result = subprocess.run([str(x) for x in command], capture_output=True, text=True, timeout=60)
        record["checks"].append({"command": [str(x) for x in command], "exitCode": result.returncode,
                                 "stdout": result.stdout, "stderr": result.stderr})
        result.check_returncode()
        return result.stdout

    for path in [apk, test]:
        run([tools / "apksigner", "verify", "--verbose", "--print-certs", path])
        run([tools / "zipalign", "-c", "-P", "16", "4", path])
    badging = run([tools / "aapt", "dump", "badging", apk])
    for text in ["ai.deepseek.harness.android.atomicpoc", "sdkVersion:'29'", "targetSdkVersion:'36'", "native-code: 'arm64-v8a'"]:
        if text not in badging:
            raise ValueError(f"Missing APK identity: {text}")
    if "uses-permission:" in badging:
        raise ValueError("Isolated PoC must not request permissions")
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix="atomic-apk-inspection-") as temporary:
        native_names = [name for name in archive.namelist() if name.startswith("lib/")]
        if native_names != ["lib/arm64-v8a/libatomic_poc.so"]:
            raise ValueError(f"Unexpected native payload: {native_names}")
        binary = archive.read(native_names[0])
        elf = Path(temporary) / "libatomic_poc.so"
        elf.write_bytes(binary)
        deps = inspect(readelf, elf)
        if deps - {"libc.so", "libm.so", "libdl.so"}:
            raise ValueError(f"Unexpected static-libc++ executable dependency: {deps}")
        report = run([readelf, "-h", "-l", "-d", "-n", "-W", elf])
        if "/system/bin/linker64" not in report:
            raise ValueError("Not an Android executable")
        entry = re.search(r"Entry point address:\s+0x([0-9a-fA-F]+)", report)
        if not entry or int(entry.group(1), 16) == 0:
            raise ValueError("Missing native entry point")
        symbols = run([readelf, "--dyn-syms", "-W", elf])
        if re.search(r"\bUND\b.*\brenameat2\b", symbols):
            raise ValueError("API-30 Bionic wrapper is forbidden in API-29 proof")
        record["nativeDependencies"] = sorted(deps)
        record["nativePackagedSha256"] = hashlib.sha256(binary).hexdigest()
        licenses = {"assets/licenses/LICENSE": root / "LICENSE",
                    "assets/licenses/THIRD_PARTY_NOTICES.md": root / "THIRD_PARTY_NOTICES.md",
                    "assets/licenses/NDK_NOTICE": ndk / "NOTICE"}
        for path in (android / "licenses/third-party").iterdir():
            if path.is_file():
                licenses["assets/third-party/" + path.name] = path
        for name, path in licenses.items():
            if archive.read(name) != path.read_bytes():
                raise ValueError(f"Missing/changed license {name}")
        record["licenseAssets"] = sorted(licenses)
    record["apkPath"] = apk.relative_to(root).as_posix()
    record["apkBytes"] = apk.stat().st_size
    record["apkSha256"] = hashlib.sha256(apk.read_bytes()).hexdigest()
    record["testApkPath"] = test.relative_to(root).as_posix()
    record["testApkSha256"] = hashlib.sha256(test.read_bytes()).hexdigest()
    record["nativeBuildSha256"] = hashlib.sha256((android / "atomic-proof/build/generated/native/arm64-v8a/libatomic_poc.so").read_bytes()).hexdigest()
    files = sorted(path for path in (android / "atomic-proof").rglob("*") if path.is_file() and "build" not in path.relative_to(android / "atomic-proof").parts)
    files.extend(android / name for name in ["settings.gradle.kts", "scripts/test_device.py", "scripts/inspect_atomic_apk.py",
                                           "scripts/validate_atomic_result.py", "tests/test_atomic_native.py"])
    record["sourceFilesSha256"] = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files if path.suffix != ".md"}
    record["artifactInspection"] = "PASS"
    destination = android / "evidence/atomic-poc-apk1-build.json"
    destination.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: record[key] for key in ["apkPath", "apkBytes", "apkSha256", "nativePackagedSha256", "artifactInspection", "physicalDeviceTests"]}, indent=2))


if __name__ == "__main__":
    main()
