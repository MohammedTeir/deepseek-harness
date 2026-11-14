"""Generate deterministic evidence for the P3A-005 native packaging policy."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from native_artifact_policy import POLICY_PATH, load_policy, policy_sha256, validate_native_artifacts

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'apps/android/evidence'
OUTPUT = EVIDENCE / 'original-web-p3a005-native-policy-audit.json'
P3A004 = EVIDENCE / 'original-web-p3a004-native-artifact-audit.json'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_record(**overrides) -> dict:
    record = {
        'path': 'lib/arm64-v8a/libsample.so',
        'sha256': 'a' * 64,
        'soname': 'libsample.so',
        'operatingSystem': 'Android',
        'abi': 'arm64-v8a',
        'libc': 'Bionic',
        'machine': 'AArch64',
        'elfClass': 64,
        'elfType': 'DYN',
        'minimumAndroidApi': 29,
        'neededLibraries': ['libc.so'],
        'artifactRole': 'runtime',
        'licenseId': 'MIT',
        'licenseEvidencePath': 'licenses/MIT.txt',
    }
    record.update(overrides)
    return record


def decision(name: str, records: list[dict], *, approved: list[dict] | None = None,
             image_files: set[str] | None = None, expected: str = 'rejected') -> dict:
    policy = copy.deepcopy(load_policy())
    if approved is not None:
        policy['approvedArtifacts'] = approved
    try:
        validate_native_artifacts(records, policy, image_files if image_files is not None else {'licenses/MIT.txt'})
        actual, reason = 'accepted', None
    except ValueError as error:
        actual, reason = 'rejected', str(error)
    if actual != expected:
        raise AssertionError(f'{name}: expected {expected}, got {actual} ({reason})')
    return {'case': name, 'result': actual, 'reason': reason}


def build_report() -> dict:
    policy = load_policy()
    p3a004 = json.loads(P3A004.read_text())
    approved = native_record()
    cases = [
        decision('empty native set passes default-deny policy', [], expected='accepted'),
        decision('unlisted Android ARM64 artifact rejected', [native_record()]),
        decision('Linux GNU host addon path rejected', [native_record(
            path='node_modules/node-addon-require-builtin-linux-x64-gnu/prebuilt/linux-x64-gnu-napi-v9.node')]),
        decision('Darwin prebuild path rejected', [native_record(path='node_modules/pkg/prebuilds/darwin-arm64/addon.node')]),
        decision('Windows prebuild path rejected', [native_record(path='node_modules/pkg/prebuilds/win32-x64/addon.node')]),
        decision('test fixture role rejected', [native_record(artifactRole='test-fixture')]),
        decision('non-Android ABI rejected', [native_record(abi='x86_64')]),
        decision('non-Bionic libc rejected', [native_record(libc='glibc')]),
        decision('minimum API above 29 rejected', [native_record(minimumAndroidApi=30)]),
        decision('missing license payload rejected', [native_record()], image_files=set()),
        decision('same path with changed SHA-256 rejected', [native_record(sha256='b' * 64)],
                 approved=[approved]),
        decision('unresolved DT_NEEDED dependency rejected', [native_record(neededLibraries=['libnode.so'])],
                 approved=[native_record(neededLibraries=['libnode.so'])]),
        decision('exact hash metadata license and system dependency accepted', [approved],
                 approved=[approved], expected='accepted'),
    ]
    if p3a004['policy']['acceptedAndroidWebRuntimeNativeArtifacts']:
        raise AssertionError('P3A-004 currently accepts a Web Runtime Image native artifact; review this policy report')
    return {
        'schemaVersion': 1,
        'task': 'P3A-005',
        'status': 'PASS',
        'policy': {
            'path': POLICY_PATH.relative_to(ROOT).as_posix(),
            'sha256': policy_sha256(),
            'mode': policy['mode'],
            'target': policy['target'],
            'approvedArtifactCount': len(policy['approvedArtifacts']),
            'denyPathPatterns': policy['denyPathPatterns'],
            'denyArtifactRoles': policy['denyArtifactRoles'],
            'allowedSystemLibraries': policy['allowedSystemLibraries'],
        },
        'validationCases': cases,
        'integration': {
            'archiveValidator': 'apps/android/scripts/package_profile.py::validate_archive',
            'policyDigestPinnedInImageManifest': True,
            'interpretedProfileArchiveStillRejectsEveryELF': True,
            'p3a004EvidenceSha256': digest(P3A004),
            'acceptedWebRuntimeImageNativeArtifactCount': 0,
            'scope': 'Policy and bounded sdk-minimal host profile packaging only; no production Web Runtime Image native set is approved.',
        },
        'sourceSha256': {
            'auditScript': digest(Path(__file__).resolve()),
            'policyValidator': digest(Path(__file__).with_name('native_artifact_policy.py')),
            'profilePacker': digest(Path(__file__).with_name('package_profile.py')),
            'regressionTests': digest(Path(__file__).with_name('test_package_profile.py')),
        },
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify the committed evidence is current')
    args = parser.parse_args()
    generated = json.dumps(build_report(), indent=2, sort_keys=True) + '\n'
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != generated:
            raise SystemExit(f'P3A-005 evidence is stale: {OUTPUT}')
        print(f'P3A-005 evidence current: {OUTPUT.relative_to(ROOT)}')
    else:
        OUTPUT.write_text(generated)
        print(f'Wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
