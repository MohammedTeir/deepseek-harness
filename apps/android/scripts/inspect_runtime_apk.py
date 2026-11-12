"""Inspect runtime APK bytes and original interpreted image; not device execution."""
import hashlib,json,re,subprocess,sys,tempfile,zipfile,os,argparse
from pathlib import Path
android=Path(__file__).resolve().parents[1]; root=android.parents[1]; sdk=Path(os.environ['ANDROID_HOME'])
parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--build-log',type=Path,required=True); parser.add_argument('--command-proof',action='store_true'); parser.add_argument('--output',type=Path,default=android/'runtime/out/runtime-apk-inspection.json'); args=parser.parse_args()
build_log=args.build_log.read_text(); assert 'BUILD SUCCESSFUL' in build_log
sys.path.insert(0,str(android/'scripts'))
from package_node import inspect,inspect_addon,inspect_executable
readelf=sdk/'ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf'
checks=[]
def run(*args):
 p=subprocess.run([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,check=True)
 checks.append(dict(command=[str(a) for a in args],exitCode=0,output=p.stdout))
 return p.stdout
apk=android/'app/build/outputs/apk/debug/app-debug.apk'; test=android/'app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk'
for file in [apk,test]:
 run(sdk/'build-tools/36.0.0/apksigner','verify',file)
 run(sdk/'build-tools/36.0.0/zipalign','-c','-P','16','4',file)
 with zipfile.ZipFile(file) as z:
  for license in (android/'licenses/third-party').iterdir():
   assert z.read('assets/third-party/'+license.name)==license.read_bytes()
badging=run(sdk/'build-tools/36.0.0/aapt','dump','badging',apk)
source_config = (android/'app/build.gradle.kts').read_text()
version_code = int(re.search(r'versionCode = (\d+)', source_config)[1])
version_name = re.search(r'versionName = "([^"]+)"', source_config)[1]
for token in [f"versionCode='{version_code}'",f"versionName='{version_name}'","sdkVersion:'29'","targetSdkVersion:'36'","native-code: 'arm64-v8a'"]: assert token in badging
libraries={}; assets={}
with zipfile.ZipFile(apk) as z,tempfile.TemporaryDirectory(prefix='android-v6-inspection-') as temp:
 for name in ['libnode.so','libharness_system.so','libnode_executable.so','libc++_shared.so','libharness_probe.so','libharness_require_builtin.so','libharness_atomic.so']:
  data=z.read('lib/arm64-v8a/'+name); path=Path(temp)/name; path.write_bytes(data)
  dependencies=inspect(readelf,path,allow_node=name in {'libharness_system.so','libnode_executable.so','libharness_require_builtin.so','libharness_atomic.so'})
  if name in {'libharness_system.so','libharness_require_builtin.so','libharness_atomic.so'}: inspect_addon(readelf,path)
  if name=='libnode_executable.so': inspect_executable(readelf,path)
  libraries[name]=dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),dependencies=sorted(dependencies),loadAlignmentAtLeast16384=True)
 for name in ['smoke.mjs','executable-smoke.mjs','child-node.mjs','proc-identity.mjs','harness-flock.mjs']:
  data=z.read('assets/runtime/'+name)
  source=root/'native/system/packages/entry/lib/flock.js' if name=='harness-flock.mjs' else android/'runtime'/name
  assert data==source.read_bytes()
  assets[name]=dict(sha256=hashlib.sha256(data).hexdigest(),source=str(source.relative_to(root)))
 for name in ['NODE_LICENSE','NDK_NOTICE','ANDROID_CPU_FEATURES_NOTICE','SYSTEM_ADDON_LICENSE','REQUIRE_BUILTIN_LICENSE','NODE_ADDON_API_LICENSE','require-builtin-build.json','atomic-build.json','LICENSE','THIRD_PARTY_NOTICES.md','runtime-build.json']: assert z.read('assets/runtime/'+name)
 assert b'upstream-system-entry' in z.read('assets/runtime/smoke.mjs')
 assert b"libharness_system.so" in z.read('assets/runtime/harness-flock.mjs')
