"""Cross-compile checksum-pinned original require-builtin N-API source for Android.

Accept an existing upstream checkout and integrity-matched node-addon-api archive.
This performs no install hooks, source patching, offset overrides or Android tests.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile


def build(source, api_archive):
    """Verify source/header inputs and build an inspected ARM64/API 29 library."""
    runtime = Path(__file__).resolve().parent
    pin = json.loads((runtime / 'require-builtin-source.json').read_text())
    for name, digest in pin['sourceFiles'].items():
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Upstream source differs: {name}')
    integrity = 'sha512-'+base64.b64encode(hashlib.sha512(api_archive.read_bytes()).digest()).decode()
    if integrity != pin['nodeAddonApi']['integrity']:
        raise ValueError('node-addon-api archive integrity mismatch')
    ndk = Path(os.environ['ANDROID_NDK_HOME'])
    if 'Pkg.Revision = 28.2.13676358' not in (ndk/'source.properties').read_text():
        raise ValueError('NDK 28.2.13676358 required')
    build_root = Path(os.environ['ANDROID_NODE_BUILD_DIR']).resolve()
    if build_root.is_relative_to(runtime.parents[2]):
        raise ValueError('Keep third-party build inputs outside the checkout')
    node = build_root/'node-v24.22.1'
    toolchain = ndk/'toolchains/llvm/prebuilt/linux-x86_64'
    output = runtime/'out/require-builtin'
    output.mkdir(parents=True,exist_ok=True)
    with tarfile.open(api_archive) as tar:
        tar.extractall(build_root/'require-builtin-headers',filter='data')
    headers = build_root/'require-builtin-headers/package'
    sources = [source/name for name in pin['sourceFiles'] if name.endswith('.cc') and not name.endswith('runtime_compat_nodeabi.cc')]
    library = output/'libharness_require_builtin.so'
    command = [str(toolchain/'bin/aarch64-linux-android29-clang++'),'-std=c++17','-O2','-shared','-fPIC',
               '-fno-exceptions','-fvisibility=hidden','-Wall','-Wextra','-Wno-unused-parameter',
               '-DNAPI_VERSION=9','-DNARB_BACKEND=1','-DNARB_PRODUCT=1',
               '-DNODE_ADDON_API_DISABLE_CPP_EXCEPTIONS','-DNODE_GYP_MODULE_NAME=require_builtin',
               '-I',str(node/'src'),'-I',str(headers),*[str(p) for p in sources],
               '-Wl,-z,max-page-size=16384','-Wl,-z,defs','-L',str(node/'out/Release'),'-l:libnode.so','-ldl',
               '-o',str(library)]
    subprocess.run(command,check=True)
    report=subprocess.check_output([str(toolchain/'bin/llvm-readelf'),'-h','-l','-d','-W',str(library)],text=True)
    (output/'readelf.txt').write_text(report)
    shutil.copy2(source/'LICENSE',output/'REQUIRE_BUILTIN_LICENSE')
    shutil.copy2(headers/'LICENSE.md',output/'NODE_ADDON_API_LICENSE')
    record=dict(schemaVersion=1,sourceVersion=pin['version'],sourceFiles=pin['sourceFiles'],
                sourceGitRevision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),
                nodeAddonApiIntegrity=integrity,nodeVersion='24.22.1',target='aarch64-linux-android29',
                backend='napi',product='require-builtin',sourceModified=False,androidExecuted=False,
                sha256=hashlib.sha256(library.read_bytes()).hexdigest(),command=command)
    (output/'build.json').write_text(json.dumps(record,indent=2)+'\n')
    print(report)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('node_addon_api_archive',type=Path)
    args=parser.parse_args()
    build(args.source.resolve(),args.node_addon_api_archive.resolve())
