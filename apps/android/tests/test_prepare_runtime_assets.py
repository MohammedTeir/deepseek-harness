import posixpath
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from prepare_runtime_assets import validate_android_web_runtime_manifest


class AndroidWebRuntimeManifestTests(unittest.TestCase):
    def manifest(self):
        frontend = 'runtime/node_modules/.pnpm/dsh-web-frontend@1/node_modules/@deepseek-ai/dsh-web-frontend'
        web_app = 'runtime/node_modules/.pnpm/dsh-web-app@1/node_modules/@deepseek-ai/dsh-web-app'
        base = 'runtime/node_modules/.pnpm/dsh-base@1/node_modules/@deepseek-ai/dsh-base'
        provider = 'runtime/node_modules/.pnpm/dsh-web-deepseek-api@1/node_modules/@deepseek-ai/dsh-web-deepseek-api'
        frontend_link = posixpath.join(posixpath.dirname(web_app), 'dsh-web-frontend')
        provider_link = posixpath.join(posixpath.dirname(base), 'dsh-web-deepseek-api')
        return {
            'schemaVersion': 1,
            'imageKind': 'original-web-runtime-candidate',
            'nativeArtifacts': [],
            'packages': [
                {'name': '@deepseek-ai/dsh-base', 'packagePath': base},
                {'name': '@deepseek-ai/dsh-web-app', 'packagePath': web_app},
                {'name': '@deepseek-ai/dsh-web-deepseek-api', 'packagePath': provider},
            ],
            'files': {
                'runtime/lib/bin.js': '1' * 64,
                'web/index.html': '2' * 64,
                provider + '/lib/index.js': '3' * 64,
                provider + '/package.json': '8' * 64,
                base + '/package.json': '9' * 64,
                base + '/cordis.patch.yml': '4' * 64,
                web_app + '/package.json': 'a' * 64,
                web_app + '/cordis.patch.yml': '5' * 64,
                frontend + '/package.json': '6' * 64,
                frontend + '/dist/index.html': '7' * 64,
            },
            'links': {
                'runtime/node_modules/@deepseek-ai/dsh-base': '../.pnpm/base@1/node_modules/@deepseek-ai/dsh-base',
                'runtime/node_modules/@deepseek-ai/dsh-web-app': '../.pnpm/web-app@1/node_modules/@deepseek-ai/dsh-web-app',
                provider_link: posixpath.relpath(provider, posixpath.dirname(provider_link)),
                frontend_link: posixpath.relpath(frontend, posixpath.dirname(frontend_link)),
            },
        }

    def test_full_production_web_image_contract_passes(self):
        validate_android_web_runtime_manifest(self.manifest())

    def test_missing_provider_entrypoint_fails(self):
        manifest = self.manifest()
        manifest['files'].pop(next(path for path in manifest['files'] if 'dsh-web-deepseek-api/lib/index.js' in path))
        with self.assertRaisesRegex(ValueError, 'web API provider entrypoint'):
            validate_android_web_runtime_manifest(manifest)

    def test_missing_provider_dependency_link_fails(self):
        manifest = self.manifest()
        base = next(package['packagePath'] for package in manifest['packages'] if package['name'] == '@deepseek-ai/dsh-base')
        manifest['links'].pop(posixpath.join(posixpath.dirname(base), 'dsh-web-deepseek-api'))
        with self.assertRaisesRegex(ValueError, 'does not link dsh-base'):
            validate_android_web_runtime_manifest(manifest)

    def test_missing_cordis_overlay_fails(self):
        manifest = self.manifest()
        manifest['files'].pop(next(path for path in manifest['files'] if path.endswith('/dsh-web-app/cordis.patch.yml')))
        with self.assertRaisesRegex(ValueError, 'web-app Cordis overlay'):
            validate_android_web_runtime_manifest(manifest)

    def test_frontend_link_must_resolve_to_packaged_dist(self):
        manifest = self.manifest()
        link = next(path for path in manifest['links'] if path.endswith('/node_modules/@deepseek-ai/dsh-web-frontend'))
        manifest['links'][link] = '../../../missing-frontend'
        with self.assertRaisesRegex(ValueError, 'does not link dsh-web-app'):
            validate_android_web_runtime_manifest(manifest)

    def test_native_artifact_is_rejected(self):
        manifest = self.manifest()
        manifest['nativeArtifacts'] = [{'path': 'runtime/native.node'}]
        with self.assertRaisesRegex(ValueError, 'must not contain native artifacts'):
            validate_android_web_runtime_manifest(manifest)

    def test_wrong_image_kind_is_rejected(self):
        manifest = self.manifest()
        manifest['imageKind'] = 'sdk-minimal'
        with self.assertRaisesRegex(ValueError, 'original-web production runtime image'):
            validate_android_web_runtime_manifest(manifest)


if __name__ == '__main__':
    unittest.main(verbosity=2)
