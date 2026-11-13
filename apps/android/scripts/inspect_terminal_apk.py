"""Inspect APK #7 actual bytes; signing/build evidence is not device execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from package_node import inspect, inspect_addon, inspect_executable
from package_profile import validate_archive, validate_host_qualification

ANDROID=Path(__file__).resolve().parents[1]
ROOT=ANDROID.parents[1]
SDK=Path(os.environ['ANDROID_HOME'])
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build-log',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert 'BUILD SUCCESSFUL' in args.build_log.read_text()
apk=ANDROID/'app/build/outputs/apk/debug/app-debug.apk'
test=ANDROID/'app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'
checks=[]
def run(*command):
    result=subprocess.run([str(x) for x in command],capture_output=True,text=True,check=True)
    checks.append(dict(command=[str(x) for x in command],exitCode=result.returncode,output=result.stdout+result.stderr))
    return result.stdout
certificates=[]
for file in [apk,test]:
    output=run(SDK/'build-tools/36.0.0/apksigner','verify','--print-certs',file)
    certificates.append(re.search(r'certificate SHA-256 digest: ([a-f0-9]+)',output)[1])
    run(SDK/'build-tools/36.0.0/zipalign','-c','-P','16','4',file)
assert certificates[0]==certificates[1]
badging=run(SDK/'build-tools/36.0.0/aapt','dump','badging',apk)
for token in ["versionCode='14'","versionName='0.1.13-original-terminal-proof'","sdkVersion:'29'","targetSdkVersion:'36'","native-code: 'arm64-v8a'"]:
    assert token in badging,token
xml=run(SDK/'build-tools/36.0.0/aapt','dump','xmltree',apk,'AndroidManifest.xml')
service=next(block for block in re.split(r'\n\s*E: service',xml) if 'TerminalProbeService' in block)
assert 'android:exported' in service and '(type 0x12)0x0' in service and ':terminalproof' in service
previous_record=json.loads((ANDROID/'evidence/runtime-node-pty-apk6-build.json').read_text())
previous=dict(previous_record['packagedLibraries'])
previous['libharness_process_probe.so']=previous_record['processProbe']
readelf=SDK/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf'
libraries={}
profile=ANDROID/'runtime/out/profile-v8'
manifest=json.loads((profile/'image-manifest.json').read_text())
assert manifest['terminalQualificationIncluded']
validate_archive(profile/'profile-image.zip',manifest)
validate_host_qualification(profile)
with zipfile.ZipFile(apk) as archive,tempfile.TemporaryDirectory(prefix='terminal-apk-inspect-') as temporary:
    names={Path(name).name for name in archive.namelist() if name.startswith('lib/')}
    assert names==set(previous),names
    for name in sorted(names):
        data=archive.read('lib/arm64-v8a/'+name)
        digest=hashlib.sha256(data).hexdigest()
        assert digest==previous[name]['sha256'], 'Native input changed: '+name
        target=Path(temporary)/name;target.write_bytes(data)
        dependencies=inspect(readelf,target,allow_node=True)
        if name in ['libharness_system.so','libharness_require_builtin.so','libharness_atomic.so','libharness_node_pty.so']:inspect_addon(readelf,target)
        if name=='libnode_executable.so':inspect_executable(readelf,target)
        if name in ['libharness_pty_fixture.so','libharness_process_probe.so']:
            header=run(readelf,'-h','-l','-W',target)
            assert 'Requesting program interpreter: /system/bin/linker64' in header
            assert int(re.search(r'Entry point address:\s*(0x[0-9a-fA-F]+)',header)[1],16)!=0
        libraries[name]=dict(sha256=digest,bytes=len(data),dependencies=sorted(dependencies),unchangedFromApk6=True)
    for license in (ANDROID/'licenses/third-party').iterdir():
        assert archive.read('assets/third-party/'+license.name)==license.read_bytes()
    for name in ['NODE_LICENSE','NDK_NOTICE','SYSTEM_ADDON_LICENSE','REQUIRE_BUILTIN_LICENSE','NODE_ADDON_API_LICENSE','LICENSE','THIRD_PARTY_NOTICES.md']:
        assert archive.read('assets/runtime/'+name)
    assert archive.read('assets/runtime/profile-image.zip')==(profile/'profile-image.zip').read_bytes()
    assert archive.read('assets/runtime/profile-image.sha256').decode()==hashlib.sha256((profile/'profile-image.zip').read_bytes()).hexdigest()
    build=json.loads(archive.read('assets/node-pty/build.json'))
    assert libraries['libharness_node_pty.so']['sha256']==build['binarySha256']
    assert libraries['libharness_pty_fixture.so']['sha256']==build['fixtureSha256']
    for name,digest in build['packageFilesSha256'].items():
        assert hashlib.sha256(archive.read('assets/node-pty/package/'+name)).hexdigest()==digest
sources=list((ANDROID/'app/src/main').rglob('*.kt'))+list((ANDROID/'app/src/main').rglob('*.java'))
sources+=[ANDROID/'app/build.gradle.kts',ANDROID/'app/src/main/AndroidManifest.xml']
record=dict(schemaVersion=1,date='2026-11-13',scope='APK #7 original registry + native-approved fixed terminal; physical execution pending',
    apkSha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [apk,test]},apkBytes={p.name:p.stat().st_size for p in [apk,test]},
    apkVersionCode=14,apkVersionName='0.1.13-original-terminal-proof',signingCertificateSha256=certificates[0],checks=checks,
    buildLogSha256=hashlib.sha256(args.build_log.read_bytes()).hexdigest(),packagedLibraries=libraries,
    profileImage=dict(sha256=hashlib.sha256((profile/'profile-image.zip').read_bytes()).hexdigest(),files=len(manifest['files']),
                      links=len(manifest['links']),hostQualificationSha256=hashlib.sha256((profile/'profile-qualification.json').read_bytes()).hexdigest(),
                      completeDependencyDistribution=False,excludedHostNative=manifest['excludedHostNative']),
    sourceFilesSha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    nativeHumanApprovalVerified=False,androidTerminalExecutionVerified=False,gate3Passed=False)
args.output.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:record[k] for k in ['apkSha256','apkBytes','signingCertificateSha256']},indent=2))