record=dict(schemaVersion=1,observedDate='2026-11-12',environment='Linux x86_64 cloud host',scope='APK #2 original JSONL publication adapter; phone recovery not yet verified',apkBuild=dict(exitCode=0,summary=build_log[build_log.index('BUILD SUCCESSFUL'):].strip(),logSha256=hashlib.sha256(args.build_log.read_bytes()).hexdigest(),runtimeAssetsExcluded=False,kotlinCompilerStrategy='in-process'),apkVersionCode=version_code,apkVersionName=version_name,apkSha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [apk,test]},apkBytes={p.name:p.stat().st_size for p in [apk,test]},packagedLibraries=libraries,assets=assets,checks=checks,hostTests=dict(androidHostTests=27,originalHarnessRegressionTests=401,unchangedWindowsOnlySkippedTests=3,publicationEntryTests=4,elfMetadataAndProfileArchiveTests=19),originalProfileReference='host-atomic-persistence-reference.json',androidNativeInternalLoaderExecuted=False,harnessInitializedOnAndroid=False,gate2Passed=False)
assert record['apkBuild']['exitCode']==0
from package_profile import validate_archive
image = android/'runtime/out/profile-v7/profile-image.zip'
manifest = json.loads((image.parent/'image-manifest.json').read_text())
validate_archive(image,manifest)
with zipfile.ZipFile(apk) as z:
 assert z.read('assets/runtime/profile-image.zip')==image.read_bytes()
 assert z.read('assets/runtime/profile-image.sha256').decode()==hashlib.sha256(image.read_bytes()).hexdigest()
record['profileImage']=dict(sha256=hashlib.sha256(image.read_bytes()).hexdigest(),bytes=image.stat().st_size,
 files=len(manifest['files']),links=len(manifest['links']),packageManifests=len(manifest['packageManifests']),
 excludedHostNative=manifest['excludedHostNative'],completeDependencyDistribution=False)
record['requireBuiltin']=dict(version='0.1.9',backend='napi',sourceModified=False,androidExecuted=False,
 sourcePinSha256=hashlib.sha256((android/'runtime/require-builtin-source.json').read_bytes()).hexdigest(),
 sha256=hashlib.sha256((android/'runtime/out/require-builtin/libharness_require_builtin.so').read_bytes()).hexdigest())
source_files = [root/'tsconfig.base.json',root/'packages/session/session-persistence-jsonl/src/index.ts',root/'packages/session/session-persistence-jsonl/src/generation.ts',root/'packages/session/session-persistence-jsonl/lib/index.js',root/'native/system/packages/entry/src/publish.ts',root/'native/system/packages/entry/src/atomic_publish.c',root/'native/system/packages/entry/lib/publish.js',root/'native/system/packages/entry/package.json',root/'packages/sdk/client/src/client.ts', root/'packages/sdk/client/lib/index.js', android/'app/build.gradle.kts', android/'app/src/main/AndroidManifest.xml']
source_files += sorted((android/'app/src/androidTest').rglob('*.kt')) + sorted((android/'runtime/profile').glob('*.yml'))
source_files += sorted((android/'app/src/main').rglob('*.kt')) + sorted((android/'app/src/main').rglob('*.java'))
source_files += sorted((android/'scripts').glob('*.py'))
for pattern in ['*.py','*.mjs','*.json']:
 source_files += sorted((android/'runtime').glob(pattern))
source_files += sorted((android/'runtime/require-builtin-carrier').iterdir())
source_files += sorted((android/'runtime').glob('build-*.sh'))
record['sourceFilesSha256']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
record['hardlinkPrimitiveFailureEstablished']=True
record['vendorAvcCaptured']=False
record['atomicNativeBindingAndroidExecuted']=False
record['physicalMechanismReview']='atomic-poc-physical-review.json'
record['productionPublicationAdapterIntegrated']=True
record['hostShutdownFailureReference']='host-sdk-shutdown-failure.json'
record['atomicNativeBuild']=json.loads((android/'runtime/out/atomic/build.json').read_text())
record['hostQualificationSha256']=hashlib.sha256((image.parent/'profile-qualification.json').read_bytes()).hexdigest()
if args.command_proof:
 record['scope']='APK #3 original Harness registered-tool/native approval qualification; phone command execution pending'
 record.pop('hostTests')
 record['originalProfileReference']='host-command-profile-reference.json'
 record['hostQualificationScope']='Automated decision/transport fixture with real original pipeline and real Linux pwd; not Android/human evidence'
 record['commandQualificationSha256']=hashlib.sha256((image.parent/'command-relocated-result.json').read_bytes()).hexdigest()
 for name in ['command-plugin.mjs','command-smoke.mjs','command-wire.mjs']:
  assert 'apps/android/runtime/'+name in manifest['files']
 assert 'apps/android/runtime/profile/command-proof.patch.yml' in manifest['files']
args.output.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(apkSha256=record['apkSha256'],apkBytes=record['apkBytes']),indent=2))
