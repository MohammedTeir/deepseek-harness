"""Build a reproducible host-side Original Web Runtime Image candidate.

This image contains the production CLI/Web Profile package deployment and the
pinned frontend static assets. It is not an Android boot or transport proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from urllib.parse import unquote
import zipfile
import zlib

from native_artifact_policy import load_policy, policy_sha256, validate_native_artifacts

ROOT = Path(__file__).resolve().parents[3]
ANDROID = ROOT / 'apps/android'
SPLIT_REPORT = ANDROID / 'evidence/original-web-p3a003-runtime-test-separation.json'
OUTPUT_REPORT = ANDROID / 'evidence/original-web-p3a006-image-build.json'
IMAGE_MANIFEST = 'web-runtime-image-manifest.json'
CARRIER_DIR = ANDROID / 'runtime/require-builtin-carrier'
DEPLOY_PACKAGE = '@deepseek-ai/dsh'
FRONTEND_PACKAGE = '@deepseek-ai/dsh-web-frontend'
SOURCE_INPUTS = [
    'package.json', 'pnpm-workspace.yaml', 'pnpm-lock.yaml',
    'apps/cli/package.json', 'packages/bundle/web-app/package.json', 'apps/web/package.json',
    'apps/android/runtime/native-artifact-policy.json',
    'apps/android/runtime/require-builtin-carrier/index.cjs',
    'apps/android/runtime/require-builtin-carrier/package.json',
    'apps/android/scripts/package_web_runtime_image.py',
    'apps/android/scripts/native_artifact_policy.py',
    'apps/android/evidence/original-web-p3a003-runtime-test-separation.json',
]
NATIVE_SUFFIXES = {'.node', '.so', '.dll', '.dylib', '.exe', '.pyd', '.a'}
SECRET_BASENAMES = {'.npmrc', '.credentials.yaml', '.credentials.json', '.netrc', 'id_rsa', 'id_ed25519'}
FORBIDDEN_PARTS = {'test', 'tests', '__tests__', 'fixture', 'fixtures', '__fixtures__'}
PACKAGE_MANAGER_METADATA = {
    'node_modules/.modules.yaml',
    'node_modules/.pnpm/lock.yaml',
    'node_modules/.pnpm-workspace-state-v1.json',
    'pnpm-lock.yaml',
    'pnpm-workspace.yaml',
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def text_file_contains(path: Path, needles: tuple[bytes, ...]) -> bool:
    """Scan text-like package files in bounded memory for leaked local checkout paths."""
    text_suffixes = {'.js', '.mjs', '.cjs', '.json', '.yaml', '.yml', '.md', '.txt', '.html', '.css',
                     '.ts', '.tsx', '.jsx', '.xml', '.sh', '.cmd', '.bat', '.ini', '.conf', '.json5'}
    if path.suffix.lower() not in text_suffixes:
        return False
    carry = b''
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            buffer = carry + block
            if any(needle in buffer for needle in needles):
                return True
            carry = buffer[-256:]
    return False


def normalize_workspace_comment_annotations(data: bytes, root: Path) -> tuple[bytes, list[str]]:
    """Normalize checkout paths only inside generated JS //#region annotation lines."""
    raw_root = root.resolve().as_posix().encode()
    encoded_root = workspace_store_token(root).encode()
    lines = data.splitlines(keepends=True)
    changed = []
    output = []
    for line_number, line in enumerate(lines, 1):
        updated = line
        if raw_root in line or encoded_root in line:
            if not line.lstrip().startswith(b'//#region'):
                raise ValueError(f'Checkout path occurs outside a generated JavaScript region comment (line {line_number})')
            if raw_root in updated:
                updated = updated.replace(raw_root, b'<WORKSPACE>')
                changed.append('absolute-checkout-prefix')
            if encoded_root in updated:
                updated = updated.replace(encoded_root, b'file++++WORKSPACE')
                changed.append('pnpm-encoded-checkout-prefix')
        output.append(updated)
    normalized = b''.join(output)
    if raw_root in normalized or encoded_root in normalized:
        raise ValueError('Checkout path remained after generated annotation normalization')
    return normalized, sorted(set(changed))


