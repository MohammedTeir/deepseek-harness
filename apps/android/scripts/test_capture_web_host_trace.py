import gzip
import json
from pathlib import Path
import tempfile
import unittest

from apps.android.scripts.capture_web_host_trace import (
    BOUNDED_DISABLED_PROVIDER_ROWS,
    TRACE_SET,
    compact_report,
    coverage_blind_spots,
    summarize_link_targets,
    summarize_path_operations,
    summarize_realpath_records,
    write_path_inventory,
)


class CaptureSummaryTests(unittest.TestCase):
    def test_path_operations_preserve_outcomes_flags_and_raw_evidence_references(self):
        events = [
            {
                'pid': 120,
                'traceFile': 'bootstrap.syscall.trace.120',
                'line': 10,
                'syscall': 'openat',
                'category': 'open',
                'outcome': 'success',
                'arguments': ['AT_FDCWD', '"/checkout/config.yml"', 'O_RDONLY|O_CLOEXEC'],
                'paths': [{
                    'decodedPath': '/checkout/config.yml',
                    'path': '/checkout/config.yml',
                    'resolution': 'absolute',
                }],
            },
            {
                'pid': 120,
                'traceFile': 'bootstrap.syscall.trace.120',
                'line': 14,
                'syscall': 'openat',
                'category': 'open',
                'outcome': 'success',
                'arguments': ['AT_FDCWD', '"/checkout/config.yml"', 'O_RDONLY|O_CLOEXEC'],
                'paths': [{
                    'decodedPath': '/checkout/config.yml',
                    'path': '/checkout/config.yml',
                    'resolution': 'absolute',
                }],
            },
            {
                'pid': 121,
                'traceFile': 'bootstrap.syscall.trace.121',
                'line': 22,
                'syscall': 'openat',
                'category': 'open',
                'outcome': 'error',
                'errno': 'ENOENT',
                'arguments': ['AT_FDCWD', '"/checkout/config.yml"', 'O_RDONLY|O_CLOEXEC'],
                'paths': [{
                    'decodedPath': '/checkout/config.yml',
                    'path': '/checkout/config.yml',
                    'resolution': 'absolute',
                }],
            },
            {
                'pid': 121,
                'traceFile': 'bootstrap.syscall.trace.121',
                'line': 30,
                'syscall': 'newfstatat',
                'category': 'metadata',
                'outcome': 'success',
                'arguments': ['AT_FDCWD', '"relative/missing.json"', '0'],
                'paths': [{
                    'decodedPath': 'relative/missing.json',
                    'path': None,
                    'resolution': 'unresolved',
                }],
            },
        ]

        summary = summarize_path_operations(events)
        successful_open = next(
            item for item in summary['operations']
            if item['syscall'] == 'openat' and item['outcome'] == 'success'
        )
        failed_open = next(
            item for item in summary['operations']
            if item['syscall'] == 'openat' and item['outcome'] == 'error'
        )
        unresolved = next(item for item in summary['operations'] if item['resolution'] == 'unresolved')

        self.assertEqual(summary['uniqueObservedPathCount'], 2)
        self.assertEqual(successful_open['observationCount'], 2)
        self.assertEqual(successful_open['evidenceReferenceCount'], 2)
        self.assertEqual(len(successful_open['evidenceExamples']), 2)
        self.assertEqual(successful_open['openFlags'], 'O_RDONLY|O_CLOEXEC')
        self.assertEqual(failed_open['errno'], 'ENOENT')
        self.assertEqual(failed_open['outcome'], 'error')
        self.assertEqual(unresolved['pathLiteral'], 'relative/missing.json')
        self.assertIsNone(unresolved['resolvedPath'])
        self.assertFalse(summary['contentTransferObserved'])
        self.assertIn('does not prove bytes were read', summary['interpretation'])

    def test_symlink_and_realpath_observations_remain_resolution_records(self):
        events = [{
            'pid': 130,
            'traceFile': 'bootstrap.syscall.trace.130',
            'line': 41,
            'syscall': 'readlinkat',
            'outcome': 'success',
            'linkTarget': '../lib/runtime.js',
            'paths': [{
                'decodedPath': '/checkout/current',
                'path': '/checkout/current',
                'resolution': 'absolute',
            }],
        }]
        link_targets = summarize_link_targets(events)
        self.assertEqual(len(link_targets), 1)
        self.assertEqual(link_targets[0]['linkTarget'], '../lib/runtime.js')
        self.assertEqual(link_targets[0]['observationCount'], 1)

        realpath = summarize_realpath_records([{
            'recordType': 'module_trace_realpath',
            'pid': 130,
            'line': 8,
            'path': '/checkout/current',
            'resolvedPath': '/checkout/releases/v1',
            'outcome': 'success',
        }])
        self.assertEqual(realpath[0]['resolvedPath'], '/checkout/releases/v1')
        self.assertEqual(realpath[0]['observationCount'], 1)

    def test_compact_report_does_not_promote_open_or_resolved_module_to_dependency(self):
        report = compact_report({
            'schemaVersion': 2,
            'androidExecuted': False,
            'completeAndroidGraph': False,
            'gate4Passed': False,
            'events': [{
                'pid': 140,
                'traceFile': 'bootstrap.syscall.trace.140',
                'line': 50,
                'syscall': 'openat',
                'category': 'open',
                'outcome': 'success',
                'arguments': ['AT_FDCWD', '"/checkout/module.js"', 'O_RDONLY'],
                'paths': [{
                    'decodedPath': '/checkout/module.js',
                    'path': '/checkout/module.js',
                    'resolution': 'absolute',
                }],
            }],
            'userSpaceLoaderRecords': [
                {'recordType': 'module_trace_resolve', 'resolvedURL': 'file:///checkout/module.js'},
                {'recordType': 'module_trace_resolve-failed', 'specifier': './optional.js', 'errorCode': 'ERR_MODULE_NOT_FOUND'},
                {'recordType': 'module_trace_realpath', 'path': '/checkout/link', 'resolvedPath': '/checkout/real', 'outcome': 'success', 'pid': 140, 'line': 6},
                {'recordType': 'module_trace_dlopen', 'filename': '/tmp/addon.node', 'outcome': 'success', 'pid': 140},
            ],
        })

        self.assertNotIn('events', report)
        self.assertEqual(report['dependencyAssessment']['status'], 'not_assessed')
        self.assertEqual(report['dependencyAssessment']['inferredRequiredPaths'], [])
        self.assertFalse(report['dependencyAssessment']['inferencePerformed'])
        self.assertEqual(report['observedPathOperations']['operations'][0]['syscall'], 'openat')
        self.assertFalse(report['observedPathOperations']['contentTransferObserved'])
        self.assertEqual(report['userSpaceLoaderSummary']['uniqueResolvedModuleUrls'], ['file:///checkout/module.js'])
        self.assertIn('not proof', report['userSpaceLoaderSummary']['interpretation'])
        self.assertEqual(report['userSpaceLoaderSummary']['nativeLoadEvents'][0]['outcome'], 'success')
        self.assertEqual(report['observedRealpathResolutions'][0]['resolvedPath'], '/checkout/real')
        self.assertFalse(report['androidExecuted'])
        self.assertFalse(report['completeAndroidGraph'])
        self.assertFalse(report['gate4Passed'])

    def test_path_inventory_is_compressed_and_summary_keeps_counts(self):
        report = compact_report({
            'events': [{
                'pid': 150,
                'traceFile': 'bootstrap.syscall.trace.150',
                'line': 77,
                'syscall': 'openat',
                'category': 'open',
                'outcome': 'success',
                'arguments': ['AT_FDCWD', '"/checkout/config.yml"', 'O_RDONLY'],
                'paths': [{
                    'decodedPath': '/checkout/config.yml',
                    'path': '/checkout/config.yml',
                    'resolution': 'absolute',
                }],
            }],
            'userSpaceLoaderRecords': [],
        })

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'path-inventory.json.gz'
            metadata = write_path_inventory(report, output)
            with gzip.open(output, 'rt', encoding='utf-8') as compressed:
                inventory = json.load(compressed)

        self.assertEqual(metadata['format'], 'gzip-json')
        self.assertEqual(metadata['path'], 'path-inventory.json.gz')
        self.assertGreater(metadata['uncompressedBytes'], metadata['compressedBytes'])
        self.assertEqual(metadata['pathOperationRows'], 1)
        self.assertEqual(inventory['schemaVersion'], 1)
        self.assertEqual(inventory['observedPathOperations']['operations'][0]['evidenceExamples'][0]['line'], 77)
        self.assertNotIn('operations', report['observedPathOperations'])
        self.assertTrue(report['observedPathOperations']['detailsStoredInPathObservationInventory'])
        self.assertTrue(report['observedSymlinkTargets']['detailsStoredInPathObservationInventory'])

    def test_blind_spots_name_unselected_syscall_and_path_scopes(self):
        bootstrap = coverage_blind_spots('bootstrap')
        bounded = coverage_blind_spots('bounded')
        self.assertEqual(bootstrap['syscallTraceSet'], TRACE_SET)
        classes = {entry['class']: entry['examples'] for entry in bootstrap['unobservedSyscallClasses']}
        self.assertIn('read', classes['file content transfer'])
        self.assertIn('mmap', classes['memory mapping and protection'])
        self.assertIn('socket', classes['network sockets and payloads'])
        scopes = {entry['scope']: entry for entry in bootstrap['knownUnobservedPathScopes']}
        self.assertIn('/data/user/<user>/<applicationId>/**', scopes['Android app-private runtime and data directories']['pathOrUrlPatterns'])
        self.assertEqual(len(bootstrap['knownUnobservedPathScopes']), 4)
        bounded_scope = bounded['knownUnobservedPathScopes'][-1]
        self.assertEqual(bounded_scope['providerRows'], BOUNDED_DISABLED_PROVIDER_ROWS)
        self.assertEqual([row['id'] for row in BOUNDED_DISABLED_PROVIDER_ROWS], [
            'subprocess', 'bash-sandbox', 'pwsh-sandbox', 'open-in-app', 'directory-picker', 'mcp-manager',
        ])
        self.assertIn('not an exhaustive list', bootstrap['scopeNote'])


if __name__ == '__main__':
    unittest.main()
