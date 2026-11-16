"""P3A-003 package-role and exclusion policy tests; no Android execution is simulated."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPT_DIR))

from audit_web_runtime_test_split import (  # noqa: E402
    classify_package_name,
    classify_path,
    is_test_path,
    path_from_module_url,
    production_tree,
    resolve_dist_reference,
)


class WebRuntimeTestSplitTest(unittest.TestCase):
    def setUp(self):
        self.production = {
            'cli': {'@deepseek-ai/dsh-cli-runtime'},
            'webProfileBundle': {'@deepseek-ai/dsh-web-runtime'},
        }
        self.development = {
            'cli': {'@deepseek-ai/dsh-cli-testkit'},
            'webProfileBundle': {'@deepseek-ai/dsh-web-testkit'},
            'webFrontend': {'@deepseek-ai/dsh-client-web'},
        }

    def test_host_tests_and_vitest_configuration_are_not_runtime_inputs(self):
        for path in (
            'apps/android/tests/web-bootstrap.host.spec.mjs',
            'apps/android/tests/fixtures/web-host-bounded.patch.yml',
            'apps/cli/tests/profiles/web/tests/default-web-process.ts',
            'apps/android/tests/vitest.web-host.config.mjs',
        ):
            with self.subTest(path=path):
                self.assertTrue(is_test_path(path))
                self.assertEqual(classify_path(path, self.production, self.development), 'host_test_or_fixture')

    def test_observer_and_capture_tools_have_explicit_instrumentation_role(self):
        self.assertEqual(
            classify_path('apps/android/scripts/web_profile_module_observer.mjs', self.production, self.development),
            'trace_instrumentation',
        )
        self.assertEqual(
            classify_path('apps/android/scripts/capture_web_host_trace.py', self.production, self.development),
            'trace_instrumentation',
        )

    def test_built_frontend_assets_are_separate_from_source_maps_and_preview(self):
        self.assertEqual(
            classify_path('apps/web/dist/assets/index.js', self.production, self.development),
            'production_frontend_asset_candidate',
        )
        self.assertEqual(
            classify_path('apps/web/dist/assets/index.js.map', self.production, self.development),
            'preview_or_source_map_excluded',
        )
        self.assertEqual(
            classify_path('apps/web/dist/preview/index.html', self.production, self.development),
            'preview_or_source_map_excluded',
        )
        self.assertEqual(
            classify_path('apps/web/src/main.tsx', self.production, self.development),
            'frontend_build_source',
        )

    def test_built_cli_and_web_bundle_code_are_runtime_candidates(self):
        self.assertEqual(
            classify_path('apps/cli/lib/bin.js', self.production, self.development),
            'cli_launcher_application_code',
        )
        self.assertEqual(
            classify_path('packages/bundle/web-app/lib/index.js', self.production, self.development),
            'web_profile_bundle_application_code',
        )

    def test_manifest_package_role_prefers_production_closure(self):
        self.assertEqual(
            classify_package_name('@deepseek-ai/dsh-web-runtime', self.production, self.development),
            'web_profile_production_package_tree',
        )
        self.assertEqual(
            classify_package_name('@deepseek-ai/dsh-cli-runtime', self.production, self.development),
            'cli_launcher_production_package_tree',
        )
        self.assertEqual(
            classify_package_name('@deepseek-ai/dsh-client-web', self.production, self.development),
            'frontend_build_dependency',
        )
        self.assertEqual(
            classify_package_name('@deepseek-ai/dsh-web-testkit', self.production, self.development),
            'development_or_test_only_package',
        )

    def test_package_tree_walk_excludes_dev_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = root / 'workspace/app'
            runtime = app / 'node_modules/runtime'
            transit = runtime / 'node_modules/transitive'
            testkit = app / 'node_modules/testkit'
            for directory in (runtime, transit, testkit):
                directory.mkdir(parents=True)
            (app / 'package.json').write_text(json.dumps({
                'name': 'app',
                'dependencies': {'runtime': '1.0.0'},
                'devDependencies': {'testkit': '1.0.0'},
            }))
            (runtime / 'package.json').write_text(json.dumps({
                'name': 'runtime', 'version': '1.0.0', 'dependencies': {'transitive': '1.0.0'},
            }))
            (transit / 'package.json').write_text(json.dumps({'name': 'transitive', 'version': '1.0.0'}))
            (testkit / 'package.json').write_text(json.dumps({'name': 'testkit', 'version': '1.0.0'}))

            report, names = production_tree('fixture', app / 'package.json', root)

            self.assertEqual(names, {'runtime', 'transitive'})
            self.assertEqual(report['uniquePackageIdentityCount'], 2)
            self.assertNotIn('testkit@1.0.0', report['packageIdentities'])

    def test_frontend_asset_reference_rejects_escape_and_keeps_local_path(self):
        self.assertEqual(resolve_dist_reference('./assets/app.js'), 'apps/web/dist/assets/app.js')
        with self.assertRaisesRegex(ValueError, 'escapes dist'):
            resolve_dist_reference('../../outside.js')

    def test_module_url_reader_keeps_preload_temp_observer_evidence(self):
        self.assertEqual(
            path_from_module_url('/tmp/dsh-web-default-isolation-abc/fixtures/runtime-roster-observer.js'),
            '/tmp/dsh-web-default-isolation-abc/fixtures/runtime-roster-observer.js',
        )
        self.assertEqual(
            path_from_module_url('file:///tmp/observer%20module.mjs'),
            '/tmp/observer module.mjs',
        )
        self.assertIsNone(path_from_module_url('node:fs'))


if __name__ == '__main__':
    unittest.main()
