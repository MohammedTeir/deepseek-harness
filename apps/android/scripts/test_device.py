"""Install the bounded proof APKs on one selected device and retain test evidence.

This runs trusted instrumentation, not a Harness agent or a root provider.
Only proof-package output is collected; device-wide logcat is never requested.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile


def instrumentation_passed(output: str, count: int) -> bool:
    """Require the expected executed test count and reject Android runner errors."""
    return (
        re.search(rf"^OK \({count} tests?\)\s*$", output, re.MULTILINE) is not None
        and re.search(r"^INSTRUMENTATION_CODE: -1\s*$", output, re.MULTILINE) is not None
        and not re.search(r"FAILURES!!!|INSTRUMENTATION_FAILED|shortMsg=|INSTRUMENTATION_STATUS_CODE: -[12]", output)
    )


def main() -> int:
    """Fail on unavailable hardware, install errors, timeouts, or incomplete runs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", required=True, help="Device explicitly selected from adb devices")
    parser.add_argument("--proof", required=True, choices=["packaging", "runtime", "executable", "profile", "atomic"])
    parser.add_argument("--output", required=True, type=Path, help="New evidence directory")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    android = Path(__file__).resolve().parents[1]
    module, package, tests = (
        ("packaging-proof", "ai.deepseek.harness.android.packagingproof", 2)
        if args.proof == "packaging"
        else ("atomic-proof", "ai.deepseek.harness.android.atomicpoc", 1) if args.proof == "atomic"
        else ("app", "ai.deepseek.harness.android.runtimepoc", 1)
    )
    directory = "atomic-probe" if args.proof == "atomic" else "profile-probe" if args.proof == "profile" else "executable-probe" if args.proof == "executable" else "runtime-probe"
    record = {"schemaVersion": 1, "proof": args.proof,
              "observedAt": datetime.now(timezone.utc).isoformat(),
              "status": "BLOCKED", "harnessVerified": False, "steps": []}

    def adb(*command: str, timeout: int = 30) -> str:
        result = subprocess.run([args.adb, "-s", args.serial, *command],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=timeout, check=False)
        record["steps"].append({"command": list(command), "exitCode": result.returncode})
        if result.returncode:
            raise RuntimeError(result.stdout.strip())
        return result.stdout

    try:
        if adb("get-state").strip() != "device":
            raise RuntimeError("Selected device is not online and authorized")
        properties = ["ro.build.version.release", "ro.build.version.sdk", "ro.build.version.security_patch",
                      "ro.build.fingerprint", "ro.product.cpu.abilist", "ro.kernel.qemu", "ro.dalvik.vm.native.bridge"]
        record["device"] = {key: adb("shell", "getprop", key).strip() for key in properties}
        record["device"]["kernelArchitecture"] = adb("shell", "uname", "-m").strip()
        record["device"]["pageSize"] = adb("shell", "getconf", "PAGE_SIZE").strip()
        if int(record["device"]["ro.build.version.sdk"]) < 29:
            raise RuntimeError("Android API 29 or later is required")
        if "arm64-v8a" not in record["device"]["ro.product.cpu.abilist"].split(","):
            raise RuntimeError("Device does not advertise ARM64 APK support")
        paths = [android / module / f"build/outputs/apk/debug/{module}-debug.apk",
                 android / module / f"build/outputs/apk/androidTest/debug/{module}-debug-androidTest.apk"]
        record["apks"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        for index, path in enumerate(paths):
            installed = adb("install", "-r", str(path), timeout=120)
            (args.output / f"install-{index}.txt").write_text(installed)
            if not re.search(r"^Success\s*$", installed, re.MULTILINE):
                raise RuntimeError("Installer did not report success")
        if args.proof != "packaging":
            # A failed start must not attach a previous run's API evidence.
            adb("shell", "run-as", package, "rm", "-f", f"files/{directory}/result.json", f"files/{directory}/stderr.txt")
        selection = [] if args.proof == "packaging" else ["-e", "class", "io.github.mohammedteir.deepseekharness." + (
            "atomic.AtomicProofTest" if args.proof == "atomic" else "ProfileProbeTest" if args.proof == "profile" else "ExecutableProbeTest" if args.proof == "executable" else "RuntimeProbeTest")]
        output = adb("shell", "am", "instrument", "-w", "-r", *selection,
                     f"{package}.test/androidx.test.runner.AndroidJUnitRunner", timeout=180)
        (args.output / "instrumentation.txt").write_text(output)
        if args.proof != "packaging":
            try:
                diagnostic = adb("shell", "run-as", package, "cat", f"files/{directory}/stderr.txt")
                (args.output / "runtime-stderr.txt").write_text(diagnostic)
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                record["runtimeDiagnosticFailure"] = str(error)
            try:
                result = adb("shell", "run-as", package, "cat", f"files/{directory}/result.json")
                (args.output / "runtime-result.json").write_text(result)
                json.loads(result)
            except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
                record["runtimeResultFailure"] = str(error)
        if not instrumentation_passed(output, tests):
            record["status"] = "FAILED"
            raise RuntimeError("Instrumentation did not complete the expected tests; inspect instrumentation.txt")
        if "runtimeResultFailure" in record:
            record["status"] = "FAILED"
            raise RuntimeError("Runtime test passed without retrievable JSON evidence")
        if args.proof == "atomic":
            from validate_atomic_result import validate
            with zipfile.ZipFile(paths[0]) as archive:
                native_digest = hashlib.sha256(archive.read("lib/arm64-v8a/libatomic_poc.so")).hexdigest()
            validate(json.loads((args.output / "runtime-result.json").read_text()),
                     apk_sha256=record["apks"][paths[0].name], native_sha256=native_digest)
            record["physicalHardwareReviewed"] = False
        elif args.proof == "profile":
            from validate_profile_result import validate
            with zipfile.ZipFile(paths[0]) as archive:
                native_digest = hashlib.sha256(archive.read("lib/arm64-v8a/libharness_atomic.so")).hexdigest()
            expected = {"apkSha256": {"app-debug.apk": record["apks"][paths[0].name]},
                        "packagedLibraries": {"libharness_atomic.so": {"sha256": native_digest}}}
            validate(json.loads((args.output / "runtime-result.json").read_text()), expected)
        record["status"] = "VERIFIED"
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        record["failure"] = str(error)
        return 1
    finally:
        (args.output / "device-test.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"{args.proof}: {record['status']}; evidence: {args.output}")


if __name__ == "__main__":
    raise SystemExit(main())
