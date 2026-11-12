"""Check APK #2 original-profile evidence without inferring app restart or model/tool success."""
import argparse
import json
from pathlib import Path
import re


def validate(value: dict, build: dict, *, require_previous_invocation: bool = False) -> None:
    """Reject mismatched artifacts, incomplete original recovery or unsupported success claims."""
    def need(condition, message):
        if not condition:
            raise ValueError(message)

    need(value.get('schemaVersion') == 1, 'Wrong result version')
    need(value.get('apkSha256') == build['apkSha256']['app-debug.apk'], 'APK digest mismatch')
    need(value.get('nativePublicationSha256') == build['packagedLibraries']['libharness_atomic.so']['sha256'], 'Publication binding digest mismatch')
    need(value.get('platform') == 'android' and value.get('arch') == 'arm64' and value.get('node') == 'v24.22.1', 'Wrong Node platform')
    need(value.get('device', {}).get('api', 0) >= 29 and bool(value.get('device', {}).get('model')), 'Missing Android device information')
    need(value.get('serverInfo', {}).get('name') == 'deepseek-harness-sdk-runtime' and value.get('profile') == 'sdk-minimal', 'Wrong original runtime/profile')
    need(value.get('nativeInternalLoader', {}).get('product') == 'require-builtin'
         and value.get('nativeInternalLoader', {}).get('abi') == 'napi-v9', 'Original internal loader unverified')
    for key in ['harnessStarted', 'sessionRecoveredAcrossRuntimeRestart', 'recoveredNondefaultDirectory']:
        need(value.get(key) is True, 'Incomplete original session recovery: ' + key)
    for key in ['modelRequestExecuted', 'approvedCommandExecuted', 'appRestartVerified', 'gate2Passed', 'installedPublicationBindingWritable']:
        need(value.get(key) is False, 'Unsupported/missing success or writable binding: ' + key)
    diagnostics = value.get('persistenceDiagnostics', {})
    need(diagnostics.get('shutdownAcknowledgements') == 2, 'SDK shutdown not acknowledged twice')
    need(diagnostics.get('sessionIntegrityAfterRejectedRecovery') is True, 'JSONL integrity after rejection unverified')
    need(diagnostics.get('missingSessionFailure', {}).get('name') == 'JsonRpcResponseError', 'Original missing-session denial absent')
    storage = diagnostics.get('storage', {})
    need(storage.get('publicationStrategy') == 'renameat2-noreplace', 'Wrong publication strategy')
    need(all(storage.get(key) is True for key in ['directorySync', 'fileSync', 'exclusivePreparedFilePublish', 'existingPathRejected']), 'Publication/sync prerequisite missing')
    uid = value.get('supervisorUid', 0)
    identity = value.get('kernelIdentity', {})
    need(uid >= 10000 and identity.get('uid') == uid and identity.get('pid') == value.get('pid')
         and identity.get('parentPid') == value.get('supervisorPid') and value.get('pid') != value.get('supervisorPid'), 'Wrong runtime identity')
    persisted = value.get('persistedJsonlSha256', {})
    need(bool(persisted) and isinstance(persisted, dict), 'No real JSONL digest evidence')
    for name, digest in persisted.items():
        need(not name.startswith('/') and '..' not in name.split('/') and name.endswith('.jsonl')
             and isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest) is not None, 'Invalid persisted JSONL entry')
    if require_previous_invocation:
        need(value.get('previousRunSessionRecovered') is True, 'Previous-invocation session not recovered')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--build-record', type=Path, required=True)
    parser.add_argument('--require-previous-invocation', action='store_true')
    args = parser.parse_args()
    validate(json.loads(args.result.read_text()), json.loads(args.build_record.read_text()),
             require_previous_invocation=args.require_previous_invocation)
    print('Original runtime/session assertions PASS; app restart, model and approved command remain separate evidence.')


if __name__ == '__main__':
    main()
