"""Strict allow/deny policy for Android native artifacts in runtime images."""
from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

POLICY_PATH = Path(__file__).resolve().parents[1] / 'runtime/native-artifact-policy.json'
SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


def policy_bytes(path: Path = POLICY_PATH) -> bytes:
    return path.read_bytes()


def policy_sha256(path: Path = POLICY_PATH) -> str:
    return hashlib.sha256(policy_bytes(path)).hexdigest()


def load_policy(path: Path = POLICY_PATH) -> dict:
    policy = json.loads(policy_bytes(path))
    if policy.get('schemaVersion') != 1 or policy.get('mode') != 'deny_unless_exact_hash_and_metadata_match':
        raise ValueError('Unsupported Android native-artifact policy')
    if not isinstance(policy.get('approvedArtifacts'), list):
        raise ValueError('Native artifact allowlist must be a list')
    return policy


def _valid_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or '\\' in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in {'', '.', '..'} for part in value.split('/'))


def _deny_reason(record: dict, policy: dict) -> str | None:
    path = record.get('path', '')
    for pattern in policy.get('denyPathPatterns', []):
        if fnmatch.fnmatchcase(path.lower(), pattern.lower()):
            return f'Android native-artifact deny pattern matched: {pattern}'
    role = record.get('artifactRole')
    if role in policy.get('denyArtifactRoles', []):
        return f'Android native-artifact role is denied: {role}'
    return None


def _validate_record_shape(record: object, policy: dict) -> dict:
    if not isinstance(record, dict):
        raise ValueError('Native artifact records must be objects')
    required = set(policy['requiredArtifactFields'])
    missing = sorted(required - record.keys())
    if missing:
        raise ValueError('Native artifact metadata missing required fields: ' + ', '.join(missing))
    if not _valid_relative_path(record['path']):
        raise ValueError('Unsafe native artifact path')
    if not SHA256_RE.fullmatch(str(record['sha256'])):
        raise ValueError('Native artifact SHA-256 must be lowercase hexadecimal')
    if not isinstance(record['soname'], str) or not record['soname'].endswith('.so') or '/' in record['soname']:
        raise ValueError('Native artifact SONAME must be a basename ending in .so')
    if not isinstance(record['neededLibraries'], list) or any(not isinstance(x, str) or '/' in x for x in record['neededLibraries']):
        raise ValueError('Native artifact DT_NEEDED entries must be library basenames')
    if not isinstance(record['minimumAndroidApi'], int) or isinstance(record['minimumAndroidApi'], bool) or record['minimumAndroidApi'] < 1:
        raise ValueError('Native artifact minimum Android API must be a positive integer')
    if not isinstance(record['elfClass'], int) or isinstance(record['elfClass'], bool):
        raise ValueError('Native artifact ELF class must be an integer')
    if not isinstance(record['licenseId'], str) or not record['licenseId'].strip():
        raise ValueError('Native artifact license identifier is required')
    if not _valid_relative_path(record['licenseEvidencePath']):
        raise ValueError('Native artifact license evidence path must be relative')
    return record


def validate_native_artifacts(records: object, policy: dict | None = None,
                              image_files: set[str] | None = None) -> list[dict]:
    """Accept only exact allowlist records with target metadata and closed dependencies.

    The function is intentionally default-deny: an empty allowlist accepts only an
    empty artifact list. Platform-library exceptions must be explicitly enumerated
    in policy['allowedSystemLibraries']; bundled dependencies must be in the set.
    """
    policy = policy or load_policy()
    if not isinstance(records, list):
        raise ValueError('nativeArtifacts must be a list')
    target = policy['target']
    allowed = {}
    for item in policy['approvedArtifacts']:
        approved = _validate_record_shape(item, policy)
        if approved['path'] in allowed:
            raise ValueError('Duplicate path in native artifact allowlist')
        denied = _deny_reason(approved, policy)
        if denied:
            raise ValueError('Invalid native artifact allowlist entry: ' + denied)
        allowed[approved['path']] = approved

    validated = []
    for raw in records:
        record = _validate_record_shape(raw, policy)
        denied = _deny_reason(record, policy)
        if denied:
            raise ValueError(denied)
        if record['operatingSystem'] != target['operatingSystem']:
            raise ValueError('Native artifact operating system is not Android')
        if record['abi'] != target['abi'] or record['machine'] != target['machine']:
            raise ValueError('Native artifact ABI/machine does not match Android arm64-v8a')
        if record['libc'] != target['libc']:
            raise ValueError('Native artifact libc is not Bionic')
        if record['elfClass'] != target['elfClass'] or record['elfType'] not in target['allowedElfTypes']:
            raise ValueError('Native artifact ELF class/type is not approved')
        if record['minimumAndroidApi'] > target['minimumApi']:
            raise ValueError('Native artifact minimum API exceeds the supported API 29 floor')
        if image_files is not None and record['licenseEvidencePath'] not in image_files:
            raise ValueError('Native artifact license evidence is absent from the image')
        approved = allowed.get(record['path'])
        if approved is None:
            raise ValueError('Native artifact is not on the exact-hash allowlist: ' + record['path'])
        if record != approved:
            raise ValueError('Native artifact metadata or hash differs from its allowlist entry: ' + record['path'])
        validated.append(record)

    sonames = [record['soname'] for record in validated]
    if len(sonames) != len(set(sonames)):
        raise ValueError('Duplicate native artifact SONAME')
    provided = set(sonames)
    system = set(policy.get('allowedSystemLibraries', []))
    for record in validated:
        missing = sorted(set(record['neededLibraries']) - provided - system)
        if missing:
            raise ValueError(f"Unclosed DT_NEEDED dependencies for {record['path']}: {', '.join(missing)}")
    return validated
