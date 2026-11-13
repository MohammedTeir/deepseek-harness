"""Validate Gate 3 OS probe reports; does not certify original terminal integration."""
import argparse
import json
from pathlib import Path


def validate(value, build, allow_partial=False):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(value.get('schemaVersion') == 1 and value.get('suite') == 'android-process-capability-v1', 'Wrong suite')
    require(value.get('platform') == 'android' and value.get('architecture') == 'aarch64', 'Actual Android ARM64 result required')
    require(value.get('nativeExitCode') == 0, 'Native execution failed')
    require(value.get('status') == 'PASS' or (allow_partial and value.get('status') == 'PARTIAL'), 'Incomplete/failed capabilities')
    require(value.get('apkSha256') == build['apkSha256']['app-debug.apk'], 'APK mismatch')
    require(value.get('nativeProbeSha256') == build['processProbe']['sha256'], 'Native probe mismatch')
    uid = value.get('uid', 0)
    require(type(uid) is int and uid > 0 and uid == value.get('supervisorUid'), 'Ordinary UID mismatch')
    require(value.get('parentPid') == value.get('supervisorPid') and value.get('pid') != value.get('supervisorPid'), 'Supervisor identity mismatch')
    require(value.get('installedProbeWritable') is False and value.get('execPath', '').endswith('/libharness_process_probe.so'), 'Installed immutable executable required')
    require(value.get('cwd') == value.get('expectedWorkspace'), 'Native workspace mismatch')
    require(value.get('device', {}).get('api', 0) >= 29, 'Device details missing')
    require(value.get('gate3Passed') is False and value.get('generalShellProviderImplemented') is False and value.get('originalTerminalIntegrated') is False, 'Unsupported scope claim')
    cases = value.get('cases', {})
    for name in ['streaming', 'backpressure', 'missingExecutable', 'cancellation', 'timeoutAndKill', 'descendantGroup']:
        require(cases.get(name, {}).get('reaped') is True, name + ' was not reaped')
    stream = cases['streaming']
    require(stream.get('stdout') == 'OUT-1\nOUT-2\n' and stream.get('stderr') == 'ERR-1\nERR-2\n' and stream.get('exitCode') == 7, 'Real separate streams/exit mismatch')
    require(stream.get('streamObservedBeforeAckAndExit') is True, 'No live streaming evidence')
    pressure = cases['backpressure']
    require(pressure.get('stdoutBytes') == pressure.get('stderrBytes') == 16384 and pressure.get('completeBytesVerified') is True and pressure.get('exitCode') == 9, 'Backpressure verification incomplete')
    require(cases['missingExecutable'].get('exitCode') == 127 and 'exec errno=2' in cases['missingExecutable'].get('stderr', ''), 'Launch-error propagation missing')
    require(cases['cancellation'].get('signal') == 15 and cases['cancellation'].get('explicitCancellation') is True and cases['cancellation'].get('timedOut') is False, 'Explicit cancellation failed')
    require(cases['timeoutAndKill'].get('signal') == 9 and cases['timeoutAndKill'].get('timedOut') is True, 'Timeout/KILL escalation missing')
    require(cases['descendantGroup'].get('descendantReaped') is True and cases['descendantGroup'].get('exitCode') == 0, 'Cooperative descendant cleanup missing')
    require(value.get('nativeWorkersRequireParentDeathKill') is True, 'Native worker lifecycle setup missing')
    shell = cases.get('systemShell', {})
    if shell.get('status') == 'UNAVAILABLE':
        require(allow_partial and value.get('status') == 'PARTIAL', 'System shell unavailable')
    else:
        require(value.get('shellTestPath') == '/system/bin/sh' and shell.get('stdout') == 'SH-OUT\n' + value['cwd'] + '\n' and shell.get('stderr') == 'SH-ERR\n' and shell.get('exitCode') == 7, 'Fixed system shell result mismatch')
    pty = value.get('pty', {})
    if pty.get('status') == 'UNAVAILABLE':
        require(allow_partial and value.get('status') == 'PARTIAL' and type(pty.get('errno')) is int and pty['errno'] != 0, 'PTY unavailable details missing')
    else:
        require(pty.get('status') == 'PASS' and pty.get('reaped') is True and pty.get('exitCode') == 0, 'PTY failed')
        require(pty.get('stdinStdoutStderrAreTty') is True and pty.get('resizeAndInputVerified') is True and pty.get('stderrMergedByPty') is True, 'Interactive PTY/resize not verified')
        require('TTY-INPUT:pty-input ROWS:40 COLS:100' in pty.get('combinedOutput', '') and 'TTY-STDERR' in pty.get('combinedOutput', ''), 'PTY output evidence missing')
    require(set(value.get('discovery', {})) == {'sh', 'pwd', 'printf', 'cat', 'sleep', 'echo', 'stty', 'toybox', 'git', 'curl', 'python3', 'ssh'}, 'Fixed availability inventory missing')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--build-record', type=Path, required=True)
    parser.add_argument('--allow-partial', action='store_true', help='Validate unavailable-capability diagnostics without accepting Gate 3')
    args = parser.parse_args()
    validate(json.loads(args.result.read_text()), json.loads(args.build_record.read_text()), args.allow_partial)
    print('PASS: supplied OS probe record is consistent; device attribution and remaining terminal capabilities require review')
