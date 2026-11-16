#!/usr/bin/env python3
"""Inventory installed native payload candidates for the original Web Profile.

This is a host-side inventory, not an Android build or a file-level necessity
proof. Non-Android platform binaries are explicitly rejected as APK inputs.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'apps/android/evidence'
P3A003 = EVIDENCE / 'original-web-p3a003-runtime-test-separation.json'
P3A006_IMAGE_REPORT = EVIDENCE / 'original-web-p3a006-image-build.json'
HOST_SUMMARIES = [
    EVIDENCE / 'original-web-profile-p3a001-host-observations.json',
    EVIDENCE / 'original-web-bounded-p3a001-host-observations.json',
]
ANDROID_BUILD_EVIDENCE = sorted(EVIDENCE.glob('*build.json'))
OUT_TSV = EVIDENCE / 'original-web-p3a004-native-candidates.tsv'
OUT_JSON = EVIDENCE / 'original-web-p3a004-native-artifact-audit.json'
OUT_APK_MATRIX_TSV = EVIDENCE / 'original-web-p3a004-android-apk-native-matrix.tsv'
NATIVE_SUFFIXES = ('.node', '.so', '.dylib', '.dll', '.a')
VERSION_RE = re.compile(r'\b(?:GLIBCXX|GLIBC|CXXABI|GCC|VERS)_[A-Za-z0-9_.+-]+\b')

ARTIFACT_ROLES = {
    'libc++_shared.so': 'NDK shared C++ runtime in historical APKs; include in a Web Runtime Image only if selected Android libraries require it.',
    'libharness_atomic.so': 'Atomic-publication proof addon; not established as a Web Profile dependency.',
    'libharness_node_pty.so': 'Terminal-specific node-pty addon; not established as a Web Profile dependency.',
    'libharness_probe.so': 'Android JNI bridge loaded by RuntimeService; it loads libnode.so and calls Node::Start. This is outside the interpreted Web Runtime Image and is part of the Android runtime bridge.',
    'libharness_process_probe.so': 'Fixed process-capability proof executable staged through the main jniLibs source set; production-release scoping requires explicit review.',
    'libharness_pty_fixture.so': 'PTY proof fixture executable; exclude from the production Web Runtime Image.',
    'libharness_require_builtin.so': 'Android require-builtin carrier candidate; packaged hash is not linked to the recorded carrier-build hash.',
    'libharness_system.so': 'System/flock addon from a separate platform-capability proof; Web Profile necessity is unproven.',
    'libnode.so': 'Embedded Node shared-runtime candidate; exact Web Runtime Image inclusion remains unproven.',
    'libnode_executable.so': 'Node executable-carrier proof artifact; exact Web Runtime Image inclusion remains unproven.',
}

LICENSE_EVIDENCE = {
    'libc++_shared.so': 'NDK notice asset is listed by the initial APK manifest; the notice-to-binary mapping is not per-artifact.',
    'libharness_atomic.so': 'Source package is BSD-3-Clause (native/system/LICENSE); per-artifact APK notice mapping is unverified.',
    'libharness_node_pty.so': 'node-pty is MIT; APK6 build record hashes the package LICENSE file, but packaged notice mapping is unverified.',
    'libharness_probe.so': 'Repository project license is MIT; test/probe artifact, not a production image input.',
    'libharness_process_probe.so': 'Repository project license is MIT; test/probe artifact, not a production image input.',
    'libharness_pty_fixture.so': 'Repository project license is MIT; test fixture, not a production image input.',
    'libharness_require_builtin.so': 'Upstream carrier and node-addon-api declare MIT; the Android build recipe copies both notices, but exact APK notice inclusion and binary hash linkage are unverified.',
    'libharness_system.so': 'Source package is BSD-3-Clause (native/system/LICENSE); initial APK lists a system-addon license asset, but per-artifact mapping is unverified.',
    'libnode.so': 'Node license and third-party notice assets are listed by the initial APK manifest; exact per-binary notice mapping is unverified.',
    'libnode_executable.so': 'Node license and third-party notice assets are listed by the initial APK manifest; exact per-binary notice mapping is unverified.',
}

BUILD_HASH_FIELDS = {
    'libharness_atomic.so': ('atomicNativeBuild.nativeSha256',),
    'libharness_node_pty.so': ('nodePtyBuild.binarySha256',),
    'libharness_pty_fixture.so': ('nodePtyBuild.fixtureSha256',),
    'libharness_require_builtin.so': ('requireBuiltin.sha256',),
}

ARTIFACT_BUILD_CONTEXT = {
    'libc++_shared.so': {
        'recipes': [],
        'toolchainTarget': 'NDK 28.2.13676358 runtime context; no artifact-specific compiler invocation/hash record.',
        'inputs': 'APK records show the packaged runtime hash and DT_NEEDED only.',
    },
    'libharness_atomic.so': {
        'recipes': ['apps/android/runtime/build-atomic-addon.sh'],
        'toolchainTarget': 'NDK 28.2.13676358; aarch64-linux-android29-clang; API 29; N-API 8.',
        'inputs': 'native/system/packages/entry/src/atomic_publish.c; recorded nativeSha256 differs from packaged APK hash.',
    },
    'libharness_node_pty.so': {
        'recipes': ['apps/android/runtime/build-node-pty.py'],
        'toolchainTarget': 'NDK 28.2.13676358; aarch64-linux-android29-clang++; API 29; arm64-v8a; N-API 8.',
        'inputs': 'node-pty 1.2.0-beta.15; repository patch hash and source hash recorded; build binary hash matches APK6 packaged hash; exact Clang version not recorded.',
    },
    'libharness_probe.so': {
        'recipes': [],
        'toolchainTarget': 'APK-level arm64-v8a/minSdk 29 context only; per-artifact compiler/toolchain record not located.',
        'inputs': 'Probe/test artifact; exclude from production image.',
    },
    'libharness_process_probe.so': {
        'recipes': [],
        'toolchainTarget': 'APK-level arm64-v8a/minSdk 29 context; readelf snapshots show AArch64 and /system/bin/linker64, but are not hash-bound.',
        'inputs': 'Process-probe test artifact; exact source/build hash record not located.',
    },
    'libharness_pty_fixture.so': {
        'recipes': ['apps/android/runtime/build-node-pty.py'],
        'toolchainTarget': 'NDK 28.2.13676358; aarch64-linux-android29-clang++; API 29; PIE fixture; 16 KiB max-page-size linker flag.',
        'inputs': 'Fixture source hash and output hash match APK6 package record; fixture is test-only; exact Clang version not recorded.',
    },
    'libharness_require_builtin.so': {
        'recipes': ['apps/android/runtime/build_require_builtin.py'],
        'toolchainTarget': 'NDK 28.2.13676358; aarch64-linux-android29-clang++; API 29; N-API 9.',
        'inputs': 'Pinned require-builtin source and node-addon-api integrity; recorded output hash differs from packaged APK hash.',
    },
    'libharness_system.so': {
        'recipes': ['apps/android/runtime/build-system-addon.sh'],
        'toolchainTarget': 'NDK 28.2.13676358; aarch64-linux-android29-clang; API 29; N-API 8.',
        'inputs': 'native/system/packages/entry/src/flock.c; exact recipe-output hash linkage is not recorded.',
    },
    'libnode.so': {
        'recipes': ['apps/android/runtime/build-node.sh'],
        'toolchainTarget': 'NDK 28.2.13676358; aarch64-linux-android29-clang/++; arm64 Android target/API 29; exact Clang version not recorded.',
        'inputs': 'Node v24.22.1 source archive SHA is pinned; APK packaged output hash is not linked to a build-output SHA.',
    },
    'libnode_executable.so': {
        'recipes': ['apps/android/runtime/build-node-executable.sh'],
        'toolchainTarget': 'NDK 28.2.13676358; aarch64-linux-android29-clang++; API 29; 16 KiB max-page-size linker flag.',
        'inputs': 'Pinned Node src/node_main.cc and linked libnode; APK output hash is not linked to a build-output SHA.',
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run_tool(command: list[str]) -> str:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    return result.stdout.strip()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def package_identity(name: str | None, version: str | None) -> str | None:
    if not name or not version:
        return None
    return f'{name}@{version}'


def package_membership(p3a003: dict) -> dict[str, list[str]]:
    members: dict[str, list[str]] = {}
    for tree_name, tree in p3a003['productionPackageTrees'].items():
        for identity in tree['packageIdentities']:
            members.setdefault(identity, []).append(tree_name)
    return {identity: sorted(set(roles)) for identity, roles in members.items()}


def is_native_filename(path: Path) -> bool:
    lower = path.name.lower()
    return lower.endswith(NATIVE_SUFFIXES) or '.so.' in lower


def _package_files(root: Path):
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if name != 'node_modules']
        base = Path(current)
        for filename in filenames:
            path = base / filename
            if is_native_filename(path) and path.is_file():
                yield path


def find_candidates(membership: dict[str, list[str]]) -> dict[str, dict]:
    candidates: dict[str, dict] = {}
    pnpm_store = ROOT / 'node_modules/.pnpm'
    for manifest in pnpm_store.glob('*/node_modules/**/package.json'):
        try:
            data = read_json(manifest)
        except (OSError, json.JSONDecodeError):
            continue
        identity = package_identity(data.get('name'), data.get('version'))
        if identity is None:
            continue
        root = manifest.parent
        roles = membership.get(identity, [])
        for path in _package_files(root):
            relative = path.relative_to(ROOT).as_posix()
            candidates[relative] = {
                'path': path,
                'manifest': manifest,
                'package': data,
                'identity': identity,
                'membership': roles,
            }

    # The platform package is a workspace artifact, not an installed pnpm store entry.
    system_root = ROOT / 'native/system'
    if system_root.exists():
        for current, directories, filenames in os.walk(system_root, followlinks=False):
            directories[:] = [name for name in directories if name != 'node_modules']
            for filename in filenames:
                path = Path(current) / filename
                if not is_native_filename(path) or not path.is_file():
                    continue
                relative = path.relative_to(ROOT).as_posix()
                manifest = next((parent / 'package.json' for parent in path.parents
                                 if (parent / 'package.json').is_file()), None)
                data = read_json(manifest) if manifest else {}
                identity = package_identity(data.get('name'), data.get('version'))
                candidates[relative] = {
                    'path': path,
                    'manifest': manifest,
                    'package': data,
                    'identity': identity,
                    'membership': membership.get(identity, []),
                }
    return dict(sorted(candidates.items()))


def _first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else None


def inspect_elf(path: Path) -> dict | None:
    with path.open('rb') as binary:
        magic = binary.read(4)
    if magic != b'\x7fELF':
        return None
    readelf = shutil.which('readelf')
    if not readelf:
        raise RuntimeError('readelf is required to inspect ELF candidates')
    header = run_tool([readelf, '-h', '-W', str(path)])
    programs = run_tool([readelf, '-l', '-W', str(path)])
    dynamic = run_tool([readelf, '-d', '-W', str(path)])
    versions = run_tool([readelf, '-V', '-W', str(path)])
    notes = run_tool([readelf, '-n', '-W', str(path)])
    symbols = run_tool([readelf, '--dyn-syms', '-W', str(path)])

    needed = sorted(set(re.findall(r'\(NEEDED\).*?\[([^]]+)\]', dynamic)))
    load_alignments = []
    for line in programs.splitlines():
        fields = line.split()
        if fields and fields[0] == 'LOAD' and fields[-1].startswith('0x'):
            try:
                load_alignments.append(int(fields[-1], 16))
            except ValueError:
                pass
    undefined_symbols = []
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[0].endswith(':') and fields[6] == 'UND':
            undefined_symbols.append(' '.join(fields[7:]))
    undefined_symbols = sorted(set(undefined_symbols))
    android_min_api = None
    if '.note.android.ident' in notes:
        android_note = notes[notes.index('.note.android.ident'):]
        data = re.search(r'description data:\s*([0-9a-fA-F ]+)', android_note)
        if data:
            octets = bytes.fromhex(data.group(1))
            if len(octets) >= 4:
                android_min_api = int.from_bytes(octets[:4], 'little')
    comments = run_tool([readelf, '-p', '.comment', str(path)])
    compiler_comments = sorted(set(re.findall(r'\[\s*\d+\]\s*(.+)', comments)))
    return {
        'class': _first(r'^\s*Class:\s*(.+)$', header),
        'dataEncoding': _first(r'^\s*Data:\s*(.+)$', header),
        'osAbi': _first(r'^\s*OS/ABI:\s*(.+)$', header),
        'type': _first(r'^\s*Type:\s*(.+)$', header),
        'machine': _first(r'^\s*Machine:\s*(.+)$', header),
        'interpreter': _first(r'\[Requesting program interpreter:\s*([^]]+)\]', programs),
        'neededLibraries': needed,
        'versionRequirements': sorted(set(VERSION_RE.findall(versions))),
        'undefinedDynamicSymbols': undefined_symbols,
        'undefinedDynamicSymbolCount': len(undefined_symbols),
        'undefinedDynamicSymbolsSha256': hashlib.sha256(
            '\n'.join(undefined_symbols).encode('utf-8')).hexdigest(),
        'loadSegmentAlignmentsBytes': load_alignments,
        'minimumAndroidApiNote': android_min_api,
        'androidIdentNotePresent': '.note.android.ident' in notes,
        'compilerComments': compiler_comments,
    }


def platform_tags(relative: str) -> list[str]:
    tags = []
    for token in re.split(r'[/.-]', relative.lower()):
        normalized = token.replace('_', '-')
        if any(part in normalized for part in (
            'linux', 'darwin', 'macos', 'win32', 'windows', 'android',
            'glibc', 'musl', 'arm64', 'aarch64', 'x64', 'ia32', 'armv7',
        )):
            tags.append(normalized)
    return sorted(set(tags))


def android_decision(file_description: str, elf: dict | None, tags: list[str]) -> str:
    desc = file_description.lower()
    if 'webassembly' in desc or desc.startswith('wasm'):
        return 'not_native_elf_wasm; keep outside native ELF policy'
    if elf is None:
        return 'deny_non_android_platform_or_archive; no ELF metadata'
    if 'libc.so.6' in elf['neededLibraries'] or any(v.startswith('GLIBC_') for v in elf['versionRequirements']):
        return 'deny_linux_gnu_glibc'
    if any(tag.startswith(('linux', 'darwin', 'macos', 'win32', 'windows', 'glibc', 'musl')) for tag in tags):
        return 'deny_non_android_platform_prebuilt'
    if elf['machine'] != 'AArch64':
        return 'deny_wrong_or_unknown_android_abi'
    if elf['minimumAndroidApiNote'] is None:
        return 'not_approved_android_minimum_api_note_missing'
    return 'candidate_only_requires_dependency_closure_and_device_validation'


def license_files_for(root: Path | None) -> list[str]:
    if root is None or not root.exists():
        return []
    found = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if name != 'node_modules']
        base = Path(current)
        for filename in filenames:
            low = filename.lower()
            if any(word in low for word in ('license', 'licence', 'notice', 'copying')):
                found.append((base / filename).relative_to(root).as_posix())
    return sorted(set(found))


def collect_native_records(candidates: dict[str, dict]) -> list[dict]:
    records = []
    for relative, entry in candidates.items():
        path = entry['path']
        file_description = run_tool(['file', '-b', str(path)])
        elf = inspect_elf(path)
        package = entry['package']
        root = entry['manifest'].parent if entry['manifest'] else None
        tags = platform_tags(relative)
        records.append({
            'path': relative,
            'package': entry['identity'],
            'productionTrees': entry['membership'],
            'installedOnly': not bool(entry['membership']),
            'platformTags': tags,
            'fileDescription': file_description,
            'elf': elf,
            'sha256': sha256(path),
            'packageLicense': package.get('license'),
            'packageOS': package.get('os'),
            'packageCPU': package.get('cpu'),
            'packageLibc': package.get('libc'),
            'licenseFiles': license_files_for(root),
            'androidPackagingDecision': android_decision(file_description, elf, tags),
        })
    return records


def read_observed_native_loads() -> list[dict]:
    observed: dict[str, set[str]] = {}
    for summary_path in HOST_SUMMARIES:
        if not summary_path.exists():
            continue
        report = read_json(summary_path)
        for path in report.get('observedNativeAddons', []):
            observed.setdefault(path, set()).add(summary_path.relative_to(ROOT).as_posix())
    result = []
    for path, sources in sorted(observed.items()):
        absolute = ROOT / path
        result.append({
            'path': path,
            'sourceEvidence': sorted(sources),
            'existsInCurrentCheckout': absolute.is_file(),
            'sha256': sha256(absolute) if absolute.is_file() else None,
        })
    return result


def _dotted_value(data: dict, dotted: str):
    value = data
    for part in dotted.split('.'):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def apk_context(data: dict) -> dict:
    context = {'minimumSdk': None, 'targetSdk': None, 'nativeCode': []}
    for check in data.get('checks', []):
        command = ' '.join(str(x) for x in check.get('command', []))
        if 'badging' not in command.lower():
            continue
        output = check.get('output', '')
        for key, pattern in (
            ('minimumSdk', r"sdkVersion:'(\d+)'"),
            ('targetSdk', r"targetSdkVersion:'(\d+)'"),
        ):
            match = re.search(pattern, output)
            if match:
                context[key] = int(match.group(1))
        match = re.search(r"native-code:\s*'([^']*)'", output)
        if match:
            context['nativeCode'] = sorted(match.group(1).split())
        break
    return context


def readelf_observations(data: dict) -> dict[str, list[dict]]:
    observations: dict[str, list[dict]] = {}
    for index, check in enumerate(data.get('checks', [])):
        command = check.get('command', [])
        if not any('readelf' in str(part).lower() for part in command):
            continue
        binary_name = Path(str(command[-1])).name if command else 'unknown'
        output = check.get('output', '')
        alignments = []
        for line in output.splitlines():
            fields = line.split()
            if fields and fields[0] == 'LOAD' and fields[-1].startswith('0x'):
                try:
                    alignments.append(int(fields[-1], 16))
                except ValueError:
                    pass
        item = {
            'evidenceCheckIndex': index,
            'tool': Path(str(command[0])).name if command else None,
            'exitCode': check.get('exitCode'),
            'machine': _first(r'^\s*Machine:\s*(.+)$', output),
            'type': _first(r'^\s*Type:\s*(.+)$', output),
            'interpreter': _first(r'\[Requesting program interpreter:\s*([^]]+)\]', output),
            'neededLibraries': sorted(set(re.findall(r'\(NEEDED\).*?\[([^]]+)\]', output))),
            'loadSegmentAlignmentsBytes': alignments,
            'minimumAndroidApiNote': None,
            'symbolRequirements': 'not present in retained readelf check output',
            'exactPackagedHashBoundToCheck': False,
        }
        observations.setdefault(binary_name, []).append(item)
    return observations


def build_hash_status(name: str, packaged_sha: str, data: dict) -> dict:
    fields = BUILD_HASH_FIELDS.get(name, ())
    declarations = []
    for field in fields:
        digest = _dotted_value(data, field)
        if isinstance(digest, str):
            declarations.append({'field': field, 'sha256': digest, 'matchesPackagedHash': digest == packaged_sha})
    if not declarations:
        status = 'no_artifact_output_hash_in_build_record'
    elif any(item['matchesPackagedHash'] for item in declarations):
        status = 'exact_build_output_hash_match'
    else:
        status = 'build_record_hash_differs_from_packaged_hash'
    return {'status': status, 'declaredBuildHashes': declarations}


def historical_android_builds() -> tuple[list[dict], list[dict]]:
    snapshots = []
    per_library: dict[str, dict] = {}
    for evidence_path in ANDROID_BUILD_EVIDENCE:
        if not evidence_path.is_file():
            continue
        data = read_json(evidence_path)
        packaged = data.get('packagedLibraries', {})
        if not isinstance(packaged, dict) or not packaged:
            continue
        context = apk_context(data)
        elf_checks = readelf_observations(data)
        snapshots.append({
            'evidence': evidence_path.relative_to(ROOT).as_posix(),
            'sha256': sha256(evidence_path),
            'scope': data.get('scope') or data.get('environment'),
            'apkVersionCode': data.get('apkVersionCode'),
            'apkVersionName': data.get('apkVersionName'),
            'apkSha256': data.get('apkSha256'),
            'apkContext': context,
            'profileImageCompleteDependencyDistribution': (data.get('profileImage') or {}).get('completeDependencyDistribution'),
            'requiredAssets': data.get('requiredAssets', []),
            'sharedLicenseAssets': data.get('sharedLicenseAssets', []),
            'packagedLibraries': packaged,
            'readelfChecksByFilename': elf_checks,
            'buildRecords': {
                key: data.get(key)
                for key in ('nodeBuild', 'nodePtyBuild', 'atomicNativeBuild', 'requireBuiltin', 'processProbe')
                if key in data
            },
            'limitation': 'historical Android build/package snapshot; not proof that a Web Runtime Image contains these bytes or has a complete native closure',
        })
        for name, details in packaged.items():
            digest = details.get('sha256')
            if not isinstance(digest, str):
                continue
            entry = per_library.setdefault(name, {'artifact': name, 'snapshots': []})
            entry['snapshots'].append({
                'evidence': evidence_path.relative_to(ROOT).as_posix(),
                'sha256': digest,
                'bytes': details.get('bytes'),
                'DT_NEEDED': details.get('dependencies', []),
                'loadAlignmentAtLeast16384': details.get('loadAlignmentAtLeast16384'),
                'apkContext': context,
                'buildHashStatus': build_hash_status(name, digest, data),
                'readelfObservations': elf_checks.get(name, []),
            })

    matrix = []
    for name, entry in sorted(per_library.items()):
        snapshots_for_lib = entry['snapshots']
        hashes = sorted({item['sha256'] for item in snapshots_for_lib})
        build_statuses = sorted({item['buildHashStatus']['status'] for item in snapshots_for_lib})
        matrix.append({
            'artifact': name,
            'purposeAndWebImageDisposition': ARTIFACT_ROLES.get(name, 'Role and Web Runtime Image necessity not assessed.'),
            'buildContext': ARTIFACT_BUILD_CONTEXT.get(name, {
                'recipes': [],
                'toolchainTarget': 'Not recorded.',
                'inputs': 'Not recorded.',
            }),
            'sha256Variants': hashes,
            'hashStableAcrossRecordedSnapshots': len(hashes) == 1,
            'evidenceSnapshots': snapshots_for_lib,
            'apkLevelAbi': sorted({abi for item in snapshots_for_lib for abi in item['apkContext']['nativeCode']}),
            'apkMinimumSdkValues': sorted({item['apkContext']['minimumSdk'] for item in snapshots_for_lib if item['apkContext']['minimumSdk'] is not None}),
            'apkTargetSdkValues': sorted({item['apkContext']['targetSdk'] for item in snapshots_for_lib if item['apkContext']['targetSdk'] is not None}),
            'elfMinimumAndroidApiNoteStatus': 'not recorded in retained exact-artifact readelf output; APK minSdk is package-level context only.',
            'symbolAndVersionRequirementStatus': 'full dynamic symbol/version requirements are not recorded for this exact packaged artifact.',
            'DT_NEEDEDVariants': sorted({tuple(item['DT_NEEDED']) for item in snapshots_for_lib}),
            'reported16kAlignmentValues': sorted({item['loadAlignmentAtLeast16384'] for item in snapshots_for_lib if item['loadAlignmentAtLeast16384'] is not None}),
            'buildHashLinkStatuses': build_statuses,
            'licenseEvidence': LICENSE_EVIDENCE.get(name, 'License evidence not located.'),
            'licenseMappingStatus': 'Source license/asset claims are contextual; exact packaged per-artifact notice binding is not established.',
        })
    return snapshots, matrix


def current_android_packaging_inputs(matrix: list[dict]) -> tuple[dict, list[dict]]:
    """Parse the Android Gradle/CMake declarations without treating them as APK evidence."""
    gradle_path = ROOT / 'apps/android/app/build.gradle.kts'
    runtime_prepare_path = ROOT / 'apps/android/scripts/prepare_runtime_assets.py'
    pty_prepare_path = ROOT / 'apps/android/scripts/prepare_node_pty_assets.py'
    cmake_path = ROOT / 'apps/android/native/CMakeLists.txt'
    gradle = gradle_path.read_text(encoding='utf-8')
    runtime_prepare = runtime_prepare_path.read_text(encoding='utf-8')
    pty_prepare = pty_prepare_path.read_text(encoding='utf-8')
    cmake = cmake_path.read_text(encoding='utf-8')
    runtime_allowlist_match = re.search(r'if name not in (\{.*?\}):', runtime_prepare, re.S)
    pty_names_match = re.search(r'for name in (\[\'libharness_[^\]]*\])\s*:', pty_prepare, re.S)
    process_output_match = re.search(r'generated/processNative/arm64-v8a/([^"\)]+\.so)', gradle)
    if not runtime_allowlist_match or not pty_names_match or not process_output_match:
        raise ValueError('Android runtime/PTY/process native packaging declarations could not be parsed')
    runtime_names = sorted(ast.literal_eval(runtime_allowlist_match.group(1)))
    pty_names = ast.literal_eval(pty_names_match.group(1))
    cmake_targets = re.findall(r'add_library\(\s*([A-Za-z0-9_]+)\s+SHARED\b', cmake)
    if len(runtime_names) != 6 or len(pty_names) != 2 or cmake_targets != ['harness_probe']:
        raise ValueError('Android native packaging graph changed; review P3A-004 candidate grouping')
    abi = re.search(r'abiFilters\s*\+=\s*"([^"]+)"', gradle)
    minimum_api = re.search(r'minSdk\s*=\s*(\d+)', gradle)
    if not abi or not minimum_api or abi.group(1) != 'arm64-v8a' or minimum_api.group(1) != '29':
        raise ValueError('Android native packaging ABI/API target changed; review P3A-004 evidence')

    historical = {item['artifact']: item for item in matrix}
    entries = []

    def add(name: str, group: str, recipe: str, expected_path: str, source_path: str | None, role: str) -> None:
        expected_file = ROOT / expected_path if expected_path else None
        source_file = ROOT / source_path if source_path else None
        raw_matches = [p for p in (ROOT / 'apps/android').rglob(name) if p.is_file()]
        matrix_row = historical.get(name, {})
        entries.append({
            'artifact': name,
            'packagingGroup': group,
            'role': role,
            'declaredBy': recipe,
            'expectedPackagePath': f'lib/{abi.group(1)}/{name}',
            'expectedBuildOrStagingPath': expected_path or 'Gradle externalNativeBuild output (variant-specific)',
            'sourcePath': source_path,
            'expectedBuildOrStagingPathExists': bool(expected_file and expected_file.is_file()),
            'sourcePathExists': bool(source_file and source_file.is_file()),
            'rawArtifactPathsFound': [p.relative_to(ROOT).as_posix() for p in raw_matches],
            'rawArtifactSha256': [sha256(p) for p in raw_matches],
            'historicalSha256Variants': matrix_row.get('sha256Variants', []),
            'historicalBuildHashLinkStatuses': matrix_row.get('buildHashLinkStatuses', []),
            'historicalApkAbis': matrix_row.get('apkLevelAbi', []),
        })

    for name in runtime_names:
        add(
            name, 'runtime-jni-libraries', 'apps/android/scripts/prepare_runtime_assets.py',
            f'apps/android/app/src/main/jniLibs/arm64-v8a/{name}',
            None, ARTIFACT_ROLES.get(name, 'Runtime library named by the current preparation allowlist.'),
        )
    for name in pty_names:
        role = ARTIFACT_ROLES.get(name, 'Terminal profile native input.')
        add(
            name, 'terminal-node-pty-jni-libraries', 'apps/android/scripts/prepare_node_pty_assets.py',
            f'apps/android/app/build/generated/nodePtyNative/arm64-v8a/{name}',
            f'apps/android/runtime/out/node-pty/{name}', role,
        )
    process_name = process_output_match.group(1)
    add(
        process_name, 'process-capability-proof', 'apps/android/app/build.gradle.kts: processProof',
        f'apps/android/app/build/generated/processNative/arm64-v8a/{process_name}',
        'apps/android/execution/process-proof/process_probe.cpp', ARTIFACT_ROLES[process_name],
    )
    for target in cmake_targets:
        name = f'lib{target}.so'
        runtime_service = ROOT / 'apps/android/app/src/main/java/io/github/mohammedteir/deepseekharness/RuntimeService.kt'
        if f'System.loadLibrary("{target}")' not in runtime_service.read_text(encoding='utf-8'):
            raise ValueError('CMake native target is not referenced by RuntimeService as expected')
        add(
            name, 'android-jni-runtime-bridge', 'apps/android/app/build.gradle.kts: externalNativeBuild + apps/android/native/CMakeLists.txt',
            '', 'apps/android/native/probe.cpp', ARTIFACT_ROLES[name],
        )

    source_paths = [
        'apps/android/app/build.gradle.kts', 'apps/android/native/CMakeLists.txt',
        'apps/android/native/probe.cpp', 'apps/android/scripts/prepare_runtime_assets.py',
        'apps/android/scripts/prepare_node_pty_assets.py', 'apps/android/execution/process-proof/process_probe.cpp',
        'apps/android/app/src/main/java/io/github/mohammedteir/deepseekharness/RuntimeService.kt',
        'apps/android/app/src/main/java/io/github/mohammedteir/deepseekharness/ProcessCapabilityService.kt',
        'apps/android/app/src/main/java/io/github/mohammedteir/deepseekharness/NodePtyProbeService.kt',
    ]
    source_inputs = [
        {'path': path, 'sha256': sha256(ROOT / path)}
        for path in source_paths if (ROOT / path).is_file()
    ]
    apk_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'apps/android').rglob('*')
                 if p.is_file() and p.suffix.lower() in {'.apk', '.aab'}]
    raw_native_files = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'apps/android').rglob('*')
                        if p.is_file() and (p.suffix.lower() in NATIVE_SUFFIXES or '.so.' in p.name.lower())]
    summary = {
        'status': 'declared-build-graph-only; no raw Android package/native output available in the worktree',
        'target': {'abi': abi.group(1), 'minimumApi': int(minimum_api.group(1))},
        'declaredNativeInputCount': len(entries),
        'rawApkOrAabAvailable': bool(apk_paths),
        'rawApkOrAabPaths': apk_paths,
        'rawNativeArtifactFileCount': len(raw_native_files),
        'rawNativeArtifactPaths': raw_native_files,
        'groups': {
            group: sum(item['packagingGroup'] == group for item in entries)
            for group in sorted({item['packagingGroup'] for item in entries})
        },
        'items': entries,
        'interpretation': 'Gradle/CMake declarations identify expected app-package inputs, not a built APK inventory. Source recipes and historical package snapshots do not substitute for the absent raw APK and exact packaged ELF bytes.',
    }
    return summary, source_inputs


def android_matrix_tsv(matrix: list[dict]) -> str:
    from io import StringIO
    out = StringIO()
    writer = csv.writer(out, delimiter='\t', lineterminator='\n')
    out.write('# Historical Android package matrix only; does not qualify the original Web Runtime Image.\n')
    writer.writerow([
        'artifact', 'SHA-256 variants', 'Build/package snapshots', 'APK ABI context', 'APK min SDK context',
        'Build recipe/toolchain context', 'DT_NEEDED variants', 'ELF interpreter/readelf checks',
        'ELF symbols/min API note coverage', '16 KiB alignment evidence', 'build hash-link status',
        'Web Runtime Image disposition', 'license evidence', 'license notice mapping status',
    ])
    for item in matrix:
        needed = sorted({', '.join(v) for v in item['DT_NEEDEDVariants']})
        align = sorted({
            str(snapshot['loadAlignmentAtLeast16384'])
            for snapshot in item['evidenceSnapshots']
            if snapshot['loadAlignmentAtLeast16384'] is not None
        })
        elf_checks = sorted({
            f"{snapshot['evidence']}:{check['machine'] or 'machine unknown'}:{check['type'] or 'ELF'}:{check['interpreter'] or 'no PT_INTERP recorded'}"
            for snapshot in item['evidenceSnapshots'] for check in snapshot['readelfObservations']
        })
        writer.writerow([
            item['artifact'], ';'.join(item['sha256Variants']), len(item['evidenceSnapshots']),
            ';'.join(item['apkLevelAbi']) or 'not recorded',
            ';'.join(str(v) for v in item['apkMinimumSdkValues']) or 'not recorded (package context)',
            ' '.join(item['buildContext']['recipes']) + ' — ' + item['buildContext']['toolchainTarget'],
            '; '.join(needed) or 'not recorded',
            ';'.join(elf_checks) or 'no retained artifact-specific readelf check',
            'symbol/version needs: not recorded; ELF API note: not recorded',
            ';'.join(align) or 'not recorded',
            ';'.join(item['buildHashLinkStatuses']), item['purposeAndWebImageDisposition'], item['licenseEvidence'],
            item['licenseMappingStatus'],
        ])
    return out.getvalue()


def tsv_text(records: list[dict], observed: list[dict]) -> str:
    observed_paths = {item['path'] for item in observed}
    columns = [
        'relpath', 'package@version', 'membership', 'platform tags', 'file(1) description',
        'ELF machine', 'ELF interpreter', 'DT_NEEDED', 'symbol versions',
        'undefined dynamic symbol count', 'minimum Android API note', 'PT_LOAD alignments bytes',
        'SHA256', 'package.json license field', 'license/NOTICE file evidence',
        'Android packaging decision', 'P3A-001 observed native load',
    ]
    from io import StringIO
    out = StringIO()
    writer = csv.writer(out, delimiter='\t', lineterminator='\n')
    out.write('# P3A-004 installed native payload candidates; P3A-006 host-image native exclusions are bound in the JSON report; APK/runtime ELF closure remains open.\n')
    writer.writerow(columns)
    for item in records:
        elf = item['elf'] or {}
        writer.writerow([
            item['path'], item['package'] or 'unknown', ';'.join(item['productionTrees']) or 'not in either production root',
            ';'.join(item['platformTags']) or '(no explicit tag)', item['fileDescription'],
            elf.get('machine') or 'not ELF', elf.get('interpreter') or 'N/A', ';'.join(elf.get('neededLibraries', [])) or 'N/A',
            ';'.join(elf.get('versionRequirements', [])) or 'N/A', elf.get('undefinedDynamicSymbolCount', 'N/A'),
            elf.get('minimumAndroidApiNote') if elf else 'N/A', ';'.join(str(n) for n in elf.get('loadSegmentAlignmentsBytes', [])) or 'N/A',
            item['sha256'], json.dumps(item['packageLicense'], sort_keys=True), ';'.join(item['licenseFiles']) or 'none found',
            item['androidPackagingDecision'], 'yes' if item['path'] in observed_paths else 'no',
        ])
    return out.getvalue()


def audit_p3a006_image(report: dict, report_sha256: str) -> dict:
    """Bind P3A-004 to the exact reproducible host image without claiming APK closure."""
    if report.get('task') != 'P3A-006' or report.get('status') != 'reproducible-candidate-generated-host-only':
        raise ValueError('P3A-006 image report is missing or is not the reproducible host candidate')
    artifact = report.get('artifact', {})
    manifest = report.get('manifest', {})
    comparison = report.get('reproducibilityCheck', {})
    builds = comparison.get('builds', [])
    checks = comparison.get('checks', {})
    required_checks = {
        'archiveSha256Identical', 'archiveSizeIdentical', 'filePathHashesIdentical',
        'manifestIdentical', 'packageLicenseManifestIdentical', 'sourceInputsIdentical',
        'sourceRevisionIdentical', 'symlinkManifestIdentical',
    }
    if comparison.get('status') != 'reproducibility-verified-host-only' or set(checks) != required_checks or not all(checks.values()):
        raise ValueError('P3A-006 report lacks a complete passing two-build reproducibility comparison')
    if len(builds) != 2:
        raise ValueError('P3A-006 reproducibility evidence must contain exactly two full builds')
    identity_fields = ('sha256', 'manifestSha256', 'bytes')
    if any(any(build.get(field) != builds[0].get(field) for field in identity_fields) for build in builds[1:]):
        raise ValueError('P3A-006 build records do not agree on archive identity')
    if any(artifact.get(field) != builds[0].get(field) for field in identity_fields):
        raise ValueError('P3A-006 selected artifact does not match the reproducibility records')
    native_included = manifest.get('nativeArtifacts')
    native_excluded = manifest.get('excludedNativeArtifacts')
    files = manifest.get('files')
    links = manifest.get('links')
    if not isinstance(native_included, list) or not isinstance(native_excluded, list):
        raise ValueError('P3A-006 manifest is missing native artifact inventories')
    if not isinstance(files, dict) or not isinstance(links, dict):
        raise ValueError('P3A-006 manifest is missing file or symlink inventories')
    for item in native_included + native_excluded:
        if not isinstance(item.get('path'), str) or not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', ''))):
            raise ValueError('P3A-006 native artifact record lacks a path or SHA-256')
    if any(item.get('decision') != 'excluded-default-deny-no-approved-web-image-native-artifacts' for item in native_excluded):
        raise ValueError('P3A-006 native exclusion inventory contains a non-default-deny decision')
    policy_digest = manifest.get('nativePolicySha256')
    current_policy = ROOT / 'apps/android/runtime/native-artifact-policy.json'
    if policy_digest != sha256(current_policy):
        raise ValueError('P3A-006 image was built against a different native-artifact policy digest')
    if int(artifact.get('includedFileCount', -1)) != len(files) or int(artifact.get('includedSymlinkCount', -1)) != len(links):
        raise ValueError('P3A-006 summary counts do not match its path manifests')
    if int(artifact.get('nativeArtifactCount', -1)) != len(native_included) or int(artifact.get('excludedNativeArtifactCount', -1)) != len(native_excluded):
        raise ValueError('P3A-006 summary counts do not match its native artifact manifests')
    native_suffixes = ('.node', '.so', '.dylib', '.dll', '.a', '.exe', '.pyd')
    native_paths = [path for path in files if path.lower().endswith(native_suffixes) or '.so.' in path.lower()]
    if native_paths:
        raise ValueError('P3A-006 image file inventory contains native-looking paths outside its native artifact list')
    license_manifest = manifest.get('licenseManifest', {})
    license_records = license_manifest.get('packageLicenseEvidence', [])
    if int(license_manifest.get('packageCount', -1)) != len(license_records):
        raise ValueError('P3A-006 package license count does not match the per-package records')
    if int(license_manifest.get('packagesWithDeclaredLicense', -1)) != len(license_records):
        raise ValueError('P3A-006 package license declarations are not fully mapped')
    formats: dict[str, int] = {}
    for item in native_excluded:
        kind = item.get('format') or 'unknown'
        formats[kind] = formats.get(kind, 0) + 1
    assertions = report.get('negativeAssertions', {})
    if assertions.get('elfOrOtherNativeBinariesIncluded') is not False or assertions.get('nativePolicyAcceptedEmptyImageSet') is not True:
        raise ValueError('P3A-006 native exclusion assertions are absent or failed')
    return {
        'reportPath': P3A006_IMAGE_REPORT.relative_to(ROOT).as_posix(),
        'reportSha256': report_sha256,
        'artifactSha256': artifact['sha256'],
        'artifactManifestSha256': artifact['manifestSha256'],
        'artifactBytes': artifact['bytes'],
        'reproducibilityStatus': comparison['status'],
        'reproducibilityChecks': checks,
        'sourceRevision': manifest.get('source', {}).get('revision'),
        'nativePolicySha256': policy_digest,
        'imageFileCount': len(files),
        'imageSymlinkCount': len(links),
        'packageManifestCount': manifest.get('packageManifestCount'),
        'includedNativeArtifactCount': len(native_included),
        'includedNativeArtifacts': native_included,
        'excludedNativeArtifactCount': len(native_excluded),
        'excludedNativeByFormat': dict(sorted(formats.items())),
        'excludedNativeArtifacts': native_excluded,
        'portableBinaryAssets': manifest.get('portableBinaryAssets', []),
        'negativeAssertions': assertions,
        'licenseManifestSummary': {
            'packageCount': license_manifest.get('packageCount'),
            'packagesWithDeclaredLicense': license_manifest.get('packagesWithDeclaredLicense'),
            'packagesWithLicenseFiles': license_manifest.get('packagesWithLicenseFiles'),
            'packagesMissingLicenseFiles': len(license_manifest.get('packagesMissingLicenseFiles', [])),
            'projectFiles': license_manifest.get('projectFiles', []),
        },
        'androidApkRuntimeNativeClosureAccepted': False,
        'decision': 'candidate-image-contains-no-native-artifacts; this does not prove the separate Android APK/runtime ELF closure',
    }


def build_outputs() -> tuple[str, str, str]:
    p3a003 = read_json(P3A003)
    p3a006 = read_json(P3A006_IMAGE_REPORT)
    p3a006_native_audit = audit_p3a006_image(p3a006, sha256(P3A006_IMAGE_REPORT))
    members = package_membership(p3a003)
    candidates = find_candidates(members)
    records = collect_native_records(candidates)
    observed = read_observed_native_loads()
    raw_tsv = tsv_text(records, observed)
    tsv_hash = hashlib.sha256(raw_tsv.encode('utf-8')).hexdigest()
    p3a001_paths = {item['path'] for item in observed}
    record_by_path = {item['path']: item for item in records}
    observed_review = []
    for path in sorted(p3a001_paths):
        source = record_by_path.get(path)
        observed_review.append({
            'path': path,
            'successfulHostLoadInBothCaptures': len(next((x['sourceEvidence'] for x in observed if x['path'] == path), [])) == 2,
            'artifactSha256': source['sha256'] if source else None,
            'elfMachine': source['elf']['machine'] if source and source['elf'] else None,
            'neededLibraries': source['elf']['neededLibraries'] if source and source['elf'] else [],
            'versionRequirements': source['elf']['versionRequirements'] if source and source['elf'] else [],
            'androidPackagingDecision': source['androidPackagingDecision'] if source else 'not_found_in_candidate_scan',
        })
    memberships = [set(x['productionTrees']) for x in records]
    cli_count = sum('cli' in roles for roles in memberships)
    web_count = sum('webProfileBundle' in roles for roles in memberships)
    both_count = sum({'cli', 'webProfileBundle'}.issubset(roles) for roles in memberships)
    android_builds, android_library_matrix = historical_android_builds()
    android_matrix = android_matrix_tsv(android_library_matrix)
    android_matrix_hash = hashlib.sha256(android_matrix.encode('utf-8')).hexdigest()
    android_packaging_graph, android_packaging_graph_inputs = current_android_packaging_inputs(android_library_matrix)
    android_build_inputs = [
        {'path': item['evidence'], 'sha256': item['sha256']}
        for item in android_builds
    ]
    recipe_paths = [
        'apps/android/runtime/build-node.sh',
        'apps/android/runtime/build-node-executable.sh',
        'apps/android/runtime/build-system-addon.sh',
        'apps/android/runtime/build-atomic-addon.sh',
        'apps/android/runtime/build_require_builtin.py',
        'apps/android/runtime/build-node-pty.py',
    ]
    license_paths = [
        'LICENSE',
        'apps/android/licenses/third-party/NOTICE.txt',
        'native/system/LICENSE',
        'native/system/packages/entry/package.json',
        'apps/android/runtime/require-builtin-source.json',
        'node_modules/.pnpm/node-addon-require-builtin@0.1.9/node_modules/node-addon-require-builtin/LICENSE',
        'node_modules/.pnpm/node-addon-api@7.1.1/node_modules/node-addon-api/LICENSE.md',
        *[p.relative_to(ROOT).as_posix() for p in sorted(ROOT.glob('node_modules/.pnpm/node-pty@*/node_modules/node-pty/LICENSE'))],
    ]
    recipe_inputs = [
        {'path': path, 'sha256': sha256(ROOT / path)}
        for path in recipe_paths if (ROOT / path).is_file()
    ]
    license_inputs = [
        {'path': path, 'sha256': sha256(ROOT / path)}
        for path in sorted(set(license_paths)) if (ROOT / path).is_file()
    ]
    report = {
        'schemaVersion': 1,
        'task': 'P3A-004',
        'status': 'in_progress_not_accepted',
        'target': {'abi': 'arm64-v8a', 'operatingSystem': 'Android', 'libc': 'Bionic', 'minimumApi': 29},
        'inputs': {
            'scanner': {
                'path': Path(__file__).resolve().relative_to(ROOT).as_posix(),
                'sha256': sha256(Path(__file__).resolve()),
            },
            'lockfile': {'path': 'pnpm-lock.yaml', 'sha256': sha256(ROOT / 'pnpm-lock.yaml')},
            'p3a003': {'path': P3A003.relative_to(ROOT).as_posix(), 'sha256': sha256(P3A003)},
            'p3a006ImageReport': {'path': P3A006_IMAGE_REPORT.relative_to(ROOT).as_posix(), 'sha256': sha256(P3A006_IMAGE_REPORT)},
            'hostObservations': [
                {'path': p.relative_to(ROOT).as_posix(), 'sha256': sha256(p)}
                for p in HOST_SUMMARIES if p.exists()
            ],
            'historicalAndroidBuildEvidence': android_build_inputs,
            'androidBuildRecipes': recipe_inputs,
            'androidPackagingGraphSources': android_packaging_graph_inputs,
            'androidLicenseSources': license_inputs,
            'productionPackageTrees': {name: tree['packageIdentitySetSha256'] for name, tree in p3a003['productionPackageTrees'].items()},
            'nativeStoreRoot': 'node_modules/.pnpm',
            'repositoryNativeRoot': 'native/system',
            'inspectionTools': {
                'file': run_tool(['file', '--version']).splitlines()[0],
                'readelf': run_tool(['readelf', '--version']).splitlines()[0],
            },
        },
        'inventory': {
            'candidateFileCount': len(records),
            'cliProductionTreeMembers': cli_count,
            'webProfileProductionTreeMembers': web_count,
            'membersOfBothTrees': both_count,
            'installedOnlyOrOtherTree': sum(not x['productionTrees'] for x in records),
            'candidateTsv': OUT_TSV.relative_to(ROOT).as_posix(),
            'candidateTsvSha256': tsv_hash,
            'historicalAndroidNativeMatrixTsv': OUT_APK_MATRIX_TSV.relative_to(ROOT).as_posix(),
            'historicalAndroidNativeMatrixTsvSha256': android_matrix_hash,
            'files': records,
        },
        'observedHostNativeLoads': observed_review,
        'historicalAndroidBuildEvidence': android_builds,
        'historicalAndroidNativeArtifactMatrix': android_library_matrix,
        'currentAndroidPackagingNativeInputs': android_packaging_graph,
        'p3a006ImageNativeAudit': p3a006_native_audit,
        'policy': {
            'decision': 'Reject all Linux GNU/GLIBC, Linux musl, Darwin and Windows prebuilt native payloads from an Android ARM64/Bionic runtime image unless rebuilt and re-audited for Android.',
            'acceptedAndroidWebRuntimeNativeArtifacts': [],
            'reason': 'The reproducible P3A-006 host candidate reports no included OS-native artifact and rejects its host-native candidates. The Android Gradle graph declares ten APK native inputs, but this worktree contains no APK/AAB or extracted native bytes to qualify that separate closure.',
        },
        'openAcceptanceGaps': [
            'The current Android Gradle/CMake graph declares ten native package inputs (six runtime libraries, two node-pty libraries, the RuntimeService JNI bridge, and a process-capability proof executable), but no raw APK/AAB or native ELF payload is present in the worktree for exact packaged-hash inspection.',
            'P3A-006 is a reproducible host package/static-asset candidate; its empty in-archive native list does not prove the separate Android APK/runtime ELF set is empty or qualified.',
            'The P3A-001 host-loaded addon is an x86-64 Linux GNU ELF requiring glibc and is explicitly rejected for Android.',
            'P3A-003 package-tree membership is not proof that any candidate file is required by the Web Profile.',
            'Historical APK min SDK and arm64-v8a metadata are package-level context; they do not prove each ELF minimum API note or Android build target.',
            'Build-output hash linkage is absent for most historical libraries; recorded require-builtin and atomic build hashes differ from their packaged ELF hashes.',
            'Retained readelf checks cover only selected carrier/probe/fixture binaries and are not cryptographically bound to every packaged-library hash; full symbol/version requirements and per-artifact license notice mapping remain incomplete.',
            'The app main source set currently stages the process-capability proof executable and PTY fixture; their production-release scope requires explicit review.',
            'The Android APK test profile records incomplete dependency distribution and cannot substitute for the Web Runtime Image.',
        ],
        'acceptance': {'p3a004Complete': False, 'next': 'Build or locate the exact Android APK for the current Gradle graph, extract all packaged ARM64/Bionic ELF files, resolve proof-only fixture/probe packaging, and bind every selected artifact hash to build/toolchain/readelf/dependency/API/alignment/license evidence.'},
    }
    json_text = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    return raw_tsv, android_matrix, json_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify generated TSV and JSON evidence match current inputs')
    args = parser.parse_args()
    raw_tsv, android_matrix, json_text = build_outputs()
    if args.check:
        mismatches = []
        for path, expected in ((OUT_TSV, raw_tsv), (OUT_APK_MATRIX_TSV, android_matrix), (OUT_JSON, json_text)):
            if not path.exists() or path.read_text(encoding='utf-8') != expected:
                mismatches.append(path.relative_to(ROOT).as_posix())
        if mismatches:
            print('P3A-004 evidence stale: ' + ', '.join(mismatches), file=sys.stderr)
            return 1
        print(f'P3A-004 evidence current: {OUT_TSV.relative_to(ROOT)}; {OUT_APK_MATRIX_TSV.relative_to(ROOT)}; {OUT_JSON.relative_to(ROOT)}')
        return 0
    OUT_TSV.write_text(raw_tsv, encoding='utf-8')
    OUT_APK_MATRIX_TSV.write_text(android_matrix, encoding='utf-8')
    OUT_JSON.write_text(json_text, encoding='utf-8')
    print(f'Wrote {OUT_TSV.relative_to(ROOT)} ({len(raw_tsv.encode())} bytes)')
    print(f'Wrote {OUT_APK_MATRIX_TSV.relative_to(ROOT)} ({len(android_matrix.encode())} bytes)')
    print(f'Wrote {OUT_JSON.relative_to(ROOT)} ({len(json_text.encode())} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
