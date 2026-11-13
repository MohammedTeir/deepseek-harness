"""Synthetic asset-integrity negative controls; no runtime compatibility claim."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
ANDROID=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('pty_assets',ANDROID/'scripts/prepare_node_pty_assets.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class NodePtyAssetTest(unittest.TestCase):
    def test_rejects_changed_binary_package_and_source(self):
        with tempfile.TemporaryDirectory(prefix='harness-pty-assets-') as temporary:
            root=Path(temporary);android=root/'apps/android';source=android/'runtime/out/node-pty';package=root/'dependencies/node-pty'
            def write(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [package/'src/unix/pty.cc',android/'runtime/node-pty-proof/fixture.cpp',root/'patches/node-pty@1.2.0-beta.15.patch',source/'libharness_node_pty.so',source/'libharness_pty_fixture.so',source/'package/lib/index.js',package/'lib/index.js']:
                write(path,b'fixed test bytes')
            record={'sourcePackage':'dependencies/node-pty','sourceSha256':sha(package/'src/unix/pty.cc'),'fixtureSourceSha256':sha(android/'runtime/node-pty-proof/fixture.cpp'),'repositoryPatchSha256':sha(root/'patches/node-pty@1.2.0-beta.15.patch'),'packageFilesSha256':{'lib/index.js':sha(package/'lib/index.js')},'binarySha256':sha(source/'libharness_node_pty.so'),'fixtureSha256':sha(source/'libharness_pty_fixture.so')}
            write(source/'build.json',json.dumps(record).encode())
            for name in ['smoke.mjs','loader.cjs']:write(android/'runtime/node-pty-proof'/name,b'fixed script')
            write(android/'runtime/proc-identity.mjs',b'fixed identity')
            write(package.parent/'node-addon-api/LICENSE.md',b'fixed license')
            with patch.object(module,'ANDROID',android),patch.object(module,'ROOT',root):
                module.prepare(root/'assets',root/'native')
                for target in [source/'libharness_node_pty.so',package/'src/unix/pty.cc',source/'package/lib/index.js']:
                    original=target.read_bytes();target.write_bytes(b'changed')
                    with self.assertRaises(ValueError):module.prepare(root/'assets',root/'native')
                    target.write_bytes(original)
