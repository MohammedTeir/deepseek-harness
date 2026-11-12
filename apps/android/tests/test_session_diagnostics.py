"""Real host filesystem probes and denial; no Android compatibility evidence."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class SessionDiagnosticsTest(unittest.TestCase):
    def run_node(self, code, directory):
        module=(Path(__file__).resolve().parents[1]/'runtime/session-diagnostics.mjs').as_uri()
        result=subprocess.run(['node','--input-type=module','-e',f'import * as probe from {json.dumps(module)};\n'+code,directory],
                              capture_output=True,text=True,timeout=20,check=True)
        return json.loads(result.stdout)

    def test_actual_directory_sync_file_sync_and_exclusive_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            result=self.run_node('console.log(JSON.stringify(await probe.storagePrerequisites(process.argv[1])))',directory)
            self.assertEqual(result,{'directorySync':True,'fileSync':True,'exclusiveHardlinkPublish':True,'existingPathRejected':True})
            self.assertEqual(list(Path(directory).iterdir()),[])

    @unittest.skipUnless(os.name=='posix' and hasattr(os,'getuid') and os.getuid()!=0,'Non-root POSIX permission check')
    def test_actual_permission_error_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            os.chmod(directory,0o500)
            try:
                result=self.run_node('try { await probe.storagePrerequisites(process.argv[1]); throw new Error("unexpected success"); } catch (error) { console.log(JSON.stringify(probe.describeFailure(error))); }',directory)
                self.assertEqual(result['code'],'EACCES')
                self.assertEqual(result['syscall'],'mkdtemp')
            finally: os.chmod(directory,0o700)

    def test_inventory_reports_symlinks_without_following_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outside=root/'outside';outside.mkdir();(outside/'private').write_text('fixture')
            inside=root/'inside';inside.mkdir();(inside/'alias').symlink_to(outside,target_is_directory=True)
            result=self.run_node('console.log(JSON.stringify(await probe.sessionInventory(process.argv[1])))',str(inside))
            self.assertEqual(len(result['entries']),1)
            self.assertTrue(result['entries'][0]['symbolicLink'])
            self.assertFalse(result['entries'][0]['statDirectory'])