def safe_name(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '\\' in value or any(part in {'', '.', '..'} for part in value.split('/')):
        raise ValueError(f'Unsafe runtime image path: {value!r}')
    return value


def workspace_store_token(root: Path) -> str:
    """Return pnpm's encoded file: prefix for local workspace packages."""
    return 'file++++' + root.resolve().as_posix().lstrip('/').replace('/', '+')


def normalize_workspace_text(value: str, root: Path) -> str:
    """Remove checkout-specific absolute workspace prefixes from pnpm store paths."""
    return value.replace(workspace_store_token(root), 'file++++WORKSPACE')


def native_format(path: str, prefix: bytes) -> str | None:
    """Detect OS-native payloads by magic and conservative native suffixes."""
    suffix = PurePosixPath(path).suffix.lower()
    if prefix.startswith(b'\x7fELF'):
        return 'ELF'
    if prefix.startswith(b'MZ'):
        return 'PE/MZ'
    if prefix[:4] in {
        b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe',
        b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
    }:
        return 'Mach-O/FAT'
    if suffix in NATIVE_SUFFIXES:
        return 'native-suffix:' + suffix
    return None


def exclusion_reason(path: str, *, is_link: bool = False) -> str | None:
    normalized = path.lower()
    parts = PurePosixPath(normalized).parts
    base = PurePosixPath(normalized).name
    if base in SECRET_BASENAMES or base.startswith('.env'):
        return 'credential-or-local-config'
    if path in PACKAGE_MANAGER_METADATA or '/.bin/' in '/' + path or path.startswith('node_modules/.bin/'):
        return 'package-manager-metadata-or-command-shim'
    if (any(part in FORBIDDEN_PARTS for part in parts) or 'vitest' in normalized or 'observer' in base
            or base in {'capture_web_host_trace.py', 'audit_web_host_trace.py'}
            or base.endswith(('.spec.js', '.spec.mjs', '.spec.cjs', '.test.js', '.test.mjs', '.test.cjs'))):
        return 'test-fixture-or-test-runner'
    if PurePosixPath(path).suffix.lower() == '.map':
        return 'source-map'
    if is_link and not path:
        return 'invalid-symlink'
    return None


def _read_package_manifest(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f'Invalid staged package manifest {path}: {error}') from error
    if not isinstance(value, dict):
        raise ValueError(f'Package manifest is not an object: {path}')
    return value


def package_roots(stage: Path) -> list[tuple[str, Path, dict]]:
    """Enumerate actual pnpm virtual-store package roots, excluding nested examples."""
    roots: list[tuple[str, Path, dict]] = []
    virtual = stage / 'node_modules/.pnpm'
    if not virtual.is_dir():
        raise ValueError('Production deployment has no pnpm virtual store')
    for store_entry in sorted(virtual.iterdir(), key=lambda item: item.name):
        modules = store_entry / 'node_modules'
        if not modules.is_dir():
            continue
        for scope_or_package in sorted(modules.iterdir(), key=lambda item: item.name):
            if scope_or_package.is_symlink():
                continue
            children = sorted(scope_or_package.iterdir(), key=lambda item: item.name) if scope_or_package.name.startswith('@') and scope_or_package.is_dir() else [scope_or_package]
            for candidate in children:
                if candidate.is_symlink():
                    continue
                manifest = candidate / 'package.json'
                if not manifest.is_file() or manifest.is_symlink():
                    continue
                data = _read_package_manifest(manifest)
                name, version = data.get('name'), data.get('version')
                if isinstance(name, str) and isinstance(version, (str, int, float)):
                    rel = candidate.relative_to(stage).as_posix()
                    roots.append((f'{name}@{version}', candidate, data))
    # A package can be reachable in multiple peer contexts. Keep each path, but reject duplicate path records.
    paths = [path for _, path, _ in roots]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate package root while reading deployment')
    return roots


def normalize_workspace_dependency_specs(stage: Path, project_root: Path = ROOT) -> list[dict]:
    """Replace pnpm deploy's checkout-specific file URLs with verified exact package versions."""
    manifest_path = stage / 'package.json'
    manifest = _read_package_manifest(manifest_path)
    project_root = project_root.resolve(strict=True)
    changes = []
    for field in ('dependencies', 'optionalDependencies', 'peerDependencies'):
        dependencies = manifest.get(field, {})
        if not isinstance(dependencies, dict):
            raise ValueError(f'Invalid {field} in deployed root package.json')
        for name, spec in sorted(dependencies.items()):
            if not isinstance(spec, str) or '@file://' not in spec:
                continue
            marker = f'{name}@file://'
            if not spec.startswith(marker):
                raise ValueError(f'Unexpected package-manager file spec for {name}: {spec[:len(name) + 16]}')
            source_path = Path(unquote(spec[len(marker):])).resolve(strict=True)
            try:
                source_relative = source_path.relative_to(project_root).as_posix()
            except ValueError as error:
                raise ValueError(f'Workspace dependency resolves outside the pinned source root: {name}') from error
            source_manifest_path = source_path / 'package.json'
            installed_manifest_path = stage / 'node_modules' / name / 'package.json'
            if not source_manifest_path.is_file() or not installed_manifest_path.is_file():
                raise ValueError(f'Workspace dependency manifest missing for {name}')
            source_package = _read_package_manifest(source_manifest_path)
            installed_package = _read_package_manifest(installed_manifest_path)
            version = str(installed_package.get('version', ''))
            if source_package.get('name') != name or installed_package.get('name') != name:
                raise ValueError(f'Workspace dependency name mismatch for {name}')
            if not version or str(source_package.get('version')) != version:
                raise ValueError(f'Workspace source/deployment version mismatch for {name}')
            dependencies[name] = version
            changes.append({
                'field': field,
                'dependency': name,
                'normalizedVersion': version,
                'sourcePackagePath': source_relative,
                'sourcePackageManifestSha256': sha256_file(source_manifest_path),
                'installedPackageManifestSha256': sha256_file(installed_manifest_path),
            })
    if changes:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return sorted(changes, key=lambda item: (item['field'], item['dependency']))


def package_license_files(package_root: Path) -> list[Path]:
    patterns = ('LICENSE*', 'LICENCE*', 'NOTICE*', 'COPYING*', 'COPYRIGHT*', '*-OFL.txt')
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path for path in package_root.glob(pattern) if path.is_file() and not path.is_symlink())
    licenses_dir = package_root / 'licenses'
    if licenses_dir.is_dir() and not licenses_dir.is_symlink():
        for pattern in patterns:
            found.update(path for path in licenses_dir.glob(pattern) if path.is_file() and not path.is_symlink())
    return sorted(found, key=lambda path: path.as_posix())


