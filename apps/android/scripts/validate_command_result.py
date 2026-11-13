"""Validate supplied APK #3 phone evidence; parser success is not independent instrumentation."""
import argparse
import json
from pathlib import Path


def validate(value, build, require_subprocess=False):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(value.get('schemaVersion') == 1 and value.get('suite') == 'original-harness-approved-pwd-v1', 'Wrong suite')
    require(value.get('platform') == 'android' and value.get('arch') == 'arm64' and value.get('node') == 'v24.22.1', 'Wrong runtime')
    require(value.get('device', {}).get('api', 0) >= 29, 'Device API missing')
    for key in ['harnessStarted', 'originalRegistryAndPipeline', 'approvedCommandExecuted', 'sessionRecoveredAcrossRuntimeRestart']:
        require(value.get(key) is True, key)
    require(value.get('gate2Passed') is False and value.get('modelRequestExecuted') is False, 'Unsupported claims')
    require(value.get('apkSha256') == build['apkSha256']['app-debug.apk'], 'APK mismatch')
    for field, library in [('nativeNodeSha256', 'libnode_executable.so'), ('nativePublicationSha256', 'libharness_atomic.so')]:
        require(value.get(field) == build['packagedLibraries'][library]['sha256'], field)
    if require_subprocess:
        require(value.get('originalSubprocessService') is True, 'Original subprocess service missing')
        require(value.get('commandResult', {}).get('subprocessProvider') == 'android-fixed-pwd-v1', 'Fixed adapter result missing')
    native = value.get('nativeBroker', {})
    uid = value.get('supervisorUid', 0)
    require(type(uid) is int and uid > 0 and native.get('uid') == uid == value.get('kernelIdentity', {}).get('uid'), 'UID mismatch')
    require(value.get('kernelIdentity', {}).get('parentPid') == value.get('supervisorPid') and value.get('supervisorPid', 0) > 0, 'Supervisor mismatch')
    require(native.get('sessionId') == value.get('sessionId') and native.get('processLaunches') == 1, 'Native session/launch count')
    calls = native.get('callIds', [])
    require(len(calls) == 2 and calls[0] != calls[1], 'Call identities missing')
    require(value.get('approvalOutcomes') == [{'callId': calls[0], 'outcome': 'rejected'}, {'callId': calls[1], 'outcome': 'allowed-once'}], 'Human decisions differ')
    result = value.get('commandResult', {})
    require(result.get('cwd') == native.get('cwd') and result.get('stdout') == native.get('cwd', '') + '\n', 'Real pwd output mismatch')
    require(result.get('nativeConcurrentConsumers') == 2 and result.get('nativeConcurrentRejections') == 1, 'Concurrent consumption missing')
    require(type(result.get('exitCode')) is int and result['exitCode'] == 0 and isinstance(result.get('stderr'), str), 'Exit/stderr missing')
    expected = {'unapproved': 'APPROVAL_REQUIRED', 'unauthenticated': 'UNAUTHENTICATED', 'approvalMethod': 'UNSUPPORTED_ACTION',
                'malformed': 'MALFORMED_OR_DISCONNECTED', 'duplicate': 'DUPLICATE', 'replay': 'USED', 'uid': 'MALFORMED'}
    expected.update({key: 'REQUEST_CHANGED' for key in ['command', 'arguments', 'cwd', 'session', 'call']})
    for name, code in expected.items():
        reply = value.get('negative', {}).get(name, {})
        require(reply.get('ok') is False and reply.get('code') == code, 'Negative result: ' + name)
    history = value.get('history', [])
    require(history and history == value.get('recoveredHistory'), 'History did not recover unchanged')
    asked = [e['data'] for e in history if e['type'] == 'approval/asked']
    decided = [e['data'] for e in history if e['type'] == 'approval/decided']
    require([e.get('callId') for e in asked] == calls and all(e.get('toolName') == 'android_qualified_pwd' for e in asked), 'Original approval calls missing')
    require([e.get('id') for e in asked] == [e.get('id') for e in decided] and [e.get('outcome') for e in decided] == ['rejected', 'allowed-once'], 'Audit correlation mismatch')
    batches = [json.loads(e['data']['text']) for e in history if e['type'] == 'command/done']
    require(len(batches) == 2 and [b['callId'] for b in batches] == calls, 'Canonical tool results missing')
    denied, allowed = [b['batch']['results'][0]['result'] for b in batches]
    require(denied.get('isError') is True and denied.get('error', {}).get('info', {}).get('code') == 'APPROVAL_REJECTED', 'Original denial missing')
    require(allowed.get('isError') is False and json.loads(allowed['content'][0]['text']) == result, 'Original result differs')
    audit = native.get('audit', [])
    require(sum(e.get('code') == 'EXECUTED' for e in audit) == 1, 'Native execution audit missing')
    executions = [e for e in audit if e.get('code') == 'EXECUTED']
    require(value.get('kernelIdentity', {}).get('pid', 0) > 0 and executions[0].get('peerPid') != value['kernelIdentity']['pid'], 'Execution did not originate in the profile child')
    require(all(e.get('uid') == uid and e.get('peerPid', 0) > 0 for e in audit), 'Native peer credentials missing')
    hashes = value.get('persistedJsonlSha256', {})
    require(hashes and all(name.endswith('.jsonl') and isinstance(digest, str) and len(digest) == 64 for name, digest in hashes.items()), 'JSONL hashes missing')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--build-record', type=Path, required=True)
    parser.add_argument('--require-subprocess', action='store_true')
    args = parser.parse_args()
    validate(json.loads(args.result.read_text()), json.loads(args.build_record.read_text()), args.require_subprocess)
    print('PASS: supplied original-tool/native-command report matches required evidence; physical attribution must be reviewed separately')
