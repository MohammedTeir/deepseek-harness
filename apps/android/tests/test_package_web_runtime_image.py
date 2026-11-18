import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import package_web_runtime_image as image


class WebRuntimeImageTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        project = root / 'repo'
        stage = root / 'production'
        carrier = root / 'carrier'
        for path in [project / 'apps/web/dist', stage / 'lib', stage / 'node_modules/.pnpm',
                     stage / 'node_modules/@deepseek-ai', carrier]:
            path.mkdir(parents=True, exist_ok=True)
        (project / 'LICENSE').write_text('Project MIT license\n')
        (project / 'THIRD_PARTY_NOTICES.md').write_text('Third-party notices\n')
        (project / 'apps/web/dist/index.html').write_text('<html><script src="/assets/app.js"></script></html>\n')
        (project / 'apps/web/dist/assets').mkdir()
        (project / 'apps/web/dist/assets/app.js').write_text('window.app = true;\n')
        (carrier / 'index.cjs').write_text("'use strict';\nmodule.exports = {};\n")
        (carrier / 'package.json').write_text(json.dumps({'name': 'node-addon-require-builtin-android-arm64', 'version': '1.0.0'}))
        (stage / 'package.json').write_text(json.dumps({'name': '@deepseek-ai/dsh', 'version': '1.0.0', 'license': 'MIT'}))
        (stage / 'LICENSE').write_text('CLI package license\n')
        (stage / 'lib/cli.js').write_text('console.log("runtime");\n')
        (stage / 'lib/cli.js.map').write_text('{}')
        (stage / 'lib/libfixture.a').write_bytes(b'!<arch>\nfixture archive payload')
        (stage / 'apps/android/tests').mkdir(parents=True)
        (stage / 'apps/android/tests/web-host.spec.mjs').write_text('test fixture')
        (stage / 'node_modules/.modules.yaml').write_text('nodeLinker: isolated\n')
        (stage / 'node_modules/.pnpm/lock.yaml').write_text('lockfileVersion: 9\n')
        (stage / 'node_modules/.pnpm-workspace-state-v1.json').write_text(str(project))
        (stage / 'node_modules/.bin').mkdir()
        (stage / 'node_modules/.bin/vitest').write_text('#!/bin/sh\n')
        package_root = stage / 'node_modules/.pnpm/dsh-web-app@1/node_modules/@deepseek-ai/dsh-web-app'
        package_root.mkdir(parents=True)
        (package_root / 'package.json').write_text(json.dumps({'name': '@deepseek-ai/dsh-web-app', 'version': '1.0.0', 'license': 'MIT'}))
        (package_root / 'LICENSE').write_text('Web package MIT license\n')
        (package_root / 'lib').mkdir()
        (package_root / 'lib/index.js').write_text('module.exports = {};\n')
        link = stage / 'node_modules/@deepseek-ai/dsh-web-app'
        link.symlink_to(os.path.relpath(package_root, link.parent), target_is_directory=True)
        frontend_root = stage / 'node_modules/.pnpm/dsh-web-frontend@1/node_modules/@deepseek-ai/dsh-web-frontend'
        (frontend_root / 'dist/assets').mkdir(parents=True)
        (frontend_root / 'package.json').write_text(json.dumps({'name': '@deepseek-ai/dsh-web-frontend', 'version': '1.0.0', 'license': 'MIT'}))
        (frontend_root / 'LICENSE').write_text('Frontend package MIT license\n')
        (frontend_root / 'dist/index.html').write_text('<html><script src="./assets/app.js"></script></html>\n')
        (frontend_root / 'dist/assets/app.js').write_text('window.frontend = true;\n')
        frontend_link = package_root / 'node_modules/@deepseek-ai/dsh-web-frontend'
        frontend_link.parent.mkdir(parents=True, exist_ok=True)
        frontend_link.symlink_to(os.path.relpath(frontend_root, frontend_link.parent), target_is_directory=True)
        native = package_root / 'lib/native.node'
        native.write_bytes(b'\x7fELF\x02\x01\x01\x00' + b'fixture native payload')
        native_link = stage / 'node_modules/native-carrier.node'
        native_link.symlink_to(os.path.relpath(native, native_link.parent))
        assets = [
            {'path': 'apps/web/dist/index.html', 'sha256': hashlib.sha256((project / 'apps/web/dist/index.html').read_bytes()).hexdigest()},
            {'path': 'apps/web/dist/assets/app.js', 'sha256': hashlib.sha256((project / 'apps/web/dist/assets/app.js').read_bytes()).hexdigest()},
        ]
        return project, stage, carrier, assets, package_root

    def test_workspace_path_normalization_is_stable(self):
        root = Path('/tmp/worktrees/dsh-feature')
        encoded = image.workspace_store_token(root)
        text = f'@deepseek-ai+package@{encoded}+packages+package'
        self.assertNotIn(encoded, image.normalize_workspace_text(text, root))
        self.assertIn('file++++WORKSPACE+packages+package', image.normalize_workspace_text(text, root))

    def test_generated_region_path_comment_normalization_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'repo'
            root.mkdir()
            annotation = b'//#region \\0dsh-devtools:css:' + root.as_posix().encode() + b'/node_modules/pkg/style.css\n'
            normalized, rules = image.normalize_workspace_comment_annotations(annotation, root)
            self.assertNotIn(root.as_posix().encode(), normalized)
            self.assertIn(b'<WORKSPACE>/node_modules/pkg/style.css', normalized)
            self.assertEqual(rules, ['absolute-checkout-prefix'])
            with self.assertRaisesRegex(ValueError, 'outside a generated JavaScript region comment'):
                image.normalize_workspace_comment_annotations(b'const p = "' + root.as_posix().encode() + b'";\n', root)

    def test_collection_records_generated_path_comment_normalization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, stage, carrier, assets, _ = self.make_fixture(root)
            bundle = stage / 'lib/generated-devtools-chunk.js'
            bundle.write_bytes(b'//#region \\0dsh-devtools:css:' + project.as_posix().encode() + b'/node_modules/pkg/style.css\nconsole.log("ok");\n')
            files, _, _, _, metadata = image.collect_image_items(stage, assets, carrier, project)
            packaged = files['runtime/lib/generated-devtools-chunk.js'].read_bytes()
            self.assertNotIn(project.as_posix().encode(), packaged)
            self.assertIn(b'<WORKSPACE>/node_modules/pkg/style.css', packaged)
            self.assertEqual(metadata['contentPathNormalizations'][0]['imagePath'], 'runtime/lib/generated-devtools-chunk.js')
            self.assertNotEqual(metadata['contentPathNormalizations'][0]['sourceSha256'], metadata['contentPathNormalizations'][0]['normalizedSha256'])

    def test_native_magic_and_forbidden_paths(self):
        self.assertEqual(image.native_format('x.node', b'\x7fELF\x02\x01'), 'ELF')
        self.assertEqual(image.native_format('x.exe', b'MZ\x00'), 'PE/MZ')
        self.assertEqual(image.native_format('libfixture.a', b'!<arch>\n'), 'native-suffix:.a')
        self.assertIsNone(image.native_format('model.wasm', b'\x00asm\x01'))
        self.assertEqual(image.exclusion_reason('apps/android/tests/web.spec.mjs'), 'test-fixture-or-test-runner')
        self.assertEqual(image.exclusion_reason('scripts/web_profile_module_observer.mjs'), 'test-fixture-or-test-runner')
        self.assertEqual(image.exclusion_reason('src/index.js.map'), 'source-map')
        self.assertEqual(image.exclusion_reason('config/.npmrc'), 'credential-or-local-config')

    def test_production_package_deny_list(self):
        report = {'dependencyRoles': {'testAndBuildToolNamesAbsentFromProductionTrees': ['vitest', '@tool/test-runner']}}
        packages = [{'name': '@deepseek-ai/dsh'}, {'name': 'vitest'}, {'name': 'commander'}]
        self.assertEqual(image.forbidden_runtime_package_names(packages, report), ['vitest'])

    def test_workspace_dependency_url_normalization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / 'repo'
            source_package = project / 'packages/demo'
            stage = root / 'stage'
            installed_package = stage / 'node_modules/@deepseek-ai/demo'
            source_package.mkdir(parents=True)
            installed_package.mkdir(parents=True)
            source_manifest = {'name': '@deepseek-ai/demo', 'version': '1.2.3'}
            (source_package / 'package.json').write_text(json.dumps(source_manifest))
            (installed_package / 'package.json').write_text(json.dumps(source_manifest))
            root_manifest = {
                'name': '@deepseek-ai/dsh', 'version': '0.1.0',
                'dependencies': {
                    '@deepseek-ai/demo': f"@deepseek-ai/demo@file://{source_package.as_posix()}",
                    'commander': '^15.0.0',
                },
            }
            (stage / 'package.json').write_text(json.dumps(root_manifest))
            self.assertIn(str(project), (stage / 'package.json').read_text())
            changes = image.normalize_workspace_dependency_specs(stage, project)
            updated = json.loads((stage / 'package.json').read_text())
            self.assertEqual(updated['dependencies']['@deepseek-ai/demo'], '1.2.3')
            self.assertEqual(updated['dependencies']['commander'], '^15.0.0')
            self.assertNotIn(str(project), (stage / 'package.json').read_text())
            self.assertEqual(changes[0]['sourcePackagePath'], 'packages/demo')
            self.assertEqual(changes[0]['normalizedVersion'], '1.2.3')

            outside = root / 'outside/demo'
            outside.mkdir(parents=True)
            (outside / 'package.json').write_text(json.dumps(source_manifest))
            root_manifest['dependencies']['@deepseek-ai/demo'] = f"@deepseek-ai/demo@file://{outside.as_posix()}"
            (stage / 'package.json').write_text(json.dumps(root_manifest))
            with self.assertRaisesRegex(ValueError, 'outside the pinned source root'):
                image.normalize_workspace_dependency_specs(stage, project)

    def test_independent_build_report_comparison(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = {
                'task': 'P3A-006', 'artifact': {'path': 'first.zip', 'sha256': 'a' * 64, 'bytes': 10, 'manifestSha256': 'b' * 64},
                'source': {'revision': 'rev', 'inputSha256': {'pnpm-lock.yaml': 'c' * 64}},
                'manifest': {'files': {'runtime/a.js': 'd' * 64}, 'links': {}, 'licenseManifest': {'packageCount': 1}},
                'negativeAssertions': {'deterministicSecondBuildPending': True},
            }
            second = json.loads(json.dumps(first))
            second['artifact']['path'] = 'second.zip'
            (root / 'first.json').write_text(json.dumps(first))
            (root / 'second.json').write_text(json.dumps(second))
            result = image.compare_build_reports(root / 'first.json', root / 'second.json', root / 'combined.json')
            combined = json.loads((root / 'combined.json').read_text())
            self.assertEqual(result['status'], 'reproducibility-verified-host-only')
            self.assertTrue(all(result['checks'].values()))
            self.assertTrue(combined['negativeAssertions']['deterministicSecondBuildVerified'])
            second['artifact']['sha256'] = 'e' * 64
            (root / 'second.json').write_text(json.dumps(second))
            with self.assertRaisesRegex(ValueError, 'builds differ'):
                image.compare_build_reports(root / 'first.json', root / 'second.json', root / 'bad.json')

    def test_collect_filter_license_and_deterministic_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, stage, carrier, assets, package_root = self.make_fixture(root)
            files, links, exclusions, native, metadata = image.collect_image_items(stage, assets, carrier, project)
            self.assertIn('runtime/lib/cli.js', files)
            self.assertIn('web/index.html', files)
            self.assertIn('web/assets/app.js', files)
            self.assertIn('runtime/node_modules/node-addon-require-builtin-android-arm64/index.cjs', files)
            self.assertNotIn('runtime/lib/cli.js.map', files)
            self.assertNotIn('runtime/lib/libfixture.a', files)
            self.assertNotIn('runtime/apps/android/tests/web-host.spec.mjs', files)
            self.assertNotIn('runtime/node_modules/.modules.yaml', files)
            self.assertNotIn('runtime/node_modules/.pnpm-workspace-state-v1.json', files)
            self.assertNotIn('runtime/node_modules/.bin/vitest', files)
            self.assertNotIn('runtime/node_modules/native-carrier.node', links)
            self.assertEqual(len(native), 3)
            self.assertTrue(any(item['path'] == 'runtime/lib/libfixture.a' and item['format'] == 'native-suffix:.a' for item in native))
            self.assertIn('runtime/node_modules/@deepseek-ai/dsh-web-app', links)
            self.assertTrue(any('/node_modules/@deepseek-ai/dsh-web-app/node_modules/@deepseek-ai/dsh-web-frontend' in name for name in links))
            self.assertTrue(any(name.endswith('/node_modules/@deepseek-ai/dsh-web-frontend/dist/index.html') for name in files))
            self.assertIn('@deepseek-ai/dsh@1.0.0', [item['identity'] for item in metadata['packages']])
            self.assertIn('@deepseek-ai/dsh-web-app@1.0.0', [item['identity'] for item in metadata['packages']])
            self.assertIn('@deepseek-ai/dsh-web-frontend@1.0.0', [item['identity'] for item in metadata['packages']])
            self.assertEqual(metadata['packageManifestCount'], 3)
            self.assertGreaterEqual(metadata['licenseManifest']['packagesWithLicenseFiles'], 3)
            self.assertTrue(any(item['reason'] == 'source-map' for item in exclusions))
            self.assertTrue(any(item['reason'] == 'test-fixture-or-test-runner' for item in exclusions))
            file_hashes = {name: image.sha256_file(path) for name, path in files.items()}
            manifest = {
                'schemaVersion': 1,
                'files': file_hashes,
                'fileBytes': {name: path.stat().st_size for name, path in files.items()},
                'fileModes': {name: path.stat().st_mode & 0o777 for name, path in files.items()},
                'links': links,
                'packages': metadata['packages'],
                'licenseManifest': metadata['licenseManifest'],
                'nativePolicySha256': image.policy_sha256(),
                'nativeArtifacts': [],
            }
            archive_a = root / 'a.zip'
            archive_b = root / 'b.zip'
            image.write_deterministic_archive(archive_a, files, links, manifest)
            image.write_deterministic_archive(archive_b, files, links, manifest)
            self.assertEqual(image.sha256_file(archive_a), image.sha256_file(archive_b))
            image.validate_image_archive(archive_a, manifest)
            self.assertNotIn(str(project).encode(), archive_a.read_bytes())

    def test_frontend_asset_hash_drift_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, stage, carrier, assets, _ = self.make_fixture(root)
            (project / 'apps/web/dist/index.html').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'hash changed'):
                image.collect_image_items(stage, assets, carrier, project)

    def test_broken_or_escaping_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, stage, carrier, assets, _ = self.make_fixture(root)
            broken = stage / 'node_modules/broken-link'
            broken.symlink_to('missing-target')
            with self.assertRaisesRegex(ValueError, 'Broken or escaping'):
                image.collect_image_items(stage, assets, carrier, project)

    def test_license_or_native_policy_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, stage, carrier, assets, _ = self.make_fixture(root)
            files, links, _, _, metadata = image.collect_image_items(stage, assets, carrier, project)
            file_hashes = {name: image.sha256_file(path) for name, path in files.items()}
            manifest = {
                'files': file_hashes,
                'fileBytes': {name: path.stat().st_size for name, path in files.items()},
                'fileModes': {name: path.stat().st_mode & 0o777 for name, path in files.items()},
                'links': links,
                'packages': metadata['packages'],
                'licenseManifest': metadata['licenseManifest'],
                'nativePolicySha256': '0' * 64,
                'nativeArtifacts': [],
            }
            archive = root / 'mismatch.zip'
            image.write_deterministic_archive(archive, files, links, manifest)
            with self.assertRaisesRegex(ValueError, 'policy digest mismatch'):
                image.validate_image_archive(archive, manifest)


if __name__ == '__main__':
    unittest.main(verbosity=2)
