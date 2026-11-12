# Atomic persistence investigation and APK #1

## Scope and decision

Reference for the isolated native proof, publication inventory and physical-device acceptance. Gate 2 is BLOCKED. APK #1 does not load Harness, alter its persistence packages, or touch the existing runtime app's data. Its package is `ai.deepseek.harness.android.atomicpoc`, separate from `ai.deepseek.harness.android.runtimepoc`. A successful native proof permits a subsequent adapter review; it is not session-recovery acceptance or production qualification.

The [v8 phone evidence](../evidence/phone-v8-hardlink-failure.json) establishes EACCES from link inside app-private storage after original Harness initialization. AOSP Android 11 `app_neverallows.te` explicitly prohibits `all_untrusted_apps file_type:file link`. This is consistent with the observation, but Xiaomi's effective policy and a matching AVC denial have not been captured. Neither a filesystem-wide absence of hardlinks nor a specific vendor-policy cause is established by this one app result.

## Publication inventory

[Source-pinned inventory](../evidence/atomic-publication-inventory.json) records the inspected paths and decisions. Searches include direct calls, aliased imports such as linkFile, native link/linkat and migration callers; the prior full dependency audit is retained.

| Owner and operation | Required semantics and failure behavior | Android decision |
|---|---|---|
| session-persistence-jsonl: materializePosix | Synced staging file; exclusive publication; directory fsync before redundant-stage cleanup. Competing independent runtimes must not replace an existing session; publication errors propagate and unpublished stages are removed. | Candidate adapter after physical acceptance. A move consumes staging, unlike link; cleanup and ambiguous post-publication errors require explicit handling. |
| session-persistence-jsonl: publishCurrentExclusive in generation.ts | Generation migration shares the exclusive publication path, including migration workers. EEXIST invokes existing-generation validation; other failures propagate. Directory sync follows successful publication. | Same candidate, but preserve collision validation, staged evidence and crash-recovery ordering; first-session success alone is insufficient. |
| fs-local: writeFileAtomic/createIfAbsent | A private child staging directory, synced file and atomic no-replace destination. Per-process serialization cannot protect against independent publishers. Existing-target failure maps through throwGuardedCreateFailure. | Separate cross-directory qualification needed: source is inside a staging subdirectory. This same-directory PoC is insufficient. The existing implementation syncs the file but has no equivalent explicit destination-directory sync here; do not invent a stronger baseline guarantee. |
| attachment-local: publishStagedObject | Same-filesystem immutable object publication; EEXIST requires digest verification. Read-only mode and ancestor directory sync precede returning a reference. Failure removes the owned staging file. | Separate cross-directory/ancestor review; preserve dedup and consumed-source cleanup. No blind substitution. |
| attachment-local: publishImmutableAlias | Adds another name while retaining the original immutable source. EEXIST verifies the digest; chmod and ancestor sync complete the operation. | A rename would remove the source and break semantics. Remains BLOCKED pending a separately reviewed alias/storage design; not eligible for direct move publication. |
| storage-json: writeAtomic | Intended whole-file replacement with file sync, ordinary rename and directory sync. | Keep unchanged; no hardlink publication and no no-replace requirement. |
| experimental webworker-runtime virtual link/linkSync | In-memory virtual filesystem operations; no Bionic syscall in this implementation. | Keep unchanged; not evidence of device filesystem compatibility. |
| PTC module.link, module graph links, boot/test symlinks | ESM resolution or symbolic links, not hardlink publication. | Keep unchanged. |
| Native system and Windows helpers | No native hardlink publisher found in maintained native/system C/C++ sources; original Windows no-replace publication uses its own platform implementation. | Keep unchanged; the PoC is under apps/android only. |

## Candidate comparison

| Candidate | Atomic visibility / independent no-overwrite | Durability and maintenance | Decision |
|---|---|---|---|
| renameat2(RENAME_NOREPLACE) | Kernel performs the absent-destination test and rename atomically; EEXIST leaves both names untouched. Consumes source on success. | Sync file before publication, then the parent directory; same mount required. Native syscall, filesystem, policy and error behavior need device qualification. | Leading candidate for same-directory prepared-file publication; isolated PoC only. |
| open(O_CREAT\|O_EXCL) and write final | Exclusive creation, but exposes empty/partial final content during write or after process death. | File sync cannot remove that visibility window; requires a different reader/commit protocol. | Reject as an equivalent replacement. |
| check-then-rename / ordinary rename | Can replace another process's destination between check and rename. | Locking only within one process does not close the race. | Reject. |
| O_EXCL temporary file plus ordinary rename | Staging can be complete, but publication still replaces the destination. | Correct for storage-json's replace semantics only. | Reject for no-replace publication. |
| mkdir lock or application lock around publication | Requires every writer and reader to share a new lock/recovery protocol; does not itself provide atomic publication. | Stale locks, process death and mixed-version writers introduce new obligations. | No demonstrated advantage over kernel no-replace operation. |
| Android Java/Kotlin file move | No demonstrated atomic no-replace primitive with equivalent collision/durability guarantees in the current implementation. | A Java bridge alone does not prove the underlying syscall or Android policy behavior. | Native fixed test first; no production bridge selected. |
| Existing hardlink protocol | Correct original no-replace behavior, but reported app execution is denied. | Retains staging until unlink and needs directory synchronization. | Preserve on non-Android; do not retry with weaker semantics on EACCES. |