def _stage_paths(stage: Path):
    """Walk without following links; the caller validates and serializes links itself."""
    for base, dirs, files in os.walk(stage, topdown=True, followlinks=False):
        base_path = Path(base)
        for name in sorted(list(dirs)):
            path = base_path / name
            if path.is_symlink():
                dirs.remove(name)
                yield path
        for name in sorted(files):
            yield base_path / name
        dirs.sort()


def collect_image_items(stage: Path, web_assets: list[dict], carrier_dir: Path,
                        project_root: Path = ROOT) -> tuple[dict[str, Path], dict[str, str], list[dict], list[dict], dict]:
    """Select production files and symlinks, recording every excluded native/forbidden input."""
    stage = stage.resolve(strict=True)
    files: dict[str, Path] = {}
    links: dict[str, str] = {}
    exclusions: list[dict] = []
    native_exclusions: list[dict] = []
    reason_counts: dict[str, int] = {}
    encoded_prefix = workspace_store_token(project_root)
    path_needles = (project_root.resolve().as_posix().encode(), encoded_prefix.encode())
    content_path_normalizations = []
    normalized_content_dir = stage.parent / 'normalized-workspace-annotations'

    for source in _stage_paths(stage):
        rel = source.relative_to(stage).as_posix()
        normalized_rel = normalize_workspace_text(rel, project_root)
        if rel in PACKAGE_MANAGER_METADATA or normalized_rel in PACKAGE_MANAGER_METADATA:
            exclusions.append({'path': 'runtime/' + normalized_rel, 'reason': 'package-manager-metadata'})
            reason_counts['package-manager-metadata'] = reason_counts.get('package-manager-metadata', 0) + 1
            continue
        # Package-manager metadata is not runtime content; keep generated CLI links out of the image.
        if rel.startswith('node_modules/.bin/') or '/.bin/' in '/' + rel:
            exclusions.append({'path': 'runtime/' + normalized_rel, 'reason': 'package-manager-command-shim'})
            reason_counts['package-manager-command-shim'] = reason_counts.get('package-manager-command-shim', 0) + 1
            continue
        relative_image_path = safe_name('runtime/' + normalized_rel)
        reason = exclusion_reason(normalized_rel, is_link=source.is_symlink())
        if source.is_symlink():
            target_text = os.readlink(source)
            normalized_target = normalize_workspace_text(target_text, project_root)
            try:
                resolved = source.resolve(strict=True)
                resolved.relative_to(stage)
            except (OSError, ValueError) as error:
                raise ValueError(f'Broken or escaping production symlink: {rel} -> {target_text}') from error
            if not reason and resolved.is_file():
                with resolved.open('rb') as target_stream:
                    target_prefix = target_stream.read(8)
                target_format = native_format(resolved.name, target_prefix)
                if target_format:
                    reason = 'symlink-to-native-binary'
                    native_exclusions.append({
                        'path': relative_image_path,
                        'sha256': sha256_file(resolved),
                        'bytes': resolved.stat().st_size,
                        'format': target_format,
                        'decision': 'excluded-default-deny-no-approved-web-image-native-artifacts',
                        'symlinkTarget': normalized_target,
                    })
            if reason:
                exclusions.append({'path': relative_image_path, 'reason': reason, 'linkTarget': normalized_target})
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
                continue
            target_path = PurePosixPath(normalized_target)
            resolved_target = posixpath.normpath(posixpath.join(PurePosixPath(relative_image_path).parent.as_posix(), normalized_target))
            if target_path.is_absolute() or resolved_target == '..' or resolved_target.startswith('../'):
                raise ValueError(f'Unsafe symlink in production deployment: {rel} -> {target_text}')
            if relative_image_path in files or relative_image_path in links:
                raise ValueError(f'Normalized image path collision: {relative_image_path}')
            links[relative_image_path] = normalized_target
            continue

        with source.open('rb') as stream:
            prefix = stream.read(8)
        data_digest = sha256_file(source)
        if prefix.startswith(b'\x7fELF') or prefix.startswith(b'MZ') or prefix[:4] in {
            b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe',
            b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
        } or PurePosixPath(normalized_rel).suffix.lower() in NATIVE_SUFFIXES:
            record = {
                'path': relative_image_path,
                'sha256': data_digest,
                'bytes': source.stat().st_size,
                'format': native_format(normalized_rel, prefix),
                'decision': 'excluded-default-deny-no-approved-web-image-native-artifacts',
            }
            native_exclusions.append(record)
            reason_counts['native-binary'] = reason_counts.get('native-binary', 0) + 1
            continue
        if reason:
            exclusions.append({'path': relative_image_path, 'reason': reason, 'sha256': data_digest, 'bytes': source.stat().st_size})
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            continue
        if text_file_contains(source, path_needles):
            original_data = source.read_bytes()
            normalized_data, rules = normalize_workspace_comment_annotations(original_data, project_root)
            normalized_source = normalized_content_dir / relative_image_path
            normalized_source.parent.mkdir(parents=True, exist_ok=True)
            normalized_source.write_bytes(normalized_data)
            if text_file_contains(normalized_source, path_needles):
                raise ValueError(f'Checkout-specific workspace path remains in runtime file: {relative_image_path}')
            content_path_normalizations.append({
                'imagePath': relative_image_path,
                'sourceSha256': sha256_bytes(original_data),
                'normalizedSha256': sha256_bytes(normalized_data),
                'bytes': len(normalized_data),
                'rules': rules,
                'scope': 'generated-JavaScript-region-comment-only',
            })
            files[relative_image_path] = normalized_source
            continue
        if relative_image_path in files or relative_image_path in links:
            raise ValueError(f'Normalized image path collision: {relative_image_path}')
        files[relative_image_path] = source

    package_records = []

    def add_package(identity: str, package_root: Path, metadata: dict, stage_relative_root: str) -> None:
        normalized_root = normalize_workspace_text(stage_relative_root, project_root)
        image_package_root = 'runtime' if not normalized_root else 'runtime/' + normalized_root
        manifest_path = safe_name(image_package_root + '/package.json')
        if not metadata.get('license'):
            raise ValueError(f'Production package has no declared license identifier: {identity}')
        licenses = []
        for license_path in package_license_files(package_root):
            normalized_license = normalize_workspace_text(license_path.relative_to(stage).as_posix(), project_root)
            image_path = safe_name('runtime/' + normalized_license)
            if image_path not in files:
                # Include legal notices even when the package's publish allowlist omitted them.
                files[image_path] = license_path
            licenses.append({'path': image_path, 'sha256': sha256_file(license_path)})
        package_records.append({
            'identity': identity,
            'name': metadata.get('name'),
            'version': str(metadata.get('version')),
            'license': metadata.get('license'),
            'packagePath': image_package_root,
            'licenseMetadataPath': manifest_path,
            'licenseMetadataSha256': sha256_file(package_root / 'package.json'),
            'licenseFiles': licenses,
        })

    root_manifest = stage / 'package.json'
    if root_manifest.is_file():
        root_package = _read_package_manifest(root_manifest)
        if root_package.get('name') and root_package.get('version'):
            add_package(f"{root_package['name']}@{root_package['version']}", stage, root_package, '')
    for identity, package_root, metadata in package_roots(stage):
        add_package(identity, package_root, metadata, package_root.relative_to(stage).as_posix())
    identities = {item['name'] for item in package_records}
    if DEPLOY_PACKAGE not in identities:
        raise ValueError(f'Production deployment omitted its root package {DEPLOY_PACKAGE}')
    if '@deepseek-ai/dsh-web-app' not in identities:
        raise ValueError('Production deployment omitted the Original Web Profile bundle package')

    # Add the Android-only JS carrier: its shared object is supplied by the APK and is not in this image.
    carrier_files = sorted(path for path in carrier_dir.iterdir() if path.is_file() and not path.is_symlink())
    if not carrier_files:
        raise ValueError('Android require-builtin carrier input is missing')
    for source in carrier_files:
        image_path = safe_name('runtime/node_modules/node-addon-require-builtin-android-arm64/' + source.name)
        if native_format(source.name, source.read_bytes()[:8]):
            raise ValueError('Native code must not be embedded in the interpreted Web Runtime Image')
        files[image_path] = source

    for rel, asset in sorted((item['path'], item) for item in web_assets):
        prefix = 'apps/web/dist/'
        if not rel.startswith(prefix):
            raise ValueError(f'Frontend asset is outside the pinned dist root: {rel}')
        source = project_root / rel
        if not source.is_file() or source.is_symlink():
            raise ValueError(f'Pinned frontend asset is missing or a symlink: {rel}')
        digest = sha256_file(source)
        if digest != asset['sha256']:
            raise ValueError(f'Frontend asset hash changed since P3A-003: {rel}')
        image_path = safe_name('web/' + rel[len(prefix):])
        if PurePosixPath(image_path).suffix.lower() == '.map' or '/preview/' in image_path or image_path.startswith('web/preview'):
            raise ValueError(f'Forbidden frontend output was listed as production: {rel}')
        files[image_path] = source

    project_licenses = []
    for source, destination in [
        (project_root / 'LICENSE', 'licenses/project/LICENSE'),
        (project_root / 'THIRD_PARTY_NOTICES.md', 'licenses/project/THIRD_PARTY_NOTICES.md'),
    ]:
        if not source.is_file():
            raise ValueError(f'Required project license evidence missing: {source}')
        files[safe_name(destination)] = source
        project_licenses.append({'path': destination, 'sha256': sha256_file(source)})

    # The production lockfile's workspace identifiers contain this machine's checkout path.
    # It is an input hash, not a runtime file; all runtime references are normalized above.
    if any(encoded_prefix in link for link in links.values()):
        raise ValueError('Workspace path normalization failed for symlink targets')
    return files, links, exclusions, native_exclusions, {
        'packages': sorted(package_records, key=lambda item: (item['name'], item['version'], item['packagePath'])),
        'packageManifestCount': len(package_records),
        'uniquePackageIdentityCount': len({item['identity'] for item in package_records}),
        'packageIdentitySetSha256': sha256_bytes('\n'.join(sorted({item['identity'] for item in package_records})).encode()),
        'licenseManifest': {
            'schemaVersion': 1,
            'projectFiles': project_licenses,
            'packageCount': len(package_records),
            'packagesWithDeclaredLicense': sum(bool(item['license']) for item in package_records),
            'packagesWithLicenseFiles': sum(bool(item['licenseFiles']) for item in package_records),
            'packagesMissingLicenseFiles': [item['identity'] for item in package_records if not item['licenseFiles']],
            'packageLicenseEvidence': [
                {'identity': item['identity'], 'license': item['license'],
                 'metadataPath': item['licenseMetadataPath'], 'metadataSha256': item['licenseMetadataSha256'],
                 'noticeFiles': item['licenseFiles']}
                for item in sorted(package_records, key=lambda record: (record['name'], record['version'], record['packagePath']))
            ],
            'frontendOflAssets': [path for path in sorted(files) if path.startswith('web/') and 'ofl' in Path(path).name.lower()],
        },
        'exclusionReasonCounts': reason_counts,
        'contentPathNormalizations': sorted(content_path_normalizations, key=lambda item: item['imagePath']),
    }


