"""Execute the exact isolated native suite on Linux; never Android execution evidence."""
import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class AtomicNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="harness-atomic-tests-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.root = Path(cls.directory.name)
        cls.binary = cls.root / "atomic-poc"
        source = Path(__file__).parents[1] / "atomic-proof/native/atomic_poc.cpp"
        subprocess.run(["c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(cls.binary)],
                       check=True, timeout=60)
        cls.work = cls.root / "positive"
        cls.work.mkdir(mode=0o700)
        process = subprocess.run([str(cls.binary), str(cls.work)], capture_output=True, text=True, timeout=90)
        cls.record = json.loads(process.stdout)
        if process.returncode != 0:
            raise AssertionError(process.stdout + process.stderr)
        cls.tests = {x["name"]: x for x in cls.record["tests"]}
        evidence = os.environ.get("ANDROID_ATOMIC_HOST_EVIDENCE")
        if evidence:
            Path(evidence).write_text(json.dumps({"schemaVersion": 1, "environment": "Linux host, not Android",
                "command": [str(cls.binary), str(cls.work)], "exitCode": process.returncode,
                "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "androidExecuted": False, "result": cls.record}, indent=2) + "\n")

    def test_success_preserves_identity_and_synchronizes_cleanup(self):
        value = self.tests["A-publication"]
        self.assertEqual(value["status"], "PASS")
        for key in ["fileFsync", "directoryFsync", "sameInode", "sourceConsumed", "cleanupSynced"]:
            self.assertTrue(value["evidence"][key])
        self.assertFalse((self.work / "success/published").exists())

    def test_collision_preserves_bytes_and_metadata(self):
        value = self.tests["B-existing-destination"]["evidence"]
        self.assertEqual(value["code"], "EEXIST")
        self.assertEqual(value["before"], value["after"])
        self.assertEqual(hashlib.sha256(value["beforeContent"].encode()).hexdigest(),
                         hashlib.sha256(value["afterContent"].encode()).hexdigest())
        self.assertTrue(value["destinationSymlinkProtected"])
        self.assertFalse((self.work / "collision/pending").exists())

    def test_independent_processes_have_one_complete_winner(self):
        value = self.tests["C-independent-processes"]["evidence"]
        self.assertEqual(value["processesPerRound"], 8)
        self.assertEqual(value["rounds"], 16)
        self.assertEqual(value["totalPublishers"], 128)
        self.assertEqual(value["totalIndependentObservers"], 16)
        all_pids = []
        for result in value["roundResults"]:
            self.assertEqual(result["successes"], 1)
            self.assertEqual(result["collisions"], 7)
            self.assertEqual(len(set(result["pids"])), 8)
            self.assertNotIn(self.record["pid"], result["pids"])
            self.assertEqual(result["completeReadObservations"], 8)
            self.assertTrue(result["lateCollisionProtected"])
            self.assertGreater(result["independentObserverCompleteReads"], 0)
            self.assertNotIn(result["independentObserverPid"], result["pids"])
            all_pids.extend(result["pids"])
        self.assertEqual(len(set(all_pids)), 128)

    def test_kill_boundaries_are_explicit_and_recovery_inspected(self):
        value = self.tests["D-interruption"]["evidence"]
        self.assertEqual(len(value["cases"]), 10)
        self.assertFalse(value["powerLossTested"])
        for case in value["cases"]:
            self.assertEqual(case["signal"], 9)
            self.assertTrue(case["recoveryCleanupSynced"])
            if case["boundary"] in ["before-file-sync", "after-file-sync"]:
                self.assertFalse(case["published"])
            elif case["boundary"] == "after-publish-before-directory-sync":
                self.assertTrue(case["published"])
                self.assertFalse(case["directoryFsyncAcknowledged"])
            else:
                self.assertTrue(case["directoryFsyncAcknowledged"])

    def test_errors_fail_closed_without_fallback(self):
        value = self.tests["E-errors-and-boundaries"]["evidence"]
        self.assertTrue(value["traversalRejected"])
        self.assertTrue(value["sourceSymlinkRejected"])
        self.assertTrue(value["fsyncFailurePropagated"])
        self.assertEqual(value["readOnlyDirectoryErrno"], 13)
        self.assertEqual(value["cleanupMissingErrno"], 2)
        self.assertFalse(value["fallbackUsed"])
        self.assertEqual(value["injectedUnsupportedErrors"], ["ENOSYS", "EINVAL", "EOPNOTSUPP"])
        self.assertTrue(value["unsupportedErrorsAreSimulated"])

    def test_root_symlink_rejected(self):
        target = self.root / "root-alias"
        target.symlink_to(self.work, target_is_directory=True)
        result = subprocess.run([str(self.binary), str(target)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "BLOCKED")

    def test_nonprivate_root_rejected(self):
        target = self.root / "nonprivate"
        target.mkdir(mode=0o755)
        target.chmod(0o755)
        result = subprocess.run([str(self.binary), str(target)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("0700", json.loads(result.stdout)["error"])

    def test_evidence_validation_rejects_weakened_or_missing_results(self):
        # Parser fixture derived from real Linux results; added Android metadata is synthetic.
        # It never leaves this test and is not Android compatibility evidence.
        path = Path(__file__).parents[1] / "scripts/validate_atomic_result.py"
        spec = importlib.util.spec_from_file_location("atomic_result_validator", path)
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        value = copy.deepcopy(self.record)
        value.update(nativeExitCode=0, apkSha256="1" * 64, nativeSha256="2" * 64,
                     uid=20000, supervisorUid=20000, supervisorPid=value["parentPid"], architecture="aarch64",
                     installedExecutableWritable=False, device={"api": 30, "model": "synthetic parser fixture"})
        data = {item["name"]: item["evidence"] for item in value["tests"]}
        data["A-publication"]["publishedIdentity"]["uid"] = 20000
        b = data["B-existing-destination"]
        b["before"]["uid"] = b["after"]["uid"] = 20000
        b["beforeSha256"] = b["afterSha256"] = hashlib.sha256(b["beforeContent"].encode()).hexdigest()
        kwargs = {"apk_sha256": "1" * 64, "native_sha256": "2" * 64}
        validator.validate(value, **kwargs)
        mutations = [
            lambda v: v.update(uid=0),
            lambda v: v.update(apkSha256="3" * 64),
            lambda v: v.update(nativeExitCode=1),
            lambda v: v.update(powerLossTested=True),
            lambda v: v["tests"].pop(),
            lambda v: v["tests"][0]["evidence"].update(directoryFsync=False),
            lambda v: v["tests"][1]["evidence"].update(afterContent="changed"),
            lambda v: v["tests"][2]["evidence"]["roundResults"][0].update(successes=2),
            lambda v: v["tests"][2]["evidence"]["roundResults"][0].update(pids=[1] * 8),
            lambda v: v["tests"][2]["evidence"]["roundResults"][0].update(independentObserverCompleteReads=0),
            lambda v: v["tests"][3]["evidence"]["cases"][0].update(directoryFsyncAcknowledged=True),
            lambda v: v["tests"][4]["evidence"].update(fallbackUsed=True),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                altered = copy.deepcopy(value)
                mutate(altered)
                with self.assertRaises(ValueError):
                    validator.validate(altered, **kwargs)
        with self.assertRaises(ValueError):
            validator.validate(self.record, **kwargs)

    def test_no_harness_or_power_loss_claim(self):
        self.assertFalse(self.record["harnessPersistenceModified"])
        self.assertFalse(self.record["gate2Passed"])
        self.assertFalse(self.record["powerLossTested"])
        self.assertNotEqual(self.record["uid"], 0)


if __name__ == "__main__":
    unittest.main()
