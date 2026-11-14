"""Regression tests for the P3A-004 native artifact policy classifier."""
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))

import audit_web_native_artifacts as audit  # noqa: E402


class NativeArtifactPolicyTests(unittest.TestCase):
    def test_native_suffixes_include_versioned_shared_libraries(self):
        self.assertTrue(audit.is_native_filename(Path('libvips.so.8.18.7')))
        self.assertTrue(audit.is_native_filename(Path('binding.node')))
        self.assertFalse(audit.is_native_filename(Path('bundle.js')))

    def test_platform_tags_normalize_common_android_port_targets(self):
        tags = audit.platform_tags('pkg/prebuilds/linux-arm64-gnu/addon.node')
        self.assertIn('linux', tags)
        self.assertIn('arm64', tags)

    def test_linux_glibc_elf_is_rejected_even_on_aarch64(self):
        elf = {
            'machine': 'AArch64',
            'neededLibraries': ['libc.so.6', 'ld-linux-aarch64.so.1'],
            'versionRequirements': ['GLIBC_2.17'],
            'minimumAndroidApiNote': None,
        }
        self.assertEqual(
            audit.android_decision('ELF 64-bit Linux shared object', elf, ['linux-arm64']),
            'deny_linux_gnu_glibc',
        )

    def test_other_desktop_formats_are_not_android_payloads(self):
        self.assertEqual(
            audit.android_decision('Mach-O 64-bit arm64 dynamically linked', None, ['darwin-arm64']),
            'deny_non_android_platform_or_archive; no Android build provenance',
        )
        self.assertEqual(
            audit.android_decision('PE32+ executable (DLL) Aarch64', None, ['win32-arm64']),
            'deny_non_android_platform_or_archive; no Android build provenance',
        )

    def test_android_arm64_elf_still_needs_closure_validation(self):
        elf = {
            'machine': 'AArch64',
            'neededLibraries': ['libc.so', 'libnode.so'],
            'versionRequirements': [],
            'minimumAndroidApiNote': 29,
        }
        self.assertEqual(
            audit.android_decision('ELF 64-bit LSB shared object', elf, []),
            'candidate_only_requires_dependency_closure_and_device_validation',
        )

    def test_android_elf_without_minimum_api_evidence_is_not_approved(self):
        elf = {
            'machine': 'AArch64',
            'neededLibraries': ['libc.so', 'libnode.so'],
            'versionRequirements': [],
            'minimumAndroidApiNote': None,
        }
        self.assertEqual(
            audit.android_decision('ELF 64-bit LSB shared object', elf, []),
            'not_approved_android_provenance_or_min_api_missing',
        )

    def test_wasm_extension_is_not_treated_as_elf_native_code(self):
        self.assertEqual(
            audit.android_decision('WebAssembly (wasm) binary module', None, []),
            'not_native_elf_wasm; keep outside native ELF policy',
        )

    def test_apk_context_keeps_abi_and_minimum_sdk_at_package_scope(self):
        context = audit.apk_context({
            'checks': [{
                'command': ['aapt', 'dump', 'badging', 'app.apk'],
                'output': "sdkVersion:'29'\ntargetSdkVersion:'36'\nnative-code: 'arm64-v8a'\n",
            }],
        })
        self.assertEqual(context, {
            'minimumSdk': 29,
            'targetSdk': 36,
            'nativeCode': ['arm64-v8a'],
        })

    def test_exact_build_hash_link_is_distinguished_from_mismatch(self):
        digest = 'a' * 64
        exact = audit.build_hash_status(
            'libharness_node_pty.so', digest,
            {'nodePtyBuild': {'binarySha256': digest}},
        )
        self.assertEqual(exact['status'], 'exact_build_output_hash_match')
        mismatch = audit.build_hash_status(
            'libharness_atomic.so', digest,
            {'atomicNativeBuild': {'nativeSha256': 'b' * 64}},
        )
        self.assertEqual(mismatch['status'], 'build_record_hash_differs_from_packaged_hash')
        missing = audit.build_hash_status('libnode.so', digest, {})
        self.assertEqual(missing['status'], 'no_artifact_output_hash_in_build_record')

    def test_readelf_observation_parses_interpreter_and_page_alignment(self):
        rows = audit.readelf_observations({
            'checks': [{
                'command': ['llvm-readelf', '-h', '-l', '-W', '/tmp/libprobe.so'],
                'exitCode': 0,
                'output': (
                    'Type: DYN (Shared object file)\n'
                    'Machine: AArch64\n'
                    '[Requesting program interpreter: /system/bin/linker64]\n'
                    'LOAD 0x000000 0x0 0x0 0x10 0x10 R 0x4000\n'
                ),
            }],
        })
        self.assertEqual(len(rows['libprobe.so']), 1)
        row = rows['libprobe.so'][0]
        self.assertEqual(row['machine'], 'AArch64')
        self.assertEqual(row['interpreter'], '/system/bin/linker64')
        self.assertEqual(row['loadSegmentAlignmentsBytes'], [16384])
        self.assertFalse(row['exactPackagedHashBoundToCheck'])

    def test_historical_matrix_keeps_hash_linkage_and_test_roles_distinct(self):
        _, matrix = audit.historical_android_builds()
        by_name = {item['artifact']: item for item in matrix}
        self.assertIn('exact_build_output_hash_match', by_name['libharness_node_pty.so']['buildHashLinkStatuses'])
        self.assertIn('build_record_hash_differs_from_packaged_hash', by_name['libharness_atomic.so']['buildHashLinkStatuses'])
        self.assertIn('build_record_hash_differs_from_packaged_hash', by_name['libharness_require_builtin.so']['buildHashLinkStatuses'])
        self.assertIn('exclude', by_name['libharness_probe.so']['purposeAndWebImageDisposition'])
        self.assertEqual(by_name['libnode_executable.so']['apkLevelAbi'], ['arm64-v8a'])


if __name__ == '__main__':
    unittest.main()
