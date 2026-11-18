"""Validate and stage native, qualification, and production web runtime assets."""
import hashlib
import json
import posixpath
from pathlib import Path
import shutil
import subprocess
import sys

ANDROID = Path(__file__).resolve().parents[1]
ROOT = ANDROID.parents[1]
WEB_RUNTIME_KIND = 'original-web-runtime-candidate'


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_android_web_runtime_manifest(manifest: dict) -> None:
    """Require the real Web CLI, Cordis overlays, provider and frontend package closure."""
    if manifest.get('schemaVersion') != 1 or manifest.get('imageKind') != WEB_RUNTIME_KIND:
        raise ValueError('APK web image must be an original-web production runtime image')
    files = manifest.get('files')
    links = manifest.get('links')
    if not isinstance(files, dict) or not isinstance(links, dict):
        raise ValueError('APK web image file/link manifests are malformed')
    if manifest.get('nativeArtifacts') != []:
        raise ValueError('Interpreted APK web image must not contain native artifacts')

    def require_file(path: str, description: str) -> None:
        if path not in files:
            raise ValueError(f'APK web image is missing {description}: {path}')

    def require_suffix(suffix: str, description: str) -> str:
        matches = [path for path in files if path.endswith(suffix)]
        if len(matches) != 1:
            raise ValueError(f'APK web image must contain exactly one {description}; found {len(matches)}')
        return matches[0]

    require_file('runtime/lib/bin.js', 'production dsh CLI entrypoint')
    require_file('web/index.html', 'pinned frontend asset root')
    packages = manifest.get('packages')
    if not isinstance(packages, list):
        raise ValueError('APK web image package records are malformed')

    def package_root(name: str, description: str) -> str:
        matches = [package for package in packages if package.get('name') == name]
        if len(matches) != 1 or not isinstance(matches[0].get('packagePath'), str):
            raise ValueError(f'APK web image must contain exactly one {description} package record')
        return matches[0]['packagePath']

    base_root = package_root('@deepseek-ai/dsh-base', 'dsh-base')
    web_app_root = package_root('@deepseek-ai/dsh-web-app', 'dsh-web-app')
    provider_root = package_root('@deepseek-ai/dsh-web-deepseek-api', 'web API provider')
    require_file(base_root + '/package.json', 'base package manifest')
    require_file(web_app_root + '/package.json', 'web-app package manifest')
    require_file(provider_root + '/package.json', 'web API provider package manifest')
    require_file(provider_root + '/lib/index.js', 'web API provider entrypoint')
    require_file(base_root + '/cordis.patch.yml', 'base Cordis overlay')
    require_file(web_app_root + '/cordis.patch.yml', 'web-app Cordis overlay')
    frontend_index = require_suffix('/node_modules/@deepseek-ai/dsh-web-frontend/dist/index.html', 'web frontend package index')
    require_suffix('/node_modules/@deepseek-ai/dsh-web-frontend/package.json', 'web frontend package manifest')

    required_aliases = {
        'runtime/node_modules/@deepseek-ai/dsh-base',
        'runtime/node_modules/@deepseek-ai/dsh-web-app',
    }
    missing_aliases = required_aliases - set(links)
    if missing_aliases:
        raise ValueError('APK web image is missing production bundle aliases: ' + ', '.join(sorted(missing_aliases)))

    provider_link = posixpath.join(posixpath.dirname(base_root), 'dsh-web-deepseek-api')
    provider_target = links.get(provider_link)
    if provider_target is None or posixpath.normpath(posixpath.join(posixpath.dirname(provider_link), provider_target)) != provider_root:
        raise ValueError('APK web image does not link dsh-base to its packaged web API provider')
    frontend_link = posixpath.join(posixpath.dirname(web_app_root), 'dsh-web-frontend')
    frontend_target = links.get(frontend_link)
    if frontend_target is None or posixpath.normpath(posixpath.join(posixpath.dirname(frontend_link), frontend_target)) + '/dist/index.html' != frontend_index:
        raise ValueError('APK web image does not link dsh-web-app to its packaged frontend dist')


