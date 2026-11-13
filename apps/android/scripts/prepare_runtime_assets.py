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
if record.get('requireBuiltinNodeDependency') != 'libnode.so' or 'libharness_require_builtin.so' not in record['sha256']:
    raise ValueError('Missing inspected require-builtin addon; build and package it')
if record.get('atomicNodeDependency') != 'libnode.so' or 'libharness_atomic.so' not in record['sha256']:
    raise ValueError('Missing inspected atomic publication binding; build and package it')
if record.get('atomicSourceSha256') != hashlib.sha256((android.parents[1] / 'native/system/packages/entry/src/atomic_publish.c').read_bytes()).hexdigest():
    raise ValueError('Atomic publication source changed; rebuild native assets')
for name, digest in record['sha256'].items():
    if name not in {'libharness_atomic.so', 'libnode.so', 'libc++_shared.so', 'libharness_system.so', 'libnode_executable.so', 'libharness_require_builtin.so'}:
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
for name in ['NODE_LICENSE', 'NDK_NOTICE', 'ANDROID_CPU_FEATURES_NOTICE', 'SYSTEM_ADDON_LICENSE', 'REQUIRE_BUILTIN_LICENSE', 'NODE_ADDON_API_LICENSE', 'require-builtin-build.json', 'atomic-build.json', 'runtime-build.json']:
    shutil.copy2(metadata / name, output / name)

for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
    shutil.copy2(android.parents[1] / name, output / name)

from package_profile import validate_archive, validate_host_qualification
profile = android / 'runtime/out/profile-v8'
validate_host_qualification(profile)
image = profile / 'profile-image.zip'
manifest = json.loads((profile / 'image-manifest.json').read_text())
if manifest.get('terminalQualificationIncluded') is not True:
    raise ValueError('Original terminal qualification image is required')
for name, digest in manifest['adapterSourcesSha256'].items():
    if hashlib.sha256((android.parents[1]/name).read_bytes()).hexdigest() != digest:
        raise ValueError('Terminal adapter input changed; rebuild the observed image: '+name)
validate_archive(image, manifest)
for name, digest in manifest['files'].items():
    if name.startswith('node_modules/node-addon-require-builtin-android-arm64/'):
        source = android / 'runtime/require-builtin-carrier' / Path(name).name
    else:
        source = android.parents[1] / name
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Original profile input changed: {name}; rebuild the image')
shutil.copy2(image, output / 'profile-image.zip')
(output / 'profile-image.sha256').write_text(hashlib.sha256(image.read_bytes()).hexdigest())
