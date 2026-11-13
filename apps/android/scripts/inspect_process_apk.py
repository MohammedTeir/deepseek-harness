"""Inspect Gate 3 APK/NDK fixture; compilation and signatures are not device proof."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from package_node import inspect

ANDROID = Path(__file__).resolve().parents[1]
ROOT = ANDROID.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build-log', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--subprocess-proof', action='store_true')
args = parser.parse_args()
base = ANDROID / 'runtime/out/process-base-inspection.json'
subprocess.run(['python3', str(ANDROID/'scripts/inspect_runtime_apk.py'), '--build-log', str(args.build_log),
                '--command-proof', '--output', str(base)], check=True)
record = json.loads(base.read_text())
assert record['apkVersionCode'] == (12 if args.subprocess_proof else 11)
assert record['apkVersionName'] == ('0.1.11-native-subprocess-proof' if args.subprocess_proof else '0.1.10-process-capability-proof')
previous = json.loads((ANDROID/'evidence/runtime-command-apk3-build.json').read_text())
for name, data in previous['packagedLibraries'].items():
    assert record['packagedLibraries'][name]['sha256'] == data['sha256'], name
sdk = Path(os.environ['ANDROID_HOME'])
readelf = sdk/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf'
apk = ANDROID/'app/build/outputs/apk/debug/app-debug.apk'
with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix='harness-process-inspect-') as temporary:
    name = 'libharness_process_probe.so'
    data = archive.read('lib/arm64-v8a/'+name)
    target = Path(temporary)/name
    target.write_bytes(data)
    dependencies = inspect(readelf, target)
    header = subprocess.check_output([str(readelf), '-h', '-l', '-W', str(target)], text=True)
    assert 'Requesting program interpreter: /system/bin/linker64' in header
    assert int(re.search(r'Entry point address:\s*(0x[0-9a-fA-F]+)', header)[1], 16) != 0
    assert b'--tty-child' in data and b'--ignore-term' in data and b'--tree-child' in data
    dex = b''.join(archive.read(n) for n in archive.namelist() if n.endswith('.dex'))
    assert b'ProcessCapabilityService' in dex
    assert archive.read('assets/runtime/NDK_NOTICE') == (sdk/'ndk/28.2.13676358/NOTICE').read_bytes()
    record['processProbe'] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
        'dependencies': sorted(dependencies), 'interpreter': '/system/bin/linker64', 'loadAlignmentAtLeast16384': True,
        'compiledApi': 29, 'ndk': '28.2.13676358', 'staticCppRuntime': True,
        'sourceSha256': hashlib.sha256((ANDROID/'execution/process-proof/process_probe.cpp').read_bytes()).hexdigest()}
record['observedDate'] = '2026-11-13'
record.pop('hostTests', None)
record.pop('originalProfileReference', None)
record['scope'] = 'APK #4 fixed process/shell/PTY OS qualification; not an original terminal provider'
if args.subprocess_proof:
    record['scope'] = 'APK #5 original SubprocessRuntime fixed-pwd adapter; phone execution pending'
    record['androidSubprocessAdapterExecuted'] = False
record['gate2NativeLibrariesUnchanged'] = True
record['gate3Passed'] = False
record['androidProcessProbeExecuted'] = False
record['originalTerminalIntegrated'] = False
record['sourceFilesSha256']['apps/android/execution/process-proof/process_probe.cpp'] = record['processProbe']['sourceSha256']
record['sourceFilesSha256']['apps/android/scripts/inspect_process_apk.py'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
args.output.write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'apkSha256': record['apkSha256'], 'apkBytes': record['apkBytes'], 'processProbe': record['processProbe']}, indent=2))
