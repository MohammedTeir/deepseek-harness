"""Validate and stage a pinned cross-built Node library for the diagnostic APK."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


def inspect(readelf: Path, library: Path, *, allow_node: bool = False) -> set[str]:
    """Reject foreign ABIs, unaligned segments, and non-Android dependencies."""
    report = subprocess.check_output([str(readelf), "-h", "-l", "-d", "-W", str(library)], text=True)
    if not re.search(r"Machine:\s+AArch64", report) or not re.search(r"Type:\s+DYN", report):
        raise ValueError(f"Not an ARM64 shared library: {library}")
    segments = [line.split() for line in report.splitlines() if line.strip().startswith("LOAD ")]
    if not segments or any(int(line[-1], 16) < 16384 for line in segments):
        raise ValueError(f"Library lacks 16 KB LOAD alignment: {library}")
    dependencies = set(re.findall(r"\(NEEDED\).*\[([^]]+)\]", report))
    allowed = {"libc.so", "libm.so", "libdl.so", "liblog.so", "libc++_shared.so"}
    if allow_node:
        allowed.add("libnode.so")
    if dependencies - allowed:
        raise ValueError(f"Unreviewed dependencies: {sorted(dependencies - allowed)}")
    return dependencies


def inspect_addon(readelf: Path, addon: Path) -> None:
    """Require explicit Node linkage; RTLD_GLOBAL alone failed on the test phone."""
    if "libnode.so" not in inspect(readelf, addon, allow_node=True):
        raise ValueError("Android addon must declare libnode.so in DT_NEEDED")


def inspect_executable(readelf: Path, executable: Path) -> None:
    """Require an aligned Android PIE using the bundled Node provider."""
    inspect_addon(readelf, executable)
    report = subprocess.check_output([str(readelf), "-h", "-l", "-d", "-W", str(executable)], text=True)
    if "[Requesting program interpreter: /system/bin/linker64]" not in report or "$ORIGIN" not in report:
        raise ValueError("Node executable requires Android linker64 and ORIGIN search")
    entry = re.search(r"Entry point address:\s+0x([0-9a-fA-F]+)", report)
    if not entry or int(entry.group(1), 16) == 0:
        raise ValueError("Node executable has no entry point")


def package(build: Path, ndk: Path, android: Path) -> None:
    """Stage only inspected binaries and their required license records."""
    source = build / "node-v24.22.1"
    toolchain = ndk / "toolchains/llvm/prebuilt/linux-x86_64"
    readelf = toolchain / "bin/llvm-readelf"
    library = source / "out/Release/libnode.so"
    dependencies = inspect(readelf, library)
    symbols = subprocess.check_output([str(readelf), "--dyn-syms", "-W", str(library)], text=True)
    for symbol in ["_ZN4node5StartEiPPc", "napi_create_function"]:
        if not re.search(r"\bGLOBAL\b.*\bDEFAULT\b\s+(?!UND\b)\S+\s+" + re.escape(symbol) + r"\b", symbols):
            raise ValueError(f"Node required entry is missing: {symbol}")
    addon = android / "runtime/out/system/libharness_system.so"
    inspect_addon(readelf, addon)
    executable = android / "runtime/out/executable/libnode_executable.so"
    inspect_executable(readelf, executable)
    builtin = android / "runtime/out/require-builtin/libharness_require_builtin.so"
    inspect_addon(readelf, builtin)
    atomic = android / "runtime/out/atomic/libharness_atomic.so"
    inspect_addon(readelf, atomic)
    atomic_record = json.loads((android / "runtime/out/atomic/build.json").read_text())
    for key, path in [("sourceSha256", android.parents[1] / "native/system/packages/entry/src/atomic_publish.c"),
                      ("nativeSha256", atomic), ("nodeLibrarySha256", library)]:
        if atomic_record.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError(f"Stale atomic publication build: {key}")
    if atomic_record.get("minimumApi") != 29 or atomic_record.get("napiVersion") != 8:
        raise ValueError("Unqualified atomic publication ABI/API metadata")
    binaries = {"libharness_atomic.so": atomic, "libharness_require_builtin.so": builtin, "libnode.so": library, "libharness_system.so": addon, "libnode_executable.so": executable}
    if "libc++_shared.so" in dependencies:
        cpp = toolchain / "sysroot/usr/lib/aarch64-linux-android/libc++_shared.so"
        inspect(readelf, cpp)
        binaries[cpp.name] = cpp
    notices = {"NODE_LICENSE": source / "LICENSE",
               "ANDROID_CPU_FEATURES_NOTICE": source / "deps/zlib/ANDROID_CPU_FEATURES_NOTICE",
               "NDK_NOTICE": ndk / "NOTICE",
               "SYSTEM_ADDON_LICENSE": android / "runtime/out/system/LICENSE"}
    notices.update({name: android / "runtime/out/require-builtin" / name for name in ["REQUIRE_BUILTIN_LICENSE", "NODE_ADDON_API_LICENSE"]})
    for notice in notices.values():
        if not notice.is_file():
            raise ValueError(f"Missing license: {notice}")
    destination = android / "app/src/main/jniLibs/arm64-v8a"
    destination.mkdir(parents=True, exist_ok=True)
    metadata = android / "runtime/out"
    metadata.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, binary in binaries.items():
        shutil.copy2(binary, destination / name)
        hashes[name] = hashlib.sha256(binary.read_bytes()).hexdigest()
    for name, notice in notices.items():
        shutil.copy2(notice, metadata / name)
    shutil.copy2(android / "runtime/out/require-builtin/build.json", metadata / "require-builtin-build.json")
    shutil.copy2(android / "runtime/out/atomic/build.json", metadata / "atomic-build.json")
    record = {"nodeVersion": "24.22.1", "abi": "arm64-v8a", "minimumApi": 29,
              "nodeArchiveSha256": "4f5379796280cdaeb0c2f358fd04b6a16cc4fb7dfa83b5a8c91a9d963b435231",
              "systemSourceSha256": hashlib.sha256((android.parents[1] / "native/system/packages/entry/src/flock.c").read_bytes()).hexdigest(),
              "systemNodeDependency": "libnode.so",
              "atomicNodeDependency": "libnode.so",
              "atomicSourceSha256": hashlib.sha256((android.parents[1] / "native/system/packages/entry/src/atomic_publish.c").read_bytes()).hexdigest(),
              "requireBuiltinNodeDependency": "libnode.so",
              "packagedNodeExecutable": "libnode_executable.so",
              "deviceVerified": False, "harnessStarted": False, "sha256": hashes}
    (metadata / "runtime-build.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Staged inspected ARM64 libraries and licenses; Android execution remains unverified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--ndk", required=True, type=Path)
    args = parser.parse_args()
    package(args.build.resolve(), args.ndk.resolve(), Path(__file__).resolve().parents[1])
