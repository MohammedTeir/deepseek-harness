"""Archive and observed-file rejection tests; no Android execution is simulated."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from native_artifact_policy import load_policy, policy_sha256, validate_native_artifacts
from package_profile import (REQUIRED_CORDIS_OVERLAYS, add_required_cordis_links,
                             add_required_cordis_overlays, collect, validate_archive,
                             validate_host_qualification)


class ProfileArchiveTest(unittest.TestCase):
    def archive(self, directory, name, data, *, recorded=None):
        manifest={
            'files':{name: recorded or hashlib.sha256(data).hexdigest()},
            'nativeArtifacts':[],
            'nativePolicySha256':policy_sha256(),
        }
        archive=Path(directory)/'image.zip'
        with zipfile.ZipFile(archive,'w') as zip:
            zip.writestr(name,data)
            zip.writestr('image-manifest.json',json.dumps(manifest))
        return archive,manifest

    def test_host_approval_fixture_is_not_shippable(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['command-profile-reference.mjs', 'terminal-registry-reference.mjs',
                         'terminal-registry-plugin.mjs', 'terminal-authority-plugin.mjs', 'terminal-profile-reference.mjs',
                         'web-bootstrap.host.spec.mjs', 'web-bounded-profile.host.spec.mjs',
                         'vitest.web-host.config.mjs', 'fixtures/web-host-bounded.patch.yml']:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    validate_archive(*self.archive(directory, 'apps/android/tests/' + name, b'host fixture'))

    def test_plain_interpreted_file_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            validate_archive(*self.archive(directory,'lib/index.js',b'export const value = 1;'))

    def test_changed_bytes_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'changed'):
                validate_archive(*self.archive(directory,'lib/index.js',b'changed',recorded='0'*64))

    def test_native_file_rejects_even_with_matching_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'Native'):
                validate_archive(*self.archive(directory,'lib/index.js',b'\x7fELFdata'))

    def test_traversal_and_absolute_paths_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['../outside.js','/outside.js','lib/../../outside.js','lib\\outside.js']:
                with self.subTest(name=name),self.assertRaisesRegex(ValueError,'Unsafe'):
                    validate_archive(*self.archive(directory,name,b'data'))

    def test_stale_host_qualification_cannot_approve_new_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'profile-image.zip').write_bytes(b'new image')
            (root/'profile-qualification.json').write_text(json.dumps({'imageSha256':'0'*64}))
            with self.assertRaisesRegex(ValueError,'does not match image'):
                validate_host_qualification(root)

    def test_successful_read_through_outside_symlink_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);root=base/'root';root.mkdir()
            outside=base/'outside.js';outside.write_text('data')
            alias=root/'alias.js';alias.symlink_to(outside)
            trace=base/'trace';trace.write_text(f'openat(AT_FDCWD, "{alias}", O_RDONLY) = 3\n')
            with self.assertRaises(ValueError): collect(root,[trace])

    def test_credential_read_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);secret=root/'.credentials.yaml';secret.write_text('not a real credential')
            trace=root/'trace';trace.write_text(f'openat(AT_FDCWD, "{secret}", O_RDONLY) = 3\n')
            with self.assertRaisesRegex(ValueError,'Credential'): collect(root,[trace])

    def test_required_cordis_overlays_use_canonical_files_behind_cli_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            files=set()
            for runtime_path, source_path in REQUIRED_CORDIS_OVERLAYS.items():
                source=root/source_path
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(f'# source for {source_path}\n')
            add_required_cordis_overlays(files, root)
            links={}
            add_required_cordis_links(links)
            host=root/'host'
            for name in files:
                destination=host/name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((root/name).read_bytes())
            for name,target in sorted(links.items()):
                destination=host/name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(os.path.relpath(host/target,destination.parent),target_is_directory=True)
            for alias,source in REQUIRED_CORDIS_OVERLAYS.items():
                self.assertEqual((host/alias).read_bytes(),(host/source).read_bytes())
            digests={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}
            self.assertEqual(set(digests),set(REQUIRED_CORDIS_OVERLAYS.values()))
            required={name:digests[source] for name,source in REQUIRED_CORDIS_OVERLAYS.items()}
            manifest={
                'files':digests,
                'links':links,
                'requiredCordisOverlays':required,
                'nativeArtifacts':[],
                'nativePolicySha256':policy_sha256(),
            }
            archive=Path(directory)/'profile.zip'
            with zipfile.ZipFile(archive,'w') as zip:
                for name in files: zip.write(root/name,name)
                zip.writestr('image-manifest.json',json.dumps(manifest))
            validate_archive(archive,manifest)
            bad_manifest=json.loads(json.dumps(manifest))
            bad_manifest['requiredCordisOverlays'].pop(next(iter(bad_manifest['requiredCordisOverlays'])))
            bad_archive=Path(directory)/'missing-overlay.zip'
            with zipfile.ZipFile(bad_archive,'w') as zip:
                for name in files: zip.write(root/name,name)
                zip.writestr('image-manifest.json',json.dumps(bad_manifest))
            with self.assertRaisesRegex(ValueError,'alias set'):
                validate_archive(bad_archive,bad_manifest)

    def native_record(self, **overrides):
        record={
            'path':'lib/arm64-v8a/libsample.so',
            'sha256':'a'*64,
            'soname':'libsample.so',
            'operatingSystem':'Android',
            'abi':'arm64-v8a',
            'libc':'Bionic',
            'machine':'AArch64',
            'elfClass':64,
            'elfType':'DYN',
            'minimumAndroidApi':29,
            'neededLibraries':['libc.so'],
            'artifactRole':'runtime',
            'licenseId':'MIT',
            'licenseEvidencePath':'licenses/MIT.txt',
        }
        record.update(overrides)
        return record

    def test_native_policy_defaults_to_no_approved_artifacts(self):
        policy=load_policy()
        self.assertEqual(policy['approvedArtifacts'],[])
        self.assertEqual(validate_native_artifacts([],policy,set()),[])
        with self.assertRaisesRegex(ValueError,'not on the exact-hash allowlist'):
            validate_native_artifacts([self.native_record()],policy,{'licenses/MIT.txt'})

    def test_exact_allowlisted_android_artifact_and_license_closure_pass(self):
        record=self.native_record()
        policy=load_policy()
        policy['approvedArtifacts']=[record]
        result=validate_native_artifacts([record],policy,{'licenses/MIT.txt'})
        self.assertEqual(result,[record])

    def test_same_path_with_changed_hash_is_rejected(self):
        approved=self.native_record()
        changed=self.native_record(sha256='b'*64)
        policy=load_policy()
        policy['approvedArtifacts']=[approved]
        with self.assertRaisesRegex(ValueError,'differs from its allowlist entry'):
            validate_native_artifacts([changed],policy,{'licenses/MIT.txt'})

    def test_known_desktop_prebuild_is_denied_before_allowlist(self):
        record=self.native_record(
            path='node_modules/pkg/prebuilds/linux-arm64-gnu/addon.node',
            soname='addon.so',
        )
        policy=load_policy()
        policy['approvedArtifacts']=[record]
        with self.assertRaisesRegex(ValueError,'deny pattern'):
            validate_native_artifacts([record],policy,{'licenses/MIT.txt'})

    def test_wrong_abi_test_fixture_and_missing_license_are_rejected(self):
        policy=load_policy()
        for record, expected in [
            (self.native_record(abi='x86_64'), 'ABI/machine'),
            (self.native_record(artifactRole='test-fixture'), 'role is denied'),
            (self.native_record(licenseEvidencePath='licenses/MIT.txt'), 'license evidence is absent'),
        ]:
            with self.subTest(expected=expected), self.assertRaisesRegex(ValueError,expected):
                validate_native_artifacts([record],policy,set())

    def test_non_system_dt_needed_requires_a_present_allowlisted_soname(self):
        leaf=self.native_record()
        leaf['neededLibraries']=['libnode.so']
        policy=load_policy()
        policy['approvedArtifacts']=[leaf]
        with self.assertRaisesRegex(ValueError,'Unclosed DT_NEEDED'):
            validate_native_artifacts([leaf],policy,{'licenses/MIT.txt'})

    def test_native_minimum_api_above_floor_is_rejected(self):
        record=self.native_record(minimumAndroidApi=30)
        policy=load_policy()
        with self.assertRaisesRegex(ValueError,'minimum API exceeds'):
            validate_native_artifacts([record],policy,{'licenses/MIT.txt'})

    def test_manifest_is_bound_to_native_policy_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            archive,manifest=self.archive(directory,'lib/index.js',b'export const value = 1;')
            manifest['nativePolicySha256']='0'*64
            with self.assertRaisesRegex(ValueError,'policy digest mismatch'):
                validate_archive(archive,manifest)


if __name__=='__main__': unittest.main()
