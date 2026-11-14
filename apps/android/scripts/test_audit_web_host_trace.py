"""Trace parser tests use synthetic lines, never Android compatibility evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'apps/android/scripts/audit_web_host_trace.py'


class WebHostTraceAuditTest(unittest.TestCase):
    def run_report(self, trace_glob, output, *options):
        command = [sys.executable, str(SCRIPT), '--trace-glob', str(trace_glob),
                   '--output', str(output), *options]
        process = subprocess.run(command, capture_output=True, text=True)
        if process.returncode:
            self.fail(f'parser failed: {process.stderr}')
        return json.loads(output.read_text())

    def test_legacy_absolute_open_counts_and_native_observations_remain(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.1'
            trace.write_text('\n'.join([
                f'openat(AT_FDCWD, "{ROOT}/example/a.node", O_RDONLY|O_CLOEXEC) = 8',
                f'openat(AT_FDCWD, "{ROOT}/example/missing.node", O_RDONLY) = -1 ENOENT (No such file or directory)',
                'openat(AT_FDCWD, "relative.node", O_RDONLY) = 9',
                'openat(AT_FDCWD, "/outside/foreign.node", O_RDONLY) = 10',
                f'openat(AT_FDCWD, "{ROOT}/example/output.node", O_WRONLY) = 11',
                f'openat(AT_FDCWD, "{ROOT}/example/other.js", O_RDONLY) = 12',
            ]) + '\n')
            result = self.run_report(directory / 'trace.*', directory / 'evidence.json')
            self.assertEqual(result['schemaVersion'], 2)
            self.assertEqual(result['distinctSuccessfulAbsoluteCheckoutPaths'], 2)
            self.assertEqual(result['observedNativeAddons'], ['example/a.node'])
            self.assertEqual(result['relativePathObservations'], {'resolved': 0, 'unresolved': 1})
            self.assertIn('open', result['observedSyscallCategories'])
            self.assertEqual(result['observedNativeFiles'], ['example/a.node', 'example/output.node'])
            self.assertFalse(result['observationCompleteness']['syscallCoverageClaimed'])
            self.assertFalse(result['observationCompleteness']['fdGraphComplete'])
            self.assertFalse(result['androidExecuted'])
            self.assertFalse(result['completeAndroidGraph'])
            self.assertFalse(result['gate4Passed'])
            open_events = [event for event in result['events'] if event['syscall'] == 'openat']
            self.assertEqual([event['outcome'] for event in open_events],
                             ['success', 'error', 'success', 'success', 'success', 'success'])
            failed = open_events[1]
            self.assertEqual(failed['errno'], 'ENOENT')
            self.assertEqual(failed['paths'][0]['resolution'], 'absolute')

    def test_open_metadata_access_directory_read_readlink_and_exec_categories(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.20'
            trace.write_text('\n'.join([
                'open("/tmp/file", O_RDONLY) = 3</tmp/file>',
                'openat2(AT_FDCWD</tmp>, "file", {flags=O_RDONLY}, 24) = 4</tmp/file>',
                'statx(AT_FDCWD</tmp>, "file", AT_STATX_SYNC_AS_STAT, STATX_ALL, {}) = 0',
                'newfstatat(3</tmp/file>, "", {}, AT_EMPTY_PATH) = 0',
                'fstatat64(AT_FDCWD</tmp>, "legacy", {}, 0) = 0',
                'statvfs("/tmp", {}) = 0',
                'fstat(3</tmp/file>, {}) = 0',
                'access("/tmp/file", R_OK) = 0',
                'faccessat2(AT_FDCWD</tmp>, "file", R_OK, 0) = -1 EACCES (Permission denied)',
                'getdents64(5</tmp>, [{d_name="file"}], 1024) = 24',
                'readlinkat(AT_FDCWD</tmp>, "link", "/tmp/file", 4096) = 9',
                'readlink("/tmp/legacy-link", "/tmp/legacy-target", 4096) = 18',
                'execve("/bin/tool", ["tool"], 0) = -1 ENOENT (No such file or directory)',
                'execveat(AT_FDCWD</bin>, "tool", ["tool"], 0, 0) = 0',
            ]) + '\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json')
            categories = {event['syscall']: event['category'] for event in result['events']}
            self.assertEqual(categories, {
                'open': 'open', 'openat2': 'open', 'statx': 'metadata',
                'newfstatat': 'metadata', 'fstatat64': 'metadata', 'statvfs': 'metadata',
                'fstat': 'metadata', 'access': 'access',
                'faccessat2': 'access', 'getdents64': 'directory_read',
                'readlinkat': 'readlink', 'readlink': 'readlink',
                'execve': 'exec', 'execveat': 'exec',
            })
            events = {event['syscall']: event for event in result['events']}
            self.assertEqual(events['openat2']['paths'][0]['path'], '/tmp/file')
            self.assertEqual(events['newfstatat']['paths'][0]['resolution'], 'resolved')
            self.assertEqual(events['getdents64']['paths'][0]['path'], '/tmp')
            self.assertEqual(events['readlinkat']['paths'][0]['path'], '/tmp/link')
            self.assertEqual(events['readlinkat']['linkTarget'], '/tmp/file')
            self.assertNotIn('linkTarget', events['readlinkat']['paths'][0])
            self.assertEqual(events['readlink']['paths'][0]['path'], '/tmp/legacy-link')
            self.assertEqual(events['readlink']['linkTarget'], '/tmp/legacy-target')
            self.assertEqual(events['readlink']['linkTargetLength'], 18)
            self.assertEqual(events['faccessat2']['outcome'], 'error')
            self.assertEqual(events['faccessat2']['errno'], 'EACCES')
            self.assertEqual(events['execve']['errno'], 'ENOENT')
            self.assertEqual(events['execveat']['outcome'], 'success')

    def test_relative_paths_use_tracked_cwd_or_dirfd_annotation_else_remain_unresolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.21'
            trace.write_text('\n'.join([
                'chdir("/opt/app") = 0',
                'openat(AT_FDCWD, "cwd.js", O_RDONLY) = 3</opt/app/cwd.js>',
                'openat(7</srv/data>, "annotated.js", O_RDONLY) = 4</srv/data/annotated.js>',
                'openat(8, "unknown.js", O_RDONLY) = 5',
                'chdir("subdir") = 0',
                'stat("nested", {}) = 0',
            ]) + '\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json')
            paths = [event['paths'][0] for event in result['events'] if event['paths']]
            self.assertEqual(paths[0]['path'], '/opt/app/cwd.js')
            self.assertEqual(paths[0]['resolution'], 'resolved')
            self.assertEqual(paths[1]['path'], '/srv/data/annotated.js')
            self.assertEqual(paths[1]['resolution'], 'resolved')
            self.assertEqual(paths[2]['resolution'], 'unresolved')
            self.assertIsNone(paths[2]['path'])
            self.assertEqual(paths[3]['path'], '/opt/app/subdir/nested')

    def test_initial_cwd_seeds_relative_paths_for_selected_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.80'
            trace.write_text(
                f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web"], 0) = 0\n'
                'openat(AT_FDCWD, "relative.cfg", O_RDONLY) = 3\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json',
                                     '--root-pid', '80', '--initial-cwd', str(ROOT))
            event = next(event for event in result['events'] if event['syscall'] == 'openat')
            self.assertEqual(event['paths'][0]['path'], str(ROOT / 'relative.cfg'))
            self.assertEqual(event['paths'][0]['resolution'], 'resolved')
            self.assertEqual(result['relativePathObservations'], {'resolved': 1, 'unresolved': 0})
            self.assertEqual(result['initialWorkingDirectory'], str(ROOT))
            reasons = [reason for state in result['fdStateUncertaintyObservations'] for reason in state['reasons']]
            self.assertFalse(any('cwd' in reason for reason in reasons))

    def test_user_space_loader_calls_are_not_misreported_as_syscalls(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.22'
            trace.write_text('dlopen("libnative.so", RTLD_NOW) -> handle\n'
                             'realpath("../module", "/opt/module")\n'
                             'openat(AT_FDCWD, "/tmp/dlopen(file)", O_RDONLY) = 3\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json')
            self.assertEqual([event['syscall'] for event in result['events']], ['openat'])
            self.assertEqual([record['recordType'] for record in result['userSpaceLoaderRecords']],
                             ['user_space_loader', 'user_space_path_resolution'])
            self.assertFalse(any(event['syscall'] in {'dlopen', 'realpath'} for event in result['events']))

    def test_unrecognized_and_truncated_records_are_explicitly_incomplete(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.23'
            trace.write_text('openat(AT_FDCWD, "unfinished", O_RDONLY <unfinished ...>\n'
                             '<... readlinkat resumed>AT_FDCWD, "link", 4096) = ? ERESTARTSYS\n'
                             'strace decoder emitted an unfamiliar line\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json')
            self.assertFalse(result['observationsComplete'])
            self.assertCountEqual([item['recordType'] for item in result['incompleteObservations']],
                                  ['unmatched_unfinished_syscall', 'unmatched_resumed_syscall', 'unrecognized_record'])
            self.assertTrue(all(item['outcome'] == 'unknown' for item in result['incompleteObservations']))

    def test_pairs_successful_unfinished_and_resumed_syscall(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.41'
            trace.write_text('[pid 41] openat(AT_FDCWD, "joined.js", O_RDONLY <unfinished ...>\n'
                             '[pid 41] <... openat resumed>) = 7</opt/app/joined.js>\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json')
            self.assertEqual(len(result['events']), 1)
            self.assertEqual(result['events'][0]['syscall'], 'openat')
            self.assertEqual(result['events'][0]['outcome'], 'success')
            self.assertEqual(result['events'][0]['paths'][0]['path'], '/opt/app/joined.js')
            self.assertEqual(result['recordCounts']['unmatchedOrMalformedTraceRecords'], 0)
            self.assertTrue(result['observationCompleteness']['traceRecordStreamParsed'])

    def test_tracks_fd_flags_inheritance_and_uncertainty(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.51'
            trace.write_text('\n'.join([
                'openat(AT_FDCWD, "/tmp/a", O_RDONLY|O_CLOEXEC) = 3</tmp/a>',
                'fcntl(3, F_SETFD, 0) = 0',
                'dup3(3, 4, O_CLOEXEC) = 4</tmp/a>',
                'fcntl(4, F_SETFD, FD_CLOEXEC) = 0',
                'openat(AT_FDCWD, "/tmp/c", O_RDONLY) = 5</tmp/c>',
                'close_range(5, 5, CLOSE_RANGE_CLOEXEC) = 0',
                'clone(flags=SIGCHLD) = 52',
                'close_range(3, 4, 0) = 0',
                'fork() = 53',
            ]) + '\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json')
            clone, fork = [event for event in result['events'] if event['syscall'] in {'clone', 'fork'}]
            self.assertEqual(clone['inheritedFds'], [
                {'fd': '3', 'path': '/tmp/a', 'closeOnExec': False},
                {'fd': '4', 'path': '/tmp/a', 'closeOnExec': True},
                {'fd': '5', 'path': '/tmp/c', 'closeOnExec': True},
            ])
            self.assertTrue(clone['fdGraphUncertain'])
            self.assertEqual(fork['inheritedFds'], [{'fd': '5', 'path': '/tmp/c', 'closeOnExec': True}])
            self.assertFalse(result['observationCompleteness']['fdGraphComplete'])
            self.assertTrue(result['fdStateUncertaintyObservations'])
            self.assertFalse(result['completeAndroidGraph'])

    def test_tracks_chdir_fchdir_open_dup_and_close_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.54'
            trace.write_text('\n'.join([
                'chdir("/opt/app") = 0',
                'openat(AT_FDCWD, "sub", O_RDONLY|O_DIRECTORY) = 3</opt/app/sub>',
                'fchdir(3) = 0',
                'openat(AT_FDCWD, "file.js", O_RDONLY) = 4</opt/app/sub/file.js>',
                'dup(3) = 5</opt/app/sub>',
                'dup2(5, 6) = 6</opt/app/sub>',
                'close(5) = 0',
                'openat2(6, "next.js", {flags=O_RDONLY}, 24) = 7</opt/app/sub/next.js>',
                'close(6) = 0',
            ]) + '\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json')
            events = [event for event in result['events'] if event['syscall'] in {'openat', 'openat2'}]
            self.assertEqual(events[1]['paths'][0]['path'], '/opt/app/sub/file.js')
            self.assertEqual(events[2]['paths'][0]['path'], '/opt/app/sub/next.js')
            self.assertEqual(events[2]['descriptors'][0]['trackedPath'], '/opt/app/sub')

    def test_module_trace_filters_by_separate_root_and_parent_pid_and_reports_bad_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'trace.10').write_text(
                f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web"], 0) = 0\n')
            module = directory / 'modules.jsonl'
            module.write_text('\n'.join([
                json.dumps({'schemaVersion': 1, 'pid': 900, 'kind': 'resolve', 'specifier': 'pkg',
                            'parentURL': None, 'format': None}),
                json.dumps({'schemaVersion': 1, 'pid': 901, 'parentPid': 900, 'kind': 'dlopen', 'filename': '/tmp/addon.node'}),
                json.dumps({'schemaVersion': 1, 'pid': 902, 'parentPid': 999, 'kind': 'realpath', 'path': '/elsewhere'}),
                '{not json',
                json.dumps({'schemaVersion': 1, 'pid': 900, 'kind': 'unknown-kind'}),
            ]) + '\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json',
                                     '--root-pid', '10', '--module-trace', str(module), '--module-root-pid', '900')
            module_records = result['userSpaceLoaderRecords']
            self.assertEqual({item['pid'] for item in module_records}, {900, 901})
            self.assertEqual({item['recordType'] for item in module_records}, {'module_trace_resolve', 'module_trace_dlopen'})
            self.assertEqual(result['recordCounts']['recognizedModuleRecords'], 2)
            self.assertEqual(result['recordCounts']['malformedModuleRecords'], 2)
            self.assertEqual(sum(item['recordType'] == 'malformed_module_trace_json' for item in result['incompleteObservations']), 1)

    def test_module_root_pid_must_exist_in_module_stream(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            trace = directory / 'trace.1'
            trace.write_text('open("/tmp/a", O_RDONLY) = 3\n')
            module = directory / 'modules.jsonl'
            module.write_text(json.dumps({'schemaVersion': 1, 'pid': 2, 'kind': 'resolve'}) + '\n')
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--module-trace', str(module), '--module-root-pid', '99', '--output', str(directory / 'out.json')]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_discover_root_uses_exact_argv_and_keeps_descendants_not_decoy(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'trace.60').write_text(
                'execve("/node", ["/node", "vitest", "--profile", "web"], 0) = 0\n'
                f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web"], 0) = 0\n'
                'clone(flags=0) = 61\n')
            (directory / 'trace.61').write_text('open("/tmp/child", O_RDONLY) = 3\n')
            (directory / 'trace.62').write_text(f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "runner"], 0) = 0\n')
            result = self.run_report(directory / 'trace.*', directory / 'result.json', '--discover-root')
            self.assertEqual(result['selectedRootPid'], 60)
            self.assertEqual(result['traceFiles'], 2)
            self.assertEqual({event['pid'] for event in result['events']}, {60, 61})

    def test_discover_root_rejects_zero_or_multiple_candidates_and_missing_descendant(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            decoy = 'execve("/node", ["/node", "runner.js", "--profile", "web"], 0) = 0\n'
            (directory / 'trace.70').write_text(decoy)
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--discover-root', '--output', str(directory / 'out.json')]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            exact = f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web"], 0) = 0\n'
            (directory / 'trace.70').write_text(exact + 'fork() = 71\n')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            (directory / 'trace.71').write_text('exit_group(0) = ?\n')
            (directory / 'trace.72').write_text(exact)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_isolates_web_process_and_all_fork_clone_descendant_traces(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'trace.10').write_text(
                f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web"], 0) = 0\n'
                f'openat(AT_FDCWD, "{ROOT}/app.js", O_RDONLY) = 3\n'
                'clone(flags=0) = 11\n')
            (directory / 'trace.11').write_text(
                f'openat(AT_FDCWD, "{ROOT}/child.js", O_RDONLY) = 3\n'
                'fork() = 13\n')
            (directory / 'trace.13').write_text('vfork() = -1 EAGAIN (Resource temporarily unavailable)\n')
            (directory / 'trace.12').write_text(f'openat(AT_FDCWD, "{ROOT}/runner.js", O_RDONLY) = 3\n')
            output = directory / 'result.json'
            result = self.run_report(directory / 'trace.*', output, '--root-pid', '10')
            self.assertEqual(result['traceFiles'], 3)
            self.assertEqual(result['distinctSuccessfulAbsoluteCheckoutPaths'], 2)
            self.assertFalse(result['runnerAndProfileNotSeparated'])
            self.assertEqual({event['pid'] for event in result['events']}, {10, 11, 13})
            parent_events = [event for event in result['events'] if event['category'] == 'process']
            self.assertEqual([event['childPid'] for event in parent_events if 'childPid' in event], [11, 13])
            (directory / 'trace.13').unlink()
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--root-pid', '10', '--output', str(output)]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_overlay_must_be_present_in_root_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            overlay = ROOT / 'apps/android/tests/fixtures/web-host-bounded.patch.yml'
            trace = directory / 'trace.10'
            trace.write_text(
                f'execve("/node", ["/node", "{ROOT}/apps/cli/lib/bin.js", "--profile", "web", "--patch", "{overlay}"], 0) = 0\n'
                f'openat(AT_FDCWD, "{ROOT}/app.js", O_RDONLY) = 3\n')
            output = directory / 'result.json'
            result = self.run_report(directory / 'trace.*', output, '--root-pid', '10', '--overlay', str(overlay))
            self.assertEqual(result['qualificationOverlay']['path'], overlay.relative_to(ROOT).as_posix())
            trace.write_text(trace.read_text().replace(str(overlay), '/other.patch.yml'))
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--root-pid', '10', '--overlay', str(overlay), '--output', str(output)]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_rejects_root_that_is_not_original_web_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'trace.10').write_text('execve("/node", ["node", "runner.js"], 0) = 0\n')
            command = [sys.executable, str(SCRIPT), '--trace-glob', str(directory / 'trace.*'),
                       '--root-pid', '10', '--output', str(directory / 'result.json')]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_missing_trace_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            process = subprocess.run([sys.executable, str(SCRIPT), '--trace-glob', str(Path(temporary) / 'missing.*'),
                                      '--output', str(Path(temporary) / 'out.json')], capture_output=True)
            self.assertNotEqual(process.returncode, 0)


if __name__ == '__main__':
    unittest.main()