def validate_image_archive(archive_path: Path, manifest: dict) -> None:
    """Verify exact archive contents, paths, hashes, symlinks, policy and negative conditions."""
    policy = load_policy()
    if manifest.get('nativePolicySha256') != policy_sha256():
        raise ValueError('Native artifact policy digest mismatch')
    if policy.get('approvedArtifacts'):
        raise ValueError('P3A-006 image generation requires an empty default-deny native allowlist')
    validate_native_artifacts(manifest.get('nativeArtifacts'), policy, set(manifest.get('files', {})))
    files = manifest.get('files')
    links = manifest.get('links')
    file_bytes = manifest.get('fileBytes')
    file_modes = manifest.get('fileModes')
    if not isinstance(files, dict) or not isinstance(links, dict) or not isinstance(file_bytes, dict) or not isinstance(file_modes, dict):
        raise ValueError('Image file/link manifests are malformed')
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        expected = set(files) | set(links) | {IMAGE_MANIFEST}
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError('Web Runtime Image archive entries differ from its manifest')
        if json.loads(archive.read(IMAGE_MANIFEST)) != manifest:
            raise ValueError('Embedded Web Runtime Image manifest is inconsistent')
        for name, digest in files.items():
            safe_name(name)
            info = archive.getinfo(name)
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise ValueError(f'Expected regular file but found symlink entry: {name}')
            if ((info.external_attr >> 16) & 0o777) != file_modes.get(name):
                raise ValueError(f'Runtime image file mode mismatch: {name}')
            data = archive.read(name)
            if len(data) != file_bytes.get(name):
                raise ValueError(f'Runtime image file size mismatch: {name}')
            if sha256_bytes(data) != digest:
                raise ValueError(f'Runtime image file hash mismatch: {name}')
            if native_format(name, data[:8]):
                raise ValueError(f'Native/host binary included in interpreted image: {name}')
            if exclusion_reason(name.removeprefix('runtime/')):
                raise ValueError(f'Forbidden file included in runtime image: {name}')
        for name, target in links.items():
            safe_name(name)
            info = archive.getinfo(name)
            if ((info.external_attr >> 16) & 0o170000) != stat.S_IFLNK:
                raise ValueError(f'Expected symlink archive entry: {name}')
            if archive.read(name).decode('utf-8') != target:
                raise ValueError(f'Runtime symlink target mismatch: {name}')
            normalized = posixpath.normpath(posixpath.join(PurePosixPath(name).parent.as_posix(), target))
            if PurePosixPath(target).is_absolute() or normalized == '..' or normalized.startswith('../'):
                raise ValueError(f'Runtime symlink escapes image root: {name} -> {target}')
            if not any(candidate == normalized or candidate.startswith(normalized.rstrip('/') + '/') for candidate in set(files) | set(links)):
                raise ValueError(f'Runtime symlink target is not present in the image: {name} -> {target}')
        if any(name.lower().endswith('.map') or '/preview/' in name.lower() for name in names):
            raise ValueError('Source maps or preview assets entered the Web Runtime Image')
        license_manifest = manifest.get('licenseManifest', {})
        for item in license_manifest.get('projectFiles', []):
            if item['path'] not in files or files[item['path']] != item['sha256']:
                raise ValueError('Project license file missing from the image manifest')
        for package in manifest.get('packages', []):
            if package.get('licenseMetadataPath') not in files or files[package['licenseMetadataPath']] != package.get('licenseMetadataSha256'):
                raise ValueError('Package license identifier is not bound to an included package.json')
            if not package.get('license'):
                raise ValueError('Package license identifier is missing from the image manifest')
            for license_file in package.get('licenseFiles', []):
                if files.get(license_file['path']) != license_file['sha256']:
                    raise ValueError('Package license file missing or changed in the image')


