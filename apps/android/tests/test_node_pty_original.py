"""Real original node-pty host/source-addon tests; no Android execution evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ANDROID = Path(__file__).parents[1]
ROOT = ANDROID.parents[1]

@unittest.skipUnless(sys.platform.startswith('linux') and Path('/proc/self').exists() and os.getuid() != 0, 'Non-root Linux procfs host required')
class OriginalNodePtyTest(unittest.TestCase):
    def test_original_js_native_source_and_loader_with_real_pty(self):
        with tempfile.TemporaryDirectory(prefix='harness-node-pty-') as directory:
            root = Path(directory)
            package = (ROOT/'packages/subprocess/subprocess-local/node_modules/node-pty').resolve()
            headers = Path(os.environ.get('ANDROID_NODE_BUILD_DIR', '/workspace/android-node'))/'node-v24.22.1/src'
            fixture = root/'fixture'
            subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',str(ANDROID/'runtime/node-pty-proof/fixture.cpp'),'-o',str(fixture)],check=True,timeout=30)
            addon = root/'original-pty.node'
            subprocess.run(['c++','-std=c++17','-shared','-fPIC','-pthread','-DNAPI_VERSION=8','-DNAPI_CPP_EXCEPTIONS','-I'+str(headers),'-I'+str((package.parent/'node-addon-api').resolve()),str(package/'src/unix/pty.cc'),'-lutil','-o',str(addon)],check=True,timeout=60)
            env = {**os.environ,'HARNESS_NODE_PTY_PACKAGE':str(package),'HARNESS_NODE_PTY_ADDON':str(addon),'HARNESS_NODE_PTY_USE_SOURCE_BINDING':'1','HARNESS_NODE_PTY_FIXTURE':str(fixture)}
            result = subprocess.run(['node',str(ANDROID/'runtime/node-pty-proof/smoke.mjs'),str(root/'result.json')],cwd=root,env=env,capture_output=True,text=True,timeout=35)
            self.assertEqual(result.returncode,0,result.stderr+(root/'result.json').read_text())
            value = json.loads((root/'result.json').read_text())
            self.assertEqual(value['status'],'PASS')
            self.assertFalse(value['gate3Passed'])
            self.assertFalse(value['originalTerminalIntegrated'])
            self.assertEqual([item['signal'] for item in value['cases']],[0,0,2,15,9])
            self.assertTrue(all(item['childNoLongerObservable'] for item in value['cases']))
            self.assertEqual(value['cases'][1]['exitCode'],7)
            missing_env=dict(env);missing_env.pop('HARNESS_NODE_PTY_FIXTURE')
            missing=subprocess.run(['node',str(ANDROID/'runtime/node-pty-proof/smoke.mjs'),str(root/'missing.json')],cwd=root,env=missing_env,capture_output=True,text=True,timeout=10)
            self.assertEqual(missing.returncode,1)
            self.assertIn('no shell fallback',json.loads((root/'missing.json').read_text())['failure'])
            handle_result=subprocess.run(['node',str(ANDROID/'tests/terminal-handle-reference.mjs'),str(root/'handle.json')],cwd=root,env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(handle_result.returncode,0,handle_result.stdout+handle_result.stderr)
            if os.environ.get('HARNESS_PTY_HANDLE_HOST_EVIDENCE'):
                Path(os.environ['HARNESS_PTY_HANDLE_HOST_EVIDENCE']).write_text((root/'handle.json').read_text()+'\n')
            if os.environ.get('HARNESS_NODE_PTY_HOST_EVIDENCE'):
                Path(os.environ['HARNESS_NODE_PTY_HOST_EVIDENCE']).write_text(json.dumps({'environment':'Linux host only; NOT Android evidence','result':value,'stdout':result.stdout,'stderr':result.stderr,'exitCode':result.returncode},indent=2)+'\n')
