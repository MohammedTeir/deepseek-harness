"""Archive and observed-file rejection tests; no Android execution is simulated."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from package_profile import collect, validate_archive, validate_host_qualification


class ProfileArchiveTest(unittest.TestCase):
    def archive(self, directory, name, data, *, recorded=None):
        manifest={'files':{name: recorded or hashlib.sha256(data).hexdigest()}}
        archive=Path(directory)/'image.zip'
        with zipfile.ZipFile(archive,'w') as zip:
            zip.writestr(name,data)
            zip.writestr('image-manifest.json',json.dumps(manifest))
        return archive,manifest

    def test_host_approval_fixture_is_not_shippable(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ['command-profile-reference.mjs', 'terminal-registry-reference.mjs',
                         'terminal-registry-plugin.mjs', 'terminal-authority-plugin.mjs', 'terminal-profile-reference.mjs']:
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


if __name__=='__main__': unittest.main()