No performance measurements or speedup claims are made. The upstream discussion's check-then-rename patch explicitly acknowledges a concurrent-clobber window. It is not adopted; its old release/Termux testing does not qualify this standalone APK or current source revision.

## Platform evidence

[Retrieval record](../evidence/atomic-platform-research.json) preserves URLs, retrieval outcomes and SHA-256 of inspected source texts. The [rename manual](https://man7.org/linux/man-pages/man2/rename.2.html) specifies RENAME_NOREPLACE and filesystem support limits. Inspected Linux v4.14 VFS checks an occupied destination under rename locking; its ext4 and F2FS sources accept RENAME_NOREPLACE. These sources do not prove the phone's kernel configuration, mount or policy. F2FS's local comment about ordinary rename describes VFS having already handled no-replace checks, not permission to substitute userspace rename.

Android 10 Bionic headers/syscall list expose renameat but not renameat2. NDK r28c stdio.h marks renameat2 introduced in API 30, consistent with Android 11's LIBC_R symbol block. The PoC compiles with aarch64-linux-android29-clang++, uses SYS_renameat2 from NDK headers and syscall(...), and never imports the API-30 wrapper. The inspected ARM64 generic Linux UAPI assigns renameat2 syscall 276; source does not hardcode this number. A direct syscall still obeys Android seccomp, SELinux, DAC and filesystem restrictions. ENOSYS, EINVAL, EOPNOTSUPP and other errors propagate without fallback. The initially requested generated Bionic seccomp path returned 404 and remains recorded. The subsequently retrieved Android 10 SECCOMP_WHITELIST_COMMON.TXT explicitly lists renameat2 for all architectures as a useful syscall not yet used by Bionic. The retrieved seccomp policy source selects an app filter; this source evidence does not establish the vendor's installed filter or actual API-29 execution.

## Native proof and guarantees tested

The exact C++ source runs on Linux for comparison and is cross-compiled into an installer-owned Android executable named libatomic_poc.so. A private Android service accepts only a fixed start message, creates a new 0700 private test directory, and launches that executable with a scrubbed environment. It accepts no arbitrary command, filename or publication request. The native entry refuses root, a non-owned/nonprivate directory and a final-component root symlink. Publication is restricted to validated basenames under one pinned directory descriptor; source symlinks are rejected, destination symlinks must return EEXIST. No root, Termux, network or storage permission is requested.

The helper is experimental, not a production filesystem API. Trusted fixed test names prevent traversal here; fstatat is not claimed to prevent malicious same-UID staging substitution between inspection and rename. Same-UID code is not isolated. Cross-directory publication, arbitrary plugin inputs, hardlink aliases and a Node native-addon interface remain unqualified and are not exposed by this APK.

| Required test | Executed operation and acceptance | Physical status |
|---|---|---|
| A: publication | Exclusive temp open, complete write, file fsync, no-replace syscall, parent fsync, same device/inode and exact bytes, consumed staging name, synced cleanup. | BLOCKED pending phone |
| B: collision | EEXIST, byte hash and inode/device/mode/UID/GID/size/link-count/mtime/ctime unchanged; stage preserved until cleanup; existing destination symlink protected. Access time is excluded because observation itself can update it. | BLOCKED pending phone |
| C: concurrency | 16 rounds, eight independent forked publisher processes each (128 publishers); eight distinct PIDs per round, one winner and seven EEXIST results. Another independent observer process per round reads while publishers run; only complete expected content may appear. A late publisher must not replace the winner. | BLOCKED pending phone |
| D: interruption | Two SIGKILL cases at each of five pipe-acknowledged boundaries (10 children): before file sync, after file sync, after publication/before directory sync, after directory sync, and during cleanup. Reopen directory after child death, inspect exact bytes/names and sync recovery cleanup. | BLOCKED pending phone |
| E: sync and failures | A/D assert normal sync order. Invalid-descriptor fsync tests error propagation, including retained visible publication after an injected bad-directory-descriptor failure and later explicit recovery sync. Real permission, missing-source, cleanup and traversal failures must reject. ENOSYS/EINVAL/EOPNOTSUPP injections test propagation only, explicitly labeled simulated. | BLOCKED pending phone |
| F: device/security | Native UID/PID/parent, architecture, kernel, filesystem magic, available SELinux context/enforcement reads; host adds Android model/release/API/ABIs/hardware/fingerprint and actual APK/native hashes. Ordinary UID must match supervisor; installed binary must not be writable. | BLOCKED pending phone |

All child processes have parent-death SIGKILL, bounded evidence waits and an owner that reaps them. The native watchdog is 75 seconds; supervisor deadline is 85 seconds and manual UI deadline is 100 seconds. Cancellation is not proof of lifecycle safety on Android until exercised. Process-kill checks establish observable process-restart state only, not power-loss survival, storage-controller honesty, cross-directory durability or application/session restart recovery. A published file before successful directory fsync is explicitly classified durability-unconfirmed. No published file is deleted to pretend that a failed sync rolled back publication.

## Build and install tutorial

Prerequisites: existing Android SDK 36, NDK 28.2.13676358, JDK 21 and this branch's Android toolchain. In the repository root, use the same environment variables as the [Android build guide](../../../ANDROID_BUILD_GUIDE.md).

```sh
./apps/android/gradlew -p apps/android :atomic-proof:assembleDebug :atomic-proof:assembleDebugAndroidTest :atomic-proof:lintDebug --console=plain -Pkotlin.compiler.execution.strategy=in-process
python3 apps/android/scripts/inspect_atomic_apk.py
```

The [build record](../evidence/atomic-poc-apk1-build.json) pins actual APK/native/source digests and signature/alignment/ELF checks. APK #1 is intentionally much smaller than the Node runtime APK because it contains only the isolated native test, Android host and notices; it is not a replacement runtime build.

On the phone, install atomic-proof-debug.apk as a separate app named Harness atomic storage proof. Keep the old runtime app and its data. Open this app, tap Run native atomic persistence tests, confirm Run once and remain on screen until output appears. Tap Copy complete result and send the entire JSON, including FAIL/BLOCKED output. Repeat once in a fresh invocation; do not clear either app's data to force a pass. If the process dies or the screen times out, retain private evidence with ADB. Rendered Android layout, consent/copy interactions and cancellation remain physical-device checks, not verified by compilation.

With USB debugging and an authorized computer, select the phone from adb devices -l, then run:

```sh
python3 apps/android/scripts/test_device.py --adb adb --serial SERIAL --proof atomic --output /tmp/atomic-phone-run1
python3 apps/android/scripts/validate_atomic_result.py /tmp/atomic-phone-run1/runtime-result.json --build-record apps/android/evidence/atomic-poc-apk1-build.json
```

The selected-device runner installs both APKs with -r, clears only stale diagnostic summary files and runs AtomicProofTest. It retains actual device properties, APK hashes, instrumentation output, result and stderr; it does not clear test artifacts or Harness sessions. It requires complete native assertions and matching delivered APK/native hashes. A manually copied result can be saved as phone-result.json and passed to the same validator. The validator rejects missing tests, changed artifact hashes, duplicate publishers, extra winners, missing sync acknowledgements and unsupported success claims; it does not authenticate physical hardware identity by itself.

For manual failure retrieval:

```sh
adb -s SERIAL shell run-as ai.deepseek.harness.android.atomicpoc cat files/atomic-probe/result.json
adb -s SERIAL shell run-as ai.deepseek.harness.android.atomicpoc ls files/atomic-probe
```

Each run-* directory retains stdout.json, stderr.txt and any reached result.json plus test artifacts. If no result exists, collect those files from the matching run directory. Available AVC diagnostics may be requested through authorized ADB logcat, filtered to the reported native PID/process and reviewed before sharing. Android may withhold audit/kernel logs; report that limitation rather than rooting the phone or treating absent AVC lines as a successful syscall. This app does not collect device-wide logs.

## Blocking integration checkpoint

A reviewer must analyze complete results from actual physical hardware and record PASS/FAIL/BLOCKED for A–F before any production adapter is introduced. No connected phone is available in the cloud. A host pass, APK build, parsed fixture or emulator result cannot satisfy this checkpoint. API 29 and newer-device coverage remain separate requirements even if the first Android 11 phone passes.

After that checkpoint, review a shared adapter in the existing native/filesystem architecture, including source-consumption cleanup and both JSONL materialization/generation paths; preserve non-Android behavior and session format. Qualify separate cross-directory and alias requirements before widening it. APK #2 then uses original SDK/profile/JSONL to verify acknowledged shutdown, runtime restart, previous-invocation recovery and separately observed app restart/process death. Trusted approved-command work follows authentic persistence. None of that integration or recovery is included in APK #1.