def prepare_assets(destination: Path) -> None:
    metadata = ANDROID / 'runtime/out'
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
    atomic_source = ROOT / 'native/system/packages/entry/src/atomic_publish.c'
    if record.get('atomicSourceSha256') != sha256_file(atomic_source):
        raise ValueError('Atomic publication source changed; rebuild native assets')
    for name, digest in record['sha256'].items():
        if name not in {'libharness_atomic.so', 'libnode.so', 'libc++_shared.so', 'libharness_system.so', 'libnode_executable.so', 'libharness_require_builtin.so'}:
            raise ValueError('Unexpected runtime library')
        native = ANDROID / 'app/src/main/jniLibs/arm64-v8a' / name
        if sha256_file(native) != digest:
            raise ValueError(f'Inspected library changed: {name}')

    output = Path(destination) / 'runtime'
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    for name in ['smoke.mjs', 'executable-smoke.mjs', 'child-node.mjs', 'proc-identity.mjs']:
        shutil.copy2(ANDROID / 'runtime' / name, output / name)
    flock = ROOT / 'native/system/packages/entry/lib/flock.js'
    subprocess.run(['pnpm', '--dir', str(ROOT / 'native/system'), 'build:ts'], check=True)
    shutil.copy2(flock, output / 'harness-flock.mjs')
    for name in ['NODE_LICENSE', 'NDK_NOTICE', 'ANDROID_CPU_FEATURES_NOTICE', 'SYSTEM_ADDON_LICENSE', 'REQUIRE_BUILTIN_LICENSE', 'NODE_ADDON_API_LICENSE', 'require-builtin-build.json', 'atomic-build.json', 'runtime-build.json']:
        shutil.copy2(metadata / name, output / name)
    for name in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
        shutil.copy2(ROOT / name, output / name)

    sys.path.insert(0, str(ANDROID / 'scripts'))
    from package_profile import validate_archive, validate_host_qualification
    from package_web_runtime_image import validate_image_archive

    # Preserve the smaller, trace-backed sdk-minimal profile as its own qualification
    # target; it is not the complete production dependency tree used for the Web app.
    profile = ANDROID / 'runtime/out/profile-v9'
    validate_host_qualification(profile)
    profile_image = profile / 'profile-image.zip'
    profile_manifest = json.loads((profile / 'image-manifest.json').read_text())
    if profile_manifest.get('terminalQualificationIncluded') is not True:
        raise ValueError('Original terminal qualification image is required')
    for name, digest in profile_manifest['adapterSourcesSha256'].items():
        if sha256_file(ROOT / name) != digest:
            raise ValueError('Terminal adapter input changed; rebuild the observed image: ' + name)
    validate_archive(profile_image, profile_manifest)
    for name, digest in profile_manifest['files'].items():
        if name.startswith('node_modules/node-addon-require-builtin-android-arm64/'):
            source = ANDROID / 'runtime/require-builtin-carrier' / Path(name).name
        else:
            source = ROOT / name
        if sha256_file(source) != digest:
            raise ValueError(f'Original profile input changed: {name}; rebuild the image')

    # The Android Web button runs the full production tree. Fail asset preparation
    # if the provider, overlays, CLI root, or the web-app-to-frontend package link is absent.
    web_image = ANDROID / 'runtime/out/original-web-runtime-image.zip'
    web_report_path = ANDROID / 'runtime/out/original-web-runtime-image-build.json'
    web_report = json.loads(web_report_path.read_text())
    web_manifest = web_report.get('manifest')
    if not isinstance(web_manifest, dict):
        raise ValueError('Full production web image report has no embedded manifest')
    artifact = web_report.get('artifact', {})
    if artifact.get('sha256') != sha256_file(web_image) or artifact.get('bytes') != web_image.stat().st_size:
        raise ValueError('Full production web image does not match its build report')
    validate_android_web_runtime_manifest(web_manifest)
    validate_image_archive(web_image, web_manifest)
    shutil.copy2(web_image, output / 'profile-image.zip')
    (output / 'profile-image.sha256').write_text(sha256_file(web_image))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: prepare_runtime_assets.py <generated-assets-dir>')
    prepare_assets(Path(sys.argv[1]))
