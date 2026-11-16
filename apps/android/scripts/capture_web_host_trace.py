#!/usr/bin/env python3
"""Capture separate host syscall and Node-loader observations for one Web Profile spec."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
AUDITOR = ROOT / 'apps/android/scripts/audit_web_host_trace.py'
MODULE_OBSERVER = ROOT / 'apps/android/scripts/web_profile_module_observer.mjs'
PROFILE_HELPER = ROOT / 'apps/cli/tests/profiles/web/tests/default-web-process.ts'
CAPTURE_DRIVER = Path(__file__).resolve()
VITEST_CONFIG = 'apps/android/tests/vitest.web-host.config.mjs'
SPECS = {
    'bootstrap': 'apps/android/tests/web-bootstrap.host.spec.mjs',
    'bounded': 'apps/android/tests/web-bounded-profile.host.spec.mjs',
}
TRACE_SET = '%file,%process,fcntl,dup,dup2,dup3,close,close_range,getdents,getdents64'
SENSITIVE_ENV_MARKERS = ('API_KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL')
UNOBSERVED_SYSCALL_CLASSES = [
    {'class': 'file content transfer', 'examples': ['read', 'readv', 'pread64', 'preadv', 'preadv2', 'write', 'writev', 'pwrite64', 'pwritev', 'pwritev2', 'sendfile', 'copy_file_range', 'splice']},
    {'class': 'memory mapping and protection', 'examples': ['mmap', 'mprotect', 'munmap', 'mremap']},
    {'class': 'network sockets and payloads', 'examples': ['socket', 'connect', 'bind', 'listen', 'accept', 'sendto', 'recvfrom', 'sendmsg', 'recvmsg']},
    {'class': 'I/O readiness and multiplexing', 'examples': ['poll', 'ppoll', 'select', 'pselect6', 'epoll_ctl', 'epoll_wait', 'epoll_pwait', 'epoll_pwait2']},
    {'class': 'device-specific control', 'examples': ['ioctl']},
]
KNOWN_UNOBSERVED_PATH_SCOPES = [
    {
        'scope': 'Android app-private runtime and data directories',
        'pathOrUrlPatterns': ['/data/user/<user>/<applicationId>/**', '/data/user_de/<user>/<applicationId>/**', '/data/data/<applicationId>/**'],
        'reason': 'Both captures ran on Linux; no Android application process or app-private filesystem was present.',
    },
    {
        'scope': 'Android WebView packaged/local assets',
        'pathOrUrlPatterns': ['file:///android_asset/**', 'https://appassets.androidplatform.net/**'],
        'reason': 'The bounded spec supplies the appassets origin only as an HTTP header; neither spec starts WebView or loads a local Android asset URL.',
    },
    {
        'scope': 'Provider-specific model and credential files',
        'pathOrUrlPatterns': [],
        'reason': 'No model/provider request or Android credential-store read is part of these host specs; exact future paths are not asserted.',
    },
    {
        'scope': 'Conditional or lazy paths outside the two host test flows',
        'pathOrUrlPatterns': [],
        'reason': 'The specs exercise boot graphs, client batches and selected HTTP checks, not arbitrary user sessions or every optional branch.',
    },
]
BOUNDED_DISABLED_PROVIDER_ROWS = [
    {'id': 'subprocess', 'package': '@deepseek-ai/dsh-subprocess-local'},
    {'id': 'bash-sandbox', 'package': '@deepseek-ai/dsh-bash-sandbox'},
    {'id': 'pwsh-sandbox', 'package': '@deepseek-ai/dsh-pwsh-sandbox'},
    {'id': 'open-in-app', 'package': '@deepseek-ai/dsh-host-open-in-app'},
    {'id': 'directory-picker', 'package': '@deepseek-ai/dsh-host-directory-picker-auto'},
    {'id': 'mcp-manager', 'package': '@deepseek-ai/dsh-mcp-manager'},
]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def run(command, *, env, cwd, stdout_path, stderr_path):
    with stdout_path.open('wb') as stdout, stderr_path.open('wb') as stderr:
        completed = subprocess.run(command, cwd=cwd, env=env, stdout=stdout, stderr=stderr, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f'Command failed with exit code {completed.returncode}: {command!r}; '
            f'inspect {stdout_path} and {stderr_path}'
        )
    return completed.returncode


def node_version(node):
    output = subprocess.run([node, '--version'], check=True, capture_output=True, text=True).stdout.strip()
    match = re.fullmatch(r'v(\d+)\.(\d+)\.(\d+)', output)
    if not match:
        raise RuntimeError(f'Unrecognized Node version string: {output!r}')
    version = tuple(int(part) for part in match.groups())
    if version < (24, 9, 0):
        raise RuntimeError(f'Node >=24.9.0 is required; found {output}')
    return output


def test_environment():
    env = os.environ.copy()
    for key in tuple(env):
        if key == 'NODE_OPTIONS' or any(marker in key.upper() for marker in SENSITIVE_ENV_MARKERS):
            env.pop(key, None)
        if key.startswith('ANDROID_WEB_PROFILE_MODULE_'):
            env.pop(key, None)
    return env


def coverage_blind_spots(spec):
    path_scopes = [dict(scope) for scope in KNOWN_UNOBSERVED_PATH_SCOPES]
    if spec == 'bounded':
        path_scopes.append({
            'scope': 'Implementations behind disabled bounded-profile provider rows',
            'pathOrUrlPatterns': [],
            'providerRows': BOUNDED_DISABLED_PROVIDER_ROWS,
            'reason': 'The hashed host-only overlay disables these rows; exact implementation paths are not inferred from their absence in this trace.',
        })
    return {
        'syscallTraceSet': TRACE_SET,
        'unobservedSyscallClasses': UNOBSERVED_SYSCALL_CLASSES,
        'knownUnobservedPathScopes': path_scopes,
        'additionalLimitations': [
            'Only the selected Linux Web-profile test process tree is summarized; raw runner traces remain in the archive.',
            'Initial file descriptors and clone-time descriptor-table sharing are not fully known.',
            'Directory enumeration records do not expose all entries as dependencies.',
            'No path absent from the trace is proven unnecessary; unvisited conditional and lazy paths are not exhaustively enumerable from these runs.',
        ],
        'scopeNote': 'Examples identify known omissions from this configured host capture, not an exhaustive list of every syscall or path the application could use.',
    }


def summarize_path_operations(events):
    grouped = {}
    without_path_name = 0
    unique_paths = set()
    open_flag_positions = {'open': 1, 'openat': 2, 'openat2': 2}
    for event in events:
        syscall = event.get('syscall', 'unknown')
        arguments = event.get('arguments', [])
        open_flags = None
        flag_index = open_flag_positions.get(syscall)
        if flag_index is not None and flag_index < len(arguments):
            open_flags = arguments[flag_index]
        for path_record in event.get('paths', []):
            path_literal = path_record.get('decodedPath')
            resolved_path = path_record.get('path')
            raw_argument = path_record.get('raw') if path_literal is None and resolved_path is None else None
            if not any(isinstance(value, str) and value for value in (path_literal, resolved_path, raw_argument)):
                without_path_name += 1
                continue
            resolution = path_record.get('resolution', 'unknown')
            outcome = event.get('outcome', 'unknown')
            errno = event.get('errno')
            key = (path_literal, resolved_path, raw_argument, resolution, syscall, outcome, errno, open_flags)
            unique_paths.add((path_literal, resolved_path, resolution))
            item = grouped.get(key)
            if item is None:
                item = {
                    'pathLiteral': path_literal,
                    'resolvedPath': resolved_path,
                    'rawPathArgument': raw_argument,
                    'resolution': resolution,
                    'syscall': syscall,
                    'category': event.get('category', 'unknown'),
                    'outcome': outcome,
                    'errno': errno,
                    'openFlags': open_flags,
                    'observationCount': 0,
                    'processIds': set(),
                    'evidenceReferenceCount': 0,
                    'evidenceExamples': [],
                }
                grouped[key] = item
            item['observationCount'] += 1
            item['evidenceReferenceCount'] += 1
            if isinstance(event.get('pid'), int):
                item['processIds'].add(event['pid'])
            if len(item['evidenceExamples']) < 3:
                item['evidenceExamples'].append({
                    'traceFile': event.get('traceFile'),
                    'pid': event.get('pid'),
                    'line': event.get('line'),
                })
    rows = list(grouped.values())
    for item in rows:
        item['processIds'] = sorted(item['processIds'])
    rows.sort(key=lambda item: (
        item['resolvedPath'] or item['pathLiteral'] or item['rawPathArgument'] or '',
        item['resolution'], item['syscall'], item['outcome'], item['errno'] or '', item['openFlags'] or '',
    ))
    return {
        'uniqueObservedPathCount': len(unique_paths),
        'pathOperationRowCount': len(rows),
        'pathRecordsWithoutPathNameCount': without_path_name,
        'operations': rows,
        'contentTransferObserved': False,
        'interpretation': 'Rows record path-bearing syscall operations and outcomes only. An open or metadata success does not prove bytes were read or that the path is required.',
    }


def summarize_link_targets(events):
    grouped = {}
    for event in events:
        target = event.get('linkTarget')
        if not isinstance(target, str):
            continue
        paths = event.get('paths', [])
        path_record = paths[0] if paths else {}
        path_literal = path_record.get('decodedPath')
        resolved_path = path_record.get('path')
        key = (path_literal, resolved_path, target, event.get('syscall'), event.get('outcome'))
        item = grouped.get(key)
        if item is None:
            item = {
                'pathLiteral': path_literal,
                'resolvedPath': resolved_path,
                'linkTarget': target,
                'syscall': event.get('syscall'),
                'outcome': event.get('outcome'),
                'observationCount': 0,
                'evidenceExamples': [],
            }
            grouped[key] = item
        item['observationCount'] += 1
        if len(item['evidenceExamples']) < 3:
            item['evidenceExamples'].append({
                'traceFile': event.get('traceFile'), 'pid': event.get('pid'), 'line': event.get('line'),
            })
    return sorted(grouped.values(), key=lambda item: (item['resolvedPath'] or item['pathLiteral'] or '', item['linkTarget']))


def summarize_realpath_records(module_records):
    grouped = {}
    for record in module_records:
        if record.get('recordType') != 'module_trace_realpath':
            continue
        key = (record.get('path'), record.get('resolvedPath'), record.get('outcome'), record.get('errorCode'))
        item = grouped.get(key)
        if item is None:
            item = {
                'path': key[0], 'resolvedPath': key[1], 'outcome': key[2], 'errorCode': key[3],
                'observationCount': 0, 'evidenceExamples': [],
            }
            grouped[key] = item
        item['observationCount'] += 1
        if len(item['evidenceExamples']) < 3:
            item['evidenceExamples'].append({
                'moduleTraceLine': record.get('line'), 'pid': record.get('pid'),
            })
    return sorted(grouped.values(), key=lambda item: (item['path'] or '', item['resolvedPath'] or '', item['outcome'] or ''))


def compact_report(result):
    events = result.pop('events')
    module_records = result.pop('userSpaceLoaderRecords')
    result['observedPathOperations'] = summarize_path_operations(events)
    result['observedSymlinkTargets'] = summarize_link_targets(events)
    result['observedRealpathResolutions'] = summarize_realpath_records(module_records)
    result['dependencyAssessment'] = {
        'status': 'not_assessed',
        'inferredRequiredPaths': [],
        'inferencePerformed': False,
        'reason': 'No static import/asset analysis or controlled removal test is included. Observation alone is not a required-dependency verdict.',
    }
    result['syscallSummary'] = {
        'countsByName': dict(sorted(Counter(event['syscall'] for event in events).items())),
        'countsByOutcome': dict(sorted(Counter(event['outcome'] for event in events).items())),
        'pathResolutionCounts': dict(sorted(Counter(
            path.get('resolution', 'unknown') for event in events for path in event.get('paths', [])
        ).items())),
        'detailsStoredInRawTraceFiles': True,
    }
    module_counts = Counter(record['recordType'] for record in module_records)
    resolved_urls = sorted({record['resolvedURL'] for record in module_records
                            if record['recordType'] == 'module_trace_resolve'
                            and isinstance(record.get('resolvedURL'), str)})
    failed_resolutions = sorted({
        (record.get('specifier', ''), record.get('errorCode', 'Error'))
        for record in module_records if record['recordType'] == 'module_trace_resolve-failed'
    })
    result['userSpaceLoaderSummary'] = {
        'countsByKind': dict(sorted(module_counts.items())),
        'uniqueResolvedModuleUrlCount': len(resolved_urls),
        'uniqueResolvedModuleUrls': resolved_urls,
        'uniqueFailedResolutionCount': len(failed_resolutions),
        'failedResolutionExamples': [
            {'specifier': specifier, 'errorCode': error_code}
            for specifier, error_code in failed_resolutions[:50]
        ],
        'nativeLoadEvents': [
            {key: record[key] for key in ('pid', 'filename', 'outcome', 'errorCode') if key in record}
            for record in module_records if record['recordType'] == 'module_trace_dlopen'
        ],
        'interpretation': 'Successful module resolution records a resolvable URL, not proof that the module was evaluated or required; process.dlopen results are separate native-load observations.',
        'detailsStoredInRawModuleTrace': True,
    }
    result['detailedRecordRetention'] = {
        'syscallEventCount': len(events),
        'moduleRecordCount': len(module_records),
        'eventArraysOmittedFromSummary': True,
        'rawFilesAreRequiredForEventLevelReview': True,
    }
    return result


def write_path_inventory(report, output_path):
    inventory = {
        'schemaVersion': 1,
        'observedPathOperations': report['observedPathOperations'],
        'observedSymlinkTargets': report['observedSymlinkTargets'],
        'observedRealpathResolutions': report['observedRealpathResolutions'],
    }
    payload = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as raw_file:
        with gzip.GzipFile(fileobj=raw_file, mode='wb', mtime=0) as compressed:
            compressed.write(payload)

    operation_summary = report['observedPathOperations']
    operation_summary.pop('operations')
    operation_summary['detailsStoredInPathObservationInventory'] = True
    report['observedSymlinkTargets'] = {
        'distinctObservationRows': len(inventory['observedSymlinkTargets']),
        'detailsStoredInPathObservationInventory': True,
    }
    report['observedRealpathResolutions'] = {
        'distinctResolutionRows': len(inventory['observedRealpathResolutions']),
        'detailsStoredInPathObservationInventory': True,
    }
    return {
        'schemaVersion': 1,
        'path': output_path.name,
        'format': 'gzip-json',
        'sha256': sha256(output_path),
        'compressedBytes': output_path.stat().st_size,
        'uncompressedBytes': len(payload),
        'pathOperationRows': operation_summary['pathOperationRowCount'],
        'uniqueObservedPaths': operation_summary['uniqueObservedPathCount'],
        'symlinkTargetRows': len(inventory['observedSymlinkTargets']),
        'realpathResolutionRows': len(inventory['observedRealpathResolutions']),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, choices=sorted(SPECS),
                        help='run exactly one host spec so the traced root is unambiguous')
    parser.add_argument('--output', required=True, type=Path,
                        help='new summary JSON path; existing files are never overwritten')
    parser.add_argument('--path-inventory-output', type=Path,
                        help='new compressed path-inventory JSON path; defaults beside the summary')
    parser.add_argument('--raw-dir', required=True, type=Path,
                        help='new private, external directory for per-PID traces, module JSONL, and test logs')
    parser.add_argument('--overlay', type=Path,
                        help='repository overlay to verify in the Web root launch (required for --spec bounded)')
    args = parser.parse_args()

    if not AUDITOR.is_file() or not MODULE_OBSERVER.is_file() or not PROFILE_HELPER.is_file():
        raise RuntimeError('P3A-001 auditor, module observer, or profile test helper is missing')
    if not (ROOT / 'node_modules/.bin/vitest').exists():
        raise RuntimeError('Workspace dependencies are missing; install with pnpm install --frozen-lockfile')
    if not (ROOT / 'apps/cli/lib/bin.js').is_file():
        raise RuntimeError('Built CLI is missing; build artifacts before tracing with pnpm run build:artifacts')
    strace = shutil.which('strace')
    if strace is None:
        raise RuntimeError('strace is required for the Linux host syscall observation')
    node = shutil.which('node')
    if node is None:
        raise RuntimeError('Node is not on PATH')
    node_version_value = node_version(node)
    pnpm = ROOT / 'node_modules/.bin/pnpm'
    if not pnpm.exists():
        raise RuntimeError('Workspace pnpm executable is missing; install locked dependencies first')
    syscall_support = subprocess.run([strace, '-e', f'trace={TRACE_SET}', '--', 'true'],
                                     check=False, capture_output=True, text=True)
    if syscall_support.returncode != 0:
        raise RuntimeError(f'Installed strace does not support the requested trace set: {syscall_support.stderr.strip()}')

    spec = ROOT / SPECS[args.spec]
    if not spec.is_file():
        raise RuntimeError(f'Host spec is missing: {spec}')
    overlay = args.overlay.resolve(strict=True) if args.overlay else None
    if args.spec == 'bounded' and overlay is None:
        raise RuntimeError('The bounded Web Profile capture requires --overlay')
    if args.spec == 'bootstrap' and overlay is not None:
        raise RuntimeError('--overlay is only valid with --spec bounded')
    if overlay is not None:
        overlay.relative_to(ROOT)

    output = args.output.resolve()
    inventory_output = (args.path_inventory_output.resolve() if args.path_inventory_output else
                        output.with_name(output.stem + '.path-inventory.json.gz'))
    raw_dir = args.raw_dir.resolve()
    if output.exists():
        raise RuntimeError(f'Refusing to overwrite existing summary: {output}')
    if inventory_output.exists():
        raise RuntimeError(f'Refusing to overwrite existing path inventory: {inventory_output}')
    if inventory_output == output:
        raise RuntimeError('Summary JSON and path inventory output must use different paths')
    if raw_dir == ROOT or ROOT in raw_dir.parents:
        raise RuntimeError('Raw traces must be kept outside the repository checkout')
    if raw_dir.exists():
        raise RuntimeError(f'Refusing to reuse an existing raw-trace directory: {raw_dir}')
    raw_dir.mkdir(parents=True, mode=0o700)
    output.parent.mkdir(parents=True, exist_ok=True)

    prefix = raw_dir / f'{args.spec}.syscall.trace'
    module_trace = raw_dir / f'{args.spec}.module.jsonl'
    module_pid_file = raw_dir / f'{args.spec}.module-root-pid'
    base_command = [
        str(pnpm), 'exec', 'vitest', 'run', '--config', VITEST_CONFIG, SPECS[args.spec],
    ]
    base_env = test_environment()

    # This pass traces the uninstrumented app. Runner syscalls are retained in raw files but filtered by the auditor's exact Web PID tree.
    syscall_command = [
        strace, '-ff', '-qq', '-yy', '-s', '8192',
        '-e', f'trace={TRACE_SET}', '-o', str(prefix), '--', *base_command,
    ]
    run(syscall_command, env=base_env, cwd=ROOT,
        stdout_path=raw_dir / f'{args.spec}.syscall.stdout.log',
        stderr_path=raw_dir / f'{args.spec}.syscall.stderr.log')
    traces = sorted(raw_dir.glob(f'{args.spec}.syscall.trace.*'))
    if not traces:
        raise RuntimeError('strace completed but produced no per-process trace files')

    # Node loader hooks perturb startup, so collect them in a distinct run and keep its syscall events separate.
    module_env = test_environment()
    module_env['ANDROID_WEB_PROFILE_MODULE_OBSERVER'] = str(MODULE_OBSERVER)
    module_env['ANDROID_WEB_PROFILE_MODULE_TRACE'] = str(module_trace)
    module_env['ANDROID_WEB_PROFILE_MODULE_ROOT_PID_FILE'] = str(module_pid_file)
    run(base_command, env=module_env, cwd=ROOT,
        stdout_path=raw_dir / f'{args.spec}.module.stdout.log',
        stderr_path=raw_dir / f'{args.spec}.module.stderr.log')
    if not module_trace.is_file() or not module_pid_file.is_file():
        raise RuntimeError('Node module pass completed without its JSONL trace or exact profile PID file')
    module_root_pid_text = module_pid_file.read_text().strip()
    if not module_root_pid_text.isdecimal():
        raise RuntimeError(f'Invalid profile PID file contents: {module_root_pid_text!r}')
    module_root_pid = int(module_root_pid_text)

    with tempfile.TemporaryDirectory(prefix='dsh-p3a001-audit-') as temporary:
        parser_output = Path(temporary) / 'audited.json'
        audit_command = [
            sys.executable, str(AUDITOR), '--trace-glob', str(prefix) + '.*',
            '--discover-root', '--initial-cwd', str(ROOT),
            '--module-trace', str(module_trace), '--module-root-pid', str(module_root_pid),
            '--output', str(parser_output),
        ]
        if overlay is not None:
            audit_command.extend(['--overlay', str(overlay)])
        parsed = subprocess.run(audit_command, cwd=ROOT, check=False, capture_output=True, text=True)
        if parsed.returncode != 0:
            raise RuntimeError(f'Trace audit failed ({parsed.returncode}): {parsed.stderr.strip()}')
        result = compact_report(json.loads(parser_output.read_text()))

    result['pathObservationInventory'] = write_path_inventory(result, inventory_output)
    result['coverageBlindSpots'] = coverage_blind_spots(args.spec)

    strace_version = subprocess.run([strace, '-V'], check=True, capture_output=True, text=True)
    strace_lines = (strace_version.stdout or strace_version.stderr).splitlines()
    result['captureMetadata'] = {
        'capturedAtUtc': datetime.now(timezone.utc).isoformat(),
        'sourceBranch': subprocess.run(['git', 'branch', '--show-current'], cwd=ROOT,
                                       check=True, capture_output=True, text=True).stdout.strip(),
        'sourceHasUncommittedChanges': bool(subprocess.run(
            ['git', 'status', '--porcelain'], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()),
        'hostPlatform': sys.platform,
        'nodeVersion': node_version_value,
        'straceVersion': strace_lines[0] if strace_lines else 'unknown',
        'profile': 'web',
        'spec': SPECS[args.spec],
        'specSha256': sha256(spec),
        'profileHelperSha256': sha256(PROFILE_HELPER),
        'captureDriverSha256': sha256(CAPTURE_DRIVER),
        'auditorSha256': sha256(AUDITOR),
        'initialWorkingDirectory': '.',
        'syscallTraceSet': TRACE_SET,
        'syscallTraceArgumentsOmitEnvironmentValues': True,
        'sensitiveEnvironmentVariablesRemovedBeforeTestLaunch': True,
        'syscallObservationPass': 'Uninstrumented Node Web Profile test under strace; test runner is filtered by exact profile PID and descendants.',
        'moduleObservationPass': 'Separate test-only Node module.registerHooks/process.dlopen/fs.realpath observer run; its syscalls are not merged into the baseline.',
        'modulePassPidsAreSeparateFromSyscallPass': True,
        'nodeOptionsInstrumentationAppliedToProfileChildOnly': True,
        'testOnlyRuntimeRosterObserverIncluded': True,
        'moduleObserverPath': MODULE_OBSERVER.relative_to(ROOT).as_posix(),
        'moduleObserverSha256': sha256(MODULE_OBSERVER),
        'modulePassRootPid': module_root_pid,
        'traceFiles': [
            {'name': trace.name, 'sha256': sha256(trace)} for trace in traces
        ],
        'moduleTrace': {
            'name': module_trace.name,
            'sha256': sha256(module_trace),
            'rootPidFile': module_pid_file.name,
        },
        'rawTraceDirectory': str(raw_dir),
        'rawTraceDirectoryOutsideRepository': True,
        'rawTraceArchiveStoredInRepository': False,
        'overlay': None if overlay is None else {
            'path': overlay.relative_to(ROOT).as_posix(),
            'sha256': sha256(overlay),
        },
        'androidExecuted': False,
        'androidDependencyClosureProven': False,
    }
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({
        'output': str(output),
        'rawDirectory': str(raw_dir),
        'selectedRootPid': result.get('selectedRootPid'),
        'traceFiles': result.get('traceFiles'),
        'syscallEvents': result['detailedRecordRetention']['syscallEventCount'],
        'loaderRecords': result['detailedRecordRetention']['moduleRecordCount'],
        'pathInventory': result['pathObservationInventory'],
        'observationsComplete': result.get('observationsComplete'),
        'androidExecuted': False,
        'androidDependencyClosureProven': False,
    }, indent=2))


if __name__ == '__main__':
    main()
