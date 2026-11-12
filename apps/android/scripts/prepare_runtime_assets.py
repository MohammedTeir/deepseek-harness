"""Require inspected native runtime bytes; package fixed scripts and their notices."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

android = Path(__file__).resolve().parents[1]
metadata = android / 'runtime/out'
record = json.loads((metadata / 'runtime-build.json').read_text())
if 'libnode.so' not in record['sha256']:
    raise ValueError('Missing inspected libnode.so; run the runtime build and packager')
if record.get('systemNodeDependency') != 'libnode.so':
    raise ValueError('Missing verified Android addon Node dependency; rebuild the addon and run the packager')
if record.get('packagedNodeExecutable') != 'libnode_executable.so' or 'libnode_executable.so' not in record['sha256']:
    raise ValueError('Missing inspected Node executable; build it and run the packager')
for name, digest in record['sha256'].items():
    if name not in {'libnode.so', 'libc++_shared.so', 'libharness_system.so', 'libnode_executable.so'}:
        raise ValueError('Unexpected runtime library')
    native = android / 'app/src/main/jniLibs/arm64-v8a' / name
    if hashlib.sha256(native.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Inspected library changed: {name}')
output = Path(sys.argv[1]) / 'runtime'
if output.exists(): shutil.rmtree(output)
output.mkdir(parents=True)
for name in ['smoke.mjs', 'executable-smoke.mjs', 'child-node.mjs', 'proc-identity.mjs']:
    shutil.copy2(android / 'runtime' / name, output / name)
flock = android.parents[1] / 'native/system/packages/entry/lib/flock.js'
subprocess.run(['pnpm', '--dir', str(android.parents[1] / 'native/system'), 'build:ts'], check=True)
shutil.copy2(flock, output / 'harness-flock.mjs')
for name in ['NODE_LICENSE', 'NDK_NOTICE', 'ANDROID_CPU_FEATURES_NOTICE', 'SYSTEM_ADDON_LICENSE', 'runtime-build.json']:
    shutil.copy2(metadata / name, output / name)

for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
    shutil.copy2(android.parents[1] / name, output / name)
