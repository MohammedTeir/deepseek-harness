"""Copy only the inspected original node-pty build and fixed fixture into APK inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ANDROID = Path(__file__).resolve().parents[1]
ROOT = ANDROID.parents[1]
def prepare(assets, native):
    source = ANDROID/'runtime/out/node-pty'
    record = json.loads((source/'build.json').read_text())
    package = ROOT/record['sourcePackage']
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(package/'src/unix/pty.cc') != record['sourceSha256'] or digest(ANDROID/'runtime/node-pty-proof/fixture.cpp') != record['fixtureSourceSha256']:
        raise ValueError('Node-pty/fixture source changed; rebuild original binding')
    if digest(ROOT/'patches/node-pty@1.2.0-beta.15.patch') != record['repositoryPatchSha256']:
        raise ValueError('Locked node-pty patch changed')
    for name, sha in record['packageFilesSha256'].items():
        if digest(source/'package'/name) != sha or digest(package/name) != sha:
            raise ValueError('Original package byte mismatch: '+name)
    for name, key in [('libharness_node_pty.so','binarySha256'),('libharness_pty_fixture.so','fixtureSha256')]:
        if digest(source/name) != record[key]: raise ValueError('Inspected native binary changed: '+name)
    assets = assets/'node-pty'; native = native/'arm64-v8a'
    if assets.exists(): shutil.rmtree(assets)
    assets.mkdir(parents=True); native.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source/'package',assets/'package')
    shutil.copy2(source/'build.json',assets/'build.json')
    shutil.copy2(package/'src/unix/pty.cc',assets/'original-pty.cc') # Includes borrowed ISC notices.
    shutil.copy2((package.parent/'node-addon-api').resolve()/'LICENSE.md',assets/'NODE_ADDON_API_LICENSE.md')
    for name in ['smoke.mjs','loader.cjs']:shutil.copy2(ANDROID/'runtime/node-pty-proof'/name,assets/name)
    shutil.copy2(ANDROID/'runtime/proc-identity.mjs',assets/'proc-identity.mjs')
    # Keep smoke's import local inside this dedicated extracted directory.
    smoke=assets/'smoke.mjs';smoke.write_text(smoke.read_text().replace("'../proc-identity.mjs'","'./proc-identity.mjs'"))
    for name in ['libharness_node_pty.so','libharness_pty_fixture.so']:shutil.copy2(source/name,native/name)

if __name__ == '__main__':prepare(Path(sys.argv[1]),Path(sys.argv[2]))