def write_deterministic_archive(output: Path, files: dict[str, Path], links: dict[str, str], manifest: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f'Output archive already exists: {output}')
    canonical_manifest = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.comment = b''
        for name in sorted(files):
            source = files[name]
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = source.stat().st_mode & 0o777
            info.external_attr = (stat.S_IFREG | (mode or 0o644)) << 16
            info.extra = b''
            info.comment = b''
            with source.open('rb') as input_stream, archive.open(info, 'w', force_zip64=True) as output_stream:
                shutil.copyfileobj(input_stream, output_stream, 1024 * 1024)
        for name in sorted(links):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            info.extra = b''
            info.comment = b''
            archive.writestr(info, links[name].encode('utf-8'))
        info = zipfile.ZipInfo(IMAGE_MANIFEST, date_time=(1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        info.extra = b''
        info.comment = b''
        archive.writestr(info, canonical_manifest, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_p3a003_inputs(report: dict, root: Path) -> None:
    for path, expected in report.get('inputs', {}).items():
        source = root / path
        if not source.is_file() or sha256_file(source) != expected:
            raise ValueError(f'P3A-003 pinned input changed: {path}')


def forbidden_runtime_package_names(packages: list[dict], report: dict) -> list[str]:
    """Return any installed production package matching the P3A-003 test/tool deny list."""
    denied = set(report['dependencyRoles']['testAndBuildToolNamesAbsentFromProductionTrees'])
    present = {item.get('name') for item in packages}
    return sorted(denied & present)


def runtime_environment(root: Path) -> tuple[str, str]:
    node = shutil.which('node')
    pnpm = shutil.which('pnpm')
    if not node or not pnpm:
        raise ValueError('Node.js 24 and pnpm are required to build the Web Runtime Image')
    node_version = subprocess.check_output([node, '--version'], text=True).strip()
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', node_version)
    if not match or (int(match.group(1)), int(match.group(2))) < (24, 9):
        raise ValueError(f'Node.js >=24.9.0 is required; found {node_version}')
    package = json.loads((root / 'package.json').read_text())
    expected_pnpm = package.get('packageManager', '').removeprefix('pnpm@')
    pnpm_version = subprocess.check_output([pnpm, '--version'], text=True).strip()
    if pnpm_version != expected_pnpm:
        raise ValueError(f'Pinned pnpm {expected_pnpm} required; found {pnpm_version}')
    return node_version, pnpm_version


def run_command(args: list[str], root: Path, env: dict[str, str], timeout: int = 1800) -> str:
    result = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        tail = (result.stdout + '\n' + result.stderr)[-6000:]
        raise RuntimeError(f'Command failed ({result.returncode}): {args!r}\n{tail}')
    return result.stdout + result.stderr


def git_state(root: Path) -> dict:
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    status = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True, check=True).stdout
    return {'revision': revision, 'worktreeDirty': bool(status.strip()), 'statusSha256': sha256_bytes(status.encode())}


def build(output: Path, report_path: Path = OUTPUT_REPORT, *, run_builds: bool = True,
          root: Path = ROOT, timeout: int = 1800) -> dict:
    """Build the production CLI package deployment, combine pinned UI assets, and audit it."""
    output = output.resolve()
    if output.exists():
        raise ValueError(f'Output archive must not already exist: {output}')
    node_version, pnpm_version = runtime_environment(root)
    p3a003 = json.loads(SPLIT_REPORT.read_text(encoding='utf-8'))
    verify_p3a003_inputs(p3a003, root)
    web_assets = p3a003['frontendStaticAssetAnalysis']['productionAssets']
    if len(web_assets) != p3a003['frontendStaticAssetAnalysis']['productionAssetCount']:
        raise ValueError('P3A-003 frontend asset inventory count mismatch')
    env = dict(os.environ)
    env['npm_config_force_legacy_deploy'] = 'true'
    logs = []
    if run_builds:
        logs.append(run_command(['pnpm', 'run', 'build:lib'], root, env))
        logs.append(run_command(['pnpm', '--filter', FRONTEND_PACKAGE, 'run', 'build'], root, env))
    with tempfile.TemporaryDirectory(prefix='dsh-web-runtime-image-') as temporary:
        stage = Path(temporary) / 'production-deploy'
        command = ['pnpm', '--filter', DEPLOY_PACKAGE, 'deploy', '--prod', '--ignore-scripts', str(stage)]
        logs.append(run_command(command, root, env))
        workspace_dependency_normalization = normalize_workspace_dependency_specs(stage, root)
        files, links, exclusions, native_exclusions, package_meta = collect_image_items(stage, web_assets, CARRIER_DIR, root)
        p3a003_forbidden = forbidden_runtime_package_names(package_meta['packages'], p3a003)
        if p3a003_forbidden:
            raise ValueError('Development/test package entered deployment: ' + ', '.join(p3a003_forbidden))
        files_manifest = {name: sha256_file(path) for name, path in sorted(files.items())}
        sizes = {name: path.stat().st_size for name, path in sorted(files.items())}
        modes = {name: path.stat().st_mode & 0o777 for name, path in sorted(files.items())}
        portable_binary_assets = []
        for name, path in sorted(files.items()):
            with path.open('rb') as source:
                prefix = source.read(8)
            if PurePosixPath(name).suffix.lower() == '.wasm' or prefix[:4] == b'\x00asm':
                portable_binary_assets.append({'path': name, 'sha256': files_manifest[name], 'bytes': sizes[name], 'format': 'WebAssembly-non-native'})
        source_inputs = {name: sha256_file(root / name) for name in SOURCE_INPUTS}
        source_inputs['apps/android/evidence/original-web-p3a003-runtime-test-separation.json'] = sha256_file(SPLIT_REPORT)
        git = git_state(root)
        manifest = {
            'schemaVersion': 1,
            'imageKind': 'original-web-runtime-candidate',
            'status': 'host-built-candidate-not-android-boot-verified',
            'productionRoot': DEPLOY_PACKAGE,
            'productionInstallMode': 'pnpm deploy --prod --ignore-scripts',
            'workspaceDependencyNormalization': {
                'method': 'absolute-pnpm-file-url-to-verified-exact-installed-version',
                'count': len(workspace_dependency_normalization),
                'records': workspace_dependency_normalization,
            },
            'contentPathNormalizations': package_meta['contentPathNormalizations'],
            'buildCommands': [
                'pnpm run build:lib',
                f'pnpm --filter {FRONTEND_PACKAGE} run build',
                f'pnpm --filter {DEPLOY_PACKAGE} deploy --prod --ignore-scripts <isolated-output-dir>',
            ],
            'packageManager': {'node': node_version, 'pnpm': pnpm_version},
            'archiveToolchain': {
                'python': platform.python_version(),
                'pythonRuntime': sys.version.split()[0],
                'zipCompression': 'ZIP_DEFLATED level 9',
                'zlib': zlib.ZLIB_VERSION,
            },
            'source': {
                **git,
                'inputSha256': source_inputs,
                'p3a003SplitReportSha256': sha256_file(SPLIT_REPORT),
                'productionTreePackageIdentitySetSha256': p3a003['productionPackageTrees']['cli']['packageIdentitySetSha256'],
                'workspacePathNormalization': 'file++++WORKSPACE/<workspace-relative-package-path>',
            },
            'files': files_manifest,
            'fileBytes': sizes,
            'fileModes': modes,
            'links': dict(sorted(links.items())),
            'packages': package_meta['packages'],
            'packageManifestCount': package_meta['packageManifestCount'],
            'uniquePackageIdentityCount': package_meta['uniquePackageIdentityCount'],
            'packageIdentitySetSha256': package_meta['packageIdentitySetSha256'],
            'developmentTestBuildPackagesPresent': p3a003_forbidden,
            'frontend': {
                'sourceBuildCommand': f'pnpm --filter {FRONTEND_PACKAGE} run build',
                'sourceAssetCount': len(web_assets),
                'includedAssetCount': sum(name.startswith('web/') for name in files),
                'sourceIndexSha256': p3a003['frontendStaticAssetAnalysis']['indexSha256'],
                'excludedPreviewOrSourceMapCount': p3a003['frontendStaticAssetAnalysis']['excludedPreviewOrSourceMapCount'],
                'excludedPreviewOrSourceMaps': p3a003['frontendStaticAssetAnalysis']['excludedPreviewOrSourceMaps'],
                'unreferencedByIndexButIncludedCount': len(p3a003['frontendStaticAssetAnalysis']['unreferencedByIndexButIncludedInBuildOutput']),
                'sourceAssets': [{'source': item['path'], 'imagePath': 'web/' + item['path'].removeprefix('apps/web/dist/'), 'sha256': item['sha256']} for item in web_assets],
            },
            'licenseManifest': package_meta['licenseManifest'],
            'nativePolicySha256': policy_sha256(),
            'nativeArtifacts': [],
            'excludedNativeArtifacts': native_exclusions,
            'portableBinaryAssets': portable_binary_assets,
            'excludedInputSummary': {
                'byReason': package_meta['exclusionReasonCounts'],
                'forbiddenPathExamples': [item for item in exclusions if item['reason'] == 'test-fixture-or-test-runner'][:100],
                'sourceMapCount': package_meta['exclusionReasonCounts'].get('source-map', 0),
                'credentialOrLocalConfigCount': package_meta['exclusionReasonCounts'].get('credential-or-local-config', 0),
                'nativeArtifactCount': len(native_exclusions),
            },
            'excludedInputs': exclusions,
            'claims': {
                'androidExecuted': False,
                'androidWebRuntimeImageBooted': False,
                'originalBootFacadeInjected': False,
                'secureTransportEnabled': False,
                'spaFallbackImplemented': False,
                'completeDependencyClosureProven': False,
                'gate4Passed': False,
            },
            'limitations': [
                'This host-built production package/static-asset image is not Android runtime boot evidence.',
                'Static frontend assets do not include the original Web boot facade, live transport, or SPA server wiring.',
                'All OS-native binaries were excluded under the empty default-deny Android native policy; native dependencies are not qualified by this image.',
                'P3A-007 must boot the authentic Web Profile on Android; P3A-004 remains open until exact image-native closure evidence is complete.',
            ],
        }
        validate_native_artifacts([], load_policy(), set(files_manifest))
        write_deterministic_archive(output, files, links, manifest)
        validate_image_archive(output, manifest)
        report = {
            'schemaVersion': 1,
            'task': 'P3A-006',
            'status': 'candidate-generated-host-only',
            'artifact': {
                'path': output.relative_to(root).as_posix() if output.is_relative_to(root) else output.name,
                'sha256': sha256_file(output),
                'bytes': output.stat().st_size,
                'manifestSha256': sha256_bytes(json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')),
                'includedFileCount': len(files_manifest),
                'includedSymlinkCount': len(links),
                'productionPackageManifestCount': len(package_meta['packages']),
                'uniquePackageIdentityCount': package_meta['uniquePackageIdentityCount'],
                'normalizedWorkspaceDependencyCount': len(workspace_dependency_normalization),
                'normalizedContentPathFileCount': len(package_meta['contentPathNormalizations']),
                'nativeArtifactCount': 0,
                'excludedNativeArtifactCount': len(native_exclusions),
                'portableBinaryAssetCount': len(portable_binary_assets),
                'portableBinaryAssetBytes': sum(item['bytes'] for item in portable_binary_assets),
                'frontendAssetCount': sum(name.startswith('web/') for name in files_manifest),
                'licensePackageCount': package_meta['licenseManifest']['packageCount'],
                'packagesMissingLicenseFiles': len(package_meta['licenseManifest']['packagesMissingLicenseFiles']),
            },
            'packageManager': {'node': node_version, 'pnpm': pnpm_version},
            'source': manifest['source'],
            'negativeAssertions': {
                'archiveValidatedAgainstManifest': True,
                'nativePolicyAcceptedEmptyImageSet': True,
                'elfOrOtherNativeBinariesIncluded': False,
                'sourceMapsIncluded': False,
                'previewAssetsIncluded': False,
                'testFixtureOrVitestPathsIncluded': False,
                'p3a003ForbiddenTestOrBuildPackageIdentitiesPresent': [],
                'credentialsOrLocalConfigIncluded': False,
                'checkoutSpecificWorkspacePathLeak': False,
                'symlinksContainedInImage': True,
                'deterministicSecondBuildPending': True,
            },
            'manifest': manifest,
        }
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return report


def compare_build_reports(first_path: Path, second_path: Path, output_path: Path) -> dict:
    """Require two isolated image builds to have identical inputs, manifests and archive bytes."""
    first = json.loads(first_path.read_text(encoding='utf-8'))
    second = json.loads(second_path.read_text(encoding='utf-8'))
    if first.get('task') != 'P3A-006' or second.get('task') != 'P3A-006':
        raise ValueError('Reproducibility comparison requires two P3A-006 build reports')
    checks = {
        'sourceInputsIdentical': first.get('source', {}).get('inputSha256') == second.get('source', {}).get('inputSha256'),
        'sourceRevisionIdentical': first.get('source', {}).get('revision') == second.get('source', {}).get('revision'),
        'manifestIdentical': first.get('manifest') == second.get('manifest'),
        'filePathHashesIdentical': first.get('manifest', {}).get('files') == second.get('manifest', {}).get('files'),
        'symlinkManifestIdentical': first.get('manifest', {}).get('links') == second.get('manifest', {}).get('links'),
        'packageLicenseManifestIdentical': first.get('manifest', {}).get('licenseManifest') == second.get('manifest', {}).get('licenseManifest'),
        'archiveSha256Identical': first.get('artifact', {}).get('sha256') == second.get('artifact', {}).get('sha256'),
        'archiveSizeIdentical': first.get('artifact', {}).get('bytes') == second.get('artifact', {}).get('bytes'),
    }
    if not all(checks.values()):
        raise ValueError('Independent P3A-006 builds differ: ' + ', '.join(name for name, passed in checks.items() if not passed))
    result = dict(
        schemaVersion=1,
        status='reproducibility-verified-host-only',
        independentTemporaryDeploys=True,
        checks=checks,
        builds=[
            {key: first['artifact'][key] for key in ('path', 'sha256', 'bytes', 'manifestSha256')},
            {key: second['artifact'][key] for key in ('path', 'sha256', 'bytes', 'manifestSha256')},
        ],
    )
    second['status'] = 'reproducible-candidate-generated-host-only'
    second['reproducibilityCheck'] = result
    second['negativeAssertions']['deterministicSecondBuildPending'] = False
    second['negativeAssertions']['deterministicSecondBuildVerified'] = True
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(second, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, nargs='?', help='new ZIP artifact path; existing files are never overwritten')
    parser.add_argument('--report', type=Path, default=OUTPUT_REPORT, help='structured evidence JSON path')
    parser.add_argument('--skip-builds', action='store_true', help='reuse already-built lib/frontend inputs (qualification only)')
    parser.add_argument('--compare-reports', nargs=2, type=Path, metavar=('FIRST', 'SECOND'), help='compare two completed build reports and emit combined reproducibility evidence')
    args = parser.parse_args()
    if args.compare_reports:
        if args.output:
            parser.error('omit the positional output when using --compare-reports')
        result = compare_build_reports(args.compare_reports[0], args.compare_reports[1], args.report)
        print(json.dumps(result, sort_keys=True))
        return
    if not args.output:
        parser.error('an output ZIP path is required unless --compare-reports is used')
    report = build(args.output, args.report, run_builds=not args.skip_builds)
    print(json.dumps(report['artifact'], sort_keys=True))


if __name__ == '__main__':
    main()
