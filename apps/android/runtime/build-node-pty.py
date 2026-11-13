"""Cross-build the locked, unmodified node-pty Unix source for Android API 29."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
ANDROID = ROOT/'apps/android'
ndk = Path(os.environ['ANDROID_NDK_HOME'])
assert 'Pkg.Revision = 28.2.13676358' in (ndk/'source.properties').read_text()
node = Path(os.environ['ANDROID_NODE_BUILD_DIR'])/'node-v24.22.1'
package = (ROOT/'packages/subprocess/subprocess-local/node_modules/node-pty').resolve(strict=True)
assert json.loads((package/'package.json').read_text())['version'] == '1.2.0-beta.15'
assert '9d30053266d0f39d3debe894c675867f6782da6bcadbc94a693b3cfb9eff8ed0' in str(package)
api = (package.parent/'node-addon-api').resolve(strict=True)
output = ANDROID/'runtime/out/node-pty'; output.mkdir(parents=True,exist_ok=True)
toolchain = ndk/'toolchains/llvm/prebuilt/linux-x86_64'
binary = output/'libharness_node_pty.so'
command = [str(toolchain/'bin/aarch64-linux-android29-clang++'),'-std=c++17','-O2','-fPIC','-shared','-fexceptions','-fstack-protector-strong','-DNAPI_CPP_EXCEPTIONS','-DNAPI_VERSION=8','-I'+str(api),'-I'+str(node/'src'),'-Wl,-z,max-page-size=16384','-Wl,-z,defs','-Wl,-z,relro,-z,now','-static-libstdc++',str(package/'src/unix/pty.cc'),'-L'+str(node/'out/Release'),'-l:libnode.so','-o',str(binary)]
subprocess.run(command,check=True)
fixture = output/'libharness_pty_fixture.so'
fixture_source = ANDROID/'runtime/node-pty-proof/fixture.cpp'
subprocess.run([str(toolchain/'bin/aarch64-linux-android29-clang++'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-fPIE','-pie','-static-libstdc++','-Wl,-z,max-page-size=16384','-Wl,-z,relro,-z,now',str(fixture_source),'-o',str(fixture)],check=True)
for artifact in [binary,fixture]:subprocess.run([str(toolchain/'bin/llvm-strip'),'--strip-unneeded',str(artifact)],check=True)
report = subprocess.check_output([str(toolchain/'bin/llvm-readelf'),'-h','-l','-d','-W',str(binary)],text=True)
assert 'AArch64' in report and 'libnode.so' in report
assert 'libutil.so' not in report and 'libc.so.6' not in report
(output/'readelf.txt').write_text(report)
files = {}
for source in sorted((package/'lib').glob('*.js')):
 destination = output/'package/lib'/source.name; destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
 files['lib/'+source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
for name in ['LICENSE','package.json']:
 shutil.copy2(package/name,output/'package'/name);files[name]=hashlib.sha256((package/name).read_bytes()).hexdigest()
record={'schemaVersion':1,'package':'node-pty','version':'1.2.0-beta.15','sourcePackage':str(package.relative_to(ROOT)),'sourceSha256':hashlib.sha256((package/'src/unix/pty.cc').read_bytes()).hexdigest(),'repositoryPatchSha256':hashlib.sha256((ROOT/'patches/node-pty@1.2.0-beta.15.patch').read_bytes()).hexdigest(),'nativeSourceModified':False,'ndk':'28.2.13676358','api':29,'arch':'arm64-v8a','command':command,'exitCode':0,'binarySha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'packageFilesSha256':files,'nodeAddonApiVersion':json.loads((api/'package.json').read_text())['version'],'strippedBeforeHash':True,'spawnHelperUsedOnAndroid':False,'fixtureSha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),'fixtureSourceSha256':hashlib.sha256(fixture_source.read_bytes()).hexdigest(),'androidExecutionVerified':False}
(output/'build.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
