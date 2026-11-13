"""Validate executed APK #1 evidence; validation alone does not establish physical hardware."""
import argparse
import hashlib
import json
from pathlib import Path


def validate(value: dict, *, apk_sha256: str, native_sha256: str) -> None:
    """Reject incomplete, contradictory, altered-artifact or weakened test results."""
    def need(condition, message):
        if not condition:
            raise ValueError(message)

    need(value.get("schemaVersion") == 1 and value.get("suite") == "atomic-noreplace-native-v1", "Wrong suite")
    need(value.get("status") == "PASS" and value.get("nativeExitCode") == 0, "Native suite did not pass")
    need(value.get("apkSha256") == apk_sha256 and value.get("nativeSha256") == native_sha256, "Artifact digest mismatch")
    need(value.get("uid", 0) >= 10000 and value.get("uid") == value.get("supervisorUid"), "Wrong ordinary app UID")
    need(value.get("pid", 0) > 0 and value.get("parentPid") == value.get("supervisorPid")
         and value.get("pid") != value.get("supervisorPid"), "Wrong native process identity")
    need(value.get("architecture") == "aarch64" and value.get("device", {}).get("api", 0) >= 29, "Wrong Android ABI/API")
    need(bool(value.get("device", {}).get("model")) and bool(value.get("kernel"))
         and bool(value.get("filesystemType")), "Missing device/kernel/filesystem data")
    for key in ["installedExecutableWritable", "harnessPersistenceModified", "gate2Passed", "powerLossTested"]:
        need(value.get(key) is False, f"Unsupported claim or missing field: {key}")
    tests = value.get("tests", [])
    names = [item.get("name") for item in tests]
    expected = {"A-publication", "B-existing-destination", "C-independent-processes", "D-interruption", "E-errors-and-boundaries"}
    need(len(names) == 5 and set(names) == expected, "Incomplete/duplicated test set")
    need(all(item.get("status") == "PASS" for item in tests), "Individual native failure")
    data = {item["name"]: item["evidence"] for item in tests}
    a = data["A-publication"]
    need(all(a.get(key) is True for key in ["fileFsync", "directoryFsync", "sameInode", "sourceConsumed", "cleanupSynced"]), "Publication/sync incomplete")
    need(a.get("publishedIdentity", {}).get("uid") == value["uid"], "Wrong published-file owner")
    b = data["B-existing-destination"]
    need(b.get("code") == "EEXIST" and b.get("errno") == 17, "Collision not EEXIST")
    need(b.get("before") == b.get("after") and isinstance(b.get("before"), dict)
         and {"inode", "device", "mode", "uid", "gid", "size", "links", "mtimeSeconds", "mtimeNanos", "ctimeSeconds", "ctimeNanos"} <= b["before"].keys(), "Collision metadata changed/missing")
    need(b["before"].get("uid") == value["uid"], "Wrong existing-file owner")
    need(b.get("beforeContent") == b.get("afterContent") == "existing destination must survive\n", "Collision bytes changed")
    digest = hashlib.sha256(b["beforeContent"].encode()).hexdigest()
    need(b.get("beforeSha256") == b.get("afterSha256") == digest, "Collision hash mismatch")
    need(b.get("destinationSymlinkProtected") is True and b.get("loserCleanupSynced") is True, "Collision cleanup/protection incomplete")
    c = data["C-independent-processes"]
    need(c.get("processesPerRound") == 8 and c.get("rounds") == 16 and c.get("totalPublishers") == 128
         and c.get("totalIndependentObservers") == 16, "Wrong process/round counts")
    rounds = c.get("roundResults", [])
    need(len(rounds) == 16 and {r.get("round") for r in rounds} == set(range(16)), "Missing concurrency round")
    for r in rounds:
        pids = r.get("pids", [])
        need(len(pids) == len(set(pids)) == 8 and all(isinstance(p, int) and p > 0 and p != value["pid"] for p in pids), "Not independent publishers")
        need(r.get("successes") == 1 and r.get("collisions") == 7 and r.get("completeReadObservations") == 8
             and r.get("lateCollisionProtected") is True, "Concurrent publication invariant failed")
        need(r.get("independentObserverPid", 0) > 0 and r.get("independentObserverPid") not in [value["pid"], *pids]
             and r.get("independentObserverCompleteReads", 0) > 0, "Independent visibility observer missing")
    d = data["D-interruption"]
    need(d.get("iterationsPerBoundary") == 2 and d.get("powerLossTested") is False, "Wrong interruption scope")
    boundaries = ["before-file-sync", "after-file-sync", "after-publish-before-directory-sync", "after-directory-sync", "during-cleanup"]
    cases = d.get("cases", [])
    need(len(cases) == 10 and {(x.get("boundary"), x.get("iteration")) for x in cases} == {(b, i) for b in boundaries for i in range(2)}, "Missing interruption case")
    for case in cases:
        index = boundaries.index(case["boundary"])
        need(case.get("signal") == 9 and case.get("pid", 0) > 0 and case["pid"] != value["pid"]
             and case.get("recoveryCleanupSynced") is True, "Interruption/recovery incomplete")
        need(case.get("published") is (index >= 2) and case.get("fileFsyncAcknowledged") is (index >= 1)
             and case.get("directoryFsyncAcknowledged") is (index >= 3), "Incorrect synchronization checkpoint")
        classification = "unpublished-temporary" if index < 2 else "published-durability-unconfirmed" if index == 2 else "published-directory-sync-acknowledged"
        need(case.get("classification") == classification, "Incorrect durability classification")
    e = data["E-errors-and-boundaries"]
    need(all(e.get(k) is True for k in ["traversalRejected", "sourceSymlinkRejected", "fsyncFailurePropagated", "postPublicationSyncFailureRetainsFile", "syncFailureDescriptorIsInjected", "unsupportedErrorsAreSimulated"]), "Missing boundary/error checks")
    need(e.get("missingSourceErrno") == 2 and e.get("invalidDescriptorErrno") == 9
         and e.get("readOnlyDirectoryErrno") == 13 and e.get("cleanupMissingErrno") == 2, "Wrong actual error evidence")
    need(e.get("injectedUnsupportedErrors") == ["ENOSYS", "EINVAL", "EOPNOTSUPP"] and e.get("fallbackUsed") is False, "Unsupported fallback/error suppression")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--build-record", type=Path, required=True)
    args = parser.parse_args()
    build = json.loads(args.build_record.read_text())
    validate(json.loads(args.result.read_text()), apk_sha256=build["apkSha256"], native_sha256=build["nativePackagedSha256"])
    print("Evidence assertions PASS; physical hardware identity and test review are still required before integration.")


if __name__ == "__main__":
    main()
