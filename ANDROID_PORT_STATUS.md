# Android port status

## Summary

Phase 0 is VERIFIED. The [Gate 1 review](ANDROID_GATE1_REVIEW.md) accepts the reviewed audit and a bounded Phase 2 runtime experiment. Phase 2 is IN PROGRESS; Gate 2 is not passed. The user reports the complete v4 JNI API probe passing on a Redmi Note 8 Pro. V5 adds an installer-owned Node executable/child comparison; phone results are pending. The original frontend and Harness engine are preserved. Android Harness profile readiness, session recovery and authorized tool execution remain unverified.

## Upstream sync: Phase 1 evidence refreshed

The fork's upstream release `0.2.2-rc.2` is merged into this audit branch with both histories retained. The [sync impact record](audit/android/upstream-sync-impact.json) identifies the old and new revisions. The master specification is unchanged. Graphs, installed payloads, registry manifests and source indexes below now describe synced master, not the earlier release candidate. The former evidence remains in Git history.

The refresh reviews structured approval/cancellation errors, PTY load failures, credential masking, the new ripgrep/terminal/Office packages and the PTC evaluator's additional Node API. Native lock platform selection and terminal-bash defaults remain blockers. The later Gate 1 decision authorizes the bounded Phase 2 experiment; synchronization alone was not runtime acceptance.

## Baseline and verification

[Exact baseline and environment](audit/android/baseline.json) records the current fork, included upstream baseline and observed upstream HEAD separately. The checkout started clean, `origin` points to the author's fork, `upstream` points to the original project, and `feature/android-port` was created from fork master before the author-synchronized source was merged. The author-synchronized upstream source is included; no separate upstream update was selected.

| Check | Executed result | Limit |
|---|---|---|
| `git status --short`, remotes, branches, log and `ls-remote` | Correct fork/remotes; clean start; baseline recorded | Remote observations are point-in-time |
| `python3 audit/android/collect.py` | 398 importers, 1,755 package identities, 1,763 snapshots, 8,836 edges; zero unresolved endpoints | Complete committed lock graph, not future dynamic downloads |
| Installed package scan | 1,426 identities; manifests/hooks/source descriptors/binary headers inspected | Linux installation; no Android execution |
| Repeated graph/index collection | Four recorded graph/index SHA-256 values reproduced exactly | Same installed tree and source baseline |
| Binary payload/ELF dependency graph | 161 inspected payload nodes and 211 DT_NEEDED edges | Loader resolution on Android remains unverified |
| Registry manifest fetch and integrity comparison | 329/329 retrieved, zero fetch errors, all distribution integrity values match lock | Archive bytes not downloaded or executed |
| `python3 audit/android/index_sources.py` | 37 Node builtin specifiers, 383 platform-sensitive sites, 17 native source/matrix paths | Static references include different product/build roles |
| `pnpm install --frozen-lockfile` | PASS, 21.6 seconds; lockfile supply-chain policies passed for 1,755 entries | Host dependency installation only |
| `DSH_GATE_CONCURRENCY=2 pnpm run build` | PASS: 10 gates, 287.78 seconds; 369 client artifacts recorded | Host native addon, compilers, bundles, Web build and aggregate checks; no Android inference |
| `pnpm run lint` | PASS, with one existing unused-disable warning in client-ui-cot-translation | Host repository lint only |
| Current `pnpm run doc-sync` | PASS: 43/43 checks in 494.61 seconds | Exact-baseline conflict repaired through strict evidence validation; original evidence retained |
| Current `pnpm run test:docs` | PASS: 21/21 gates in 82.80 seconds | Includes repaired repository-reference validation |
| Reference-checker regression file | PASS: 46 tests | Valid evidence plus wrong-path, abbreviated, unknown, malformed, duplicate, nested and forbidden-URL rejection |
| `pnpm run verify-repository-references` | PASS | Original baseline JSON unchanged |

## Blockers and recommendation

Node >=24.9 has no demonstrated supported Android runtime in this audit. Existing native lock selection rejects Android. node-pty's Linux ARM64 binary has GNU/Linux linkage, and the default persistent terminal assumes `/bin/bash` plus bash-specific control behavior. Android W^X, linker, app identity, PTY permissions and lifecycle must be qualified on devices. MCP stdio and arbitrary Node plugins can bypass a replacement central subprocess service; secure privilege mediation requires more than UI approval.

Recommend original Web UI plus the authentic profile/Cordis engine under a Kotlin supervisor, while comparing a source-built shared-library runtime with a compliant APK-packaged executable. JNI is a candidate, not a mandatory or verified decision. Preserve existing model/provider abstractions and service seams. Defer optional Termux/root, desktop-native plugins and broad package installation.

## Review boundary and next milestone

Review the [audit](ANDROID_PORT_AUDIT.md), [compatibility matrix](ANDROID_COMPATIBILITY_MATRIX.md), [architecture](ANDROID_ARCHITECTURE.md), [security risks](ANDROID_SECURITY_MODEL.md) and [roadmap](ANDROID_IMPLEMENTATION_PLAN.md). Noninstalled binary payloads, runtime-downloaded artifacts and Android execution remain unverified; these must not be represented as compatible.

After the accepted Gate 1 review, the current milestone is an Android ARM64/API 29+ runtime qualification using real Node APIs and an authentic Harness profile: persistent session create/reopen, approved harmless command with actual stdout/stderr/exit, and denied-operation evidence. Phase 2 implementation is bounded by the review decision; no later gate is bypassed. PR publication remains subject to the author's authorization.

## Phase 2 experiment evidence

- Kotlin host, JNI shim and instrumentation-test source compile passed (31 tasks, 1m32s) with runtime asset preparation excluded for code-only checks. Initial offline resolution lacked AndroidX test dependencies; the online retry fetched them and passed with in-process Kotlin compilation. This is not an Android execution test or APK result.
- The unchanged upstream flock source cross-compiled with NDK r28c for ARM64/API 29. Its runtime loading/contention tests remain unrun on Android.
- Four ELF parser rejection/acceptance tests passed; they use synthetic inspection text and are not Android compatibility evidence.
- The API probe ran on Linux x64 Node 24.22.1: SQLite, workers, ESM, crypto and result-file output passed. Native Android locking was not run. DNS returned EAI_AGAIN, so DNS/TLS are unverified. Harness was explicitly not started.
- Pinned Node ARM64 source compilation resumed after interruption and completed with exit code 0. Host generators use `-O1`; the earlier `-O0` failure remains a failed attempt. Current binary/APK inspection evidence is recorded below.
- No physical device is attached and `/dev/kvm` is absent. Official emulator 37.2.13 and an API 30 x86_64 Google APIs image installed successfully. A software boot reached ADB online. The guest reports Android 11/API 30, 4 KB pages, x86_64 plus ARM64 ABI support through libndk_translation; sys.boot_completed was unset at observation. Node/Harness execution is not yet tested. Any ARM translation results must be labeled separately from native ARM64 hardware. Device/profile/session/tool acceptance remains BLOCKED. Normal APK generation requires inspected runtime libraries and notices and cannot silently package a replacement backend.

The production native lock selector still rejects Android. The runtime probe exercises the original C binding directly as a qualification step; it is not session integration. Genuine Harness profile boot, durable sessions and a native-authorized command must still be integrated and tested after runtime qualification. Optional Termux/root and original-UI integration are outside this bounded prototype.

Current validation: reference policy 46 tests passed, quick documentation 21/21, full doc-sync 43/43, TypeScript build checks 2/2, and root lint passed with one existing unused-disable warning. The first lint run found a new arrow-parentheses formatting error; it was corrected before the passing rerun. Original baseline and sync evidence JSON contents are unchanged.

The runtime code and instrumentation source compile retry passed with in-process Kotlin compilation. Device properties and the successful page-size query are recorded in `apps/android/evidence/emulator-observation.json`; this is software-emulated x86_64 with an advertised ARM translation bridge, not native ARM64 hardware.

## Recovered checkpoint

The workspace recovered with the Phase 2 source intact; the resumed Node build's final result is now available. Packaging fixture installation attempts failed while emulator package/settings services were unavailable. Framework logs showed system-service failures and restarts. A clean disposable-AVD retry produced no successful fixture instrumentation result. Phone testing remains required. Generated binaries, emulator images, build caches and the local debug keystore remain excluded from Git.

## Resumed Phase 2 validation

The Node build resumed against the retained source/object cache and produced `out/Release/libnode.so`. The packager uses this actual Makefile output. Successful source compilation and APK assembly do not establish Android execution or Harness readiness.

The packaged-executable comparison uses the unchanged, checksum-verified original Node UNIX entrypoint. Its first link attempt correctly returned BLOCKED while libnode was absent. After library completion, linking passed: Android ARM64 PIE, `/system/bin/linker64`, `$ORIGIN` search path and 16 KB LOAD alignment were inspected. This executable is not included in the JNI runtime APK and has not run on Android. Neither runtime strategy is selected by compilation alone.

Android lint for both modules and packaging debug/test APK assembly passed: 106 tasks in 1m33s. After improving native-linker and JNI argument diagnostics, Kotlin, JNI, instrumentation-source compilation and runtime-module lint passed again: 40 tasks in 23s. Runtime asset preparation was excluded only for these source checks. Packaging APK signature verification and 16 KB ZIP-alignment validation passed; its native fixtures and required notices are present. These checks establish build integrity, not Android execution.

The new selected-device test runner records APK hashes, device properties and complete instrumentation output. Its host regression rejects empty, incomplete, wrong-count and crashed runner output. The unavailable-device path ran and returned BLOCKED/nonzero; no phone or emulator test has passed. The runner preserves the distinction between packaging, Node APIs and authentic Harness acceptance. Gate 2 remains BLOCKED on actual runtime/profile/session/tool evidence.

Resumed validation passed: five host test cases across the result-parser and ELF-parser suites, quick documentation 21/21 in 103.35s, full documentation 43/43 in 445.41s, and repository lint with the existing unused-disable warning. APK digests and signature/alignment checks are retained in `apps/android/evidence/build-validation.json`. These results do not change the device acceptance status.

## Real Node runtime APK build

VERIFIED for cross-build and packaging only: Node 24.22.1, NDK 28.2.13676358, ARM64/API 29, on the Linux x86_64 cloud host. The retained Node build exited 0. ELF inspection accepted Android dependencies and 16 KB LOAD alignment; the original flock addon, C++ runtime and notices were staged with hashes. Normal runtime/fixture debug and test APK assembly plus Android lint passed in 18s, 156 tasks, without excluding runtime asset preparation.

The runtime debug APK is 114,942,107 bytes; instrumentation APK is 2,176,494 bytes. Both passed signature and 16 KB ZIP-alignment verification. Inspection of the packaged, stripped libraries confirmed ARM64, allowed dependencies, LOAD alignment and the exported Node Start entry. Both input and packaged-byte hashes are retained because stripping changes binary bytes. Required scripts/licenses/build metadata are present. Explicit Kotlin/AndroidX, JUnit and Hamcrest license assets are included in all four runtime/fixture APKs and checked against their source texts. See `apps/android/evidence/runtime-apk-build.json` for commands, output and digests.

Next acceptance remains BLOCKED on device execution. Run the fixed API probe and instrumentation on the planned Redmi Note 8 Pro; Android 11 is user-reported and unconfirmed by ADB. Successful Node API results must precede authentic profile/native-lock integration, persistent session recovery and the approved command proof. No model, Harness profile, session or tool execution is included in this diagnostic APK. Gate 2 remains unpassed.

Validation for this artifact update: quick documentation 21/21 in 36.54s; full documentation 43/43 in 176.36s; repository lint passed with the existing unused-disable warning. Android assembly/lint, APK inspection and matching source/artifact hashes passed. Android instrumentation remains unrun because no device is attached.

## Phone failure and diagnostic update

The user supplied a screenshot showing `BLOCKED: embedded Node API probe exited with code 1` from the first APK on the reported Redmi Note 8 Pro. This is a user-reported failure, not a successful Node API test. The root cause is unknown: the previous host discarded Node stderr and displayed only the exit code. It does not establish whether JavaScript began or which API failed. No developer-controlled physical-device reproduction has run.

Version code 2 (`0.1.1-runtime-diagnostics`) captures Node startup/module-loader stderr in the dedicated runtime process, restores the descriptor after Node returns, and retains JavaScript failure stage/message in private JSON when possible. Failed exits remain failed; API assertions are unchanged. Error display reads bounded text and can scroll/select for reporting. The device runner also retains the fixed stderr file and removes stale evidence before testing.

Five host tests passed: real POSIX stderr capture/restoration, unavailable-file and symlink rejection, actual Linux Node worker denial with stage/error retention, and runner parsing. These do not reproduce the Android cause. Runtime APK/test APK assembly and Android lint passed: 78 tasks in 17s. Signature/alignment, packaged ELF, required notices and source/artifact hashes were inspected. `apps/android/evidence/runtime-diagnostics-build.json` records the new artifact separately; the original APK evidence remains unchanged. Next: repeat the phone probe and use its actual error to identify the fix. Gate 2 remains BLOCKED.

Diagnostic-update documentation checks passed: quick 21/21 and full 43/43; repository lint passed with the same existing unused-disable warning. The v2 download archive and its contained APK were downloaded and hash-verified before handoff. No successful v2 phone result is claimed.

## Explicit Node-API linkage candidate

The user's v2 transcript identifies `stage: native-lock`, Node `v24.22.1`, platform `android`, arch `arm64`, and a loader failure resolving `napi_create_function` from `libharness_system.so`. By the shipped probe's ordering, SQLite SELECT 42 and the worker response/termination completed before this stage. This is partial user-reported phone evidence, not developer-run instrumentation or full runtime acceptance. Lock semantics, later API checks and Harness remain unverified.

ELF inspection confirms Node exports the symbol while the old addon omitted `libnode.so` from DT_NEEDED. Version code 3 (`0.1.2-native-linkage`) links the unchanged original C source explicitly against the bundled Node library and uses `-z defs` to reject unresolved addon symbols at link time. Packaging requires that dependency and the Node export; asset preparation rejects old linkage metadata. Other binaries retain the narrower Android dependency allowlist. No production flock platform selection or agent code was changed.

Eight host ELF/metadata regressions passed. The actual v2 addon extracted from its hash-verified APK is rejected by the new guard; the real newly linked addon is accepted. Normal runtime APK/test APK assembly and Android lint passed: 78 tasks in 7s. The packaged addon retains DT_NEEDED `libnode.so`, and the packaged Node library exports the required function. Signatures, alignment, notices and hashes were inspected. Evidence is separate in `apps/android/evidence/runtime-native-linkage-build.json`; earlier artifact records remain unchanged. Re-run the full phone probe to test this candidate. Gate 2 remains BLOCKED.

V3 update validation passed: quick documentation 21/21, full documentation 43/43, repository lint with the existing unused-disable warning, and matching Android source/artifact hashes. Initial Filebin delivery failed with HTTP 507 (service storage full). A later retry uploaded v3 successfully, and the downloaded ZIP and APK hashes matched the inspected files. V3 phone verification remains pending.

## Android identity reporting adapter

The user's v3 transcript reaches result-write, then fails at process.getuid. By probe ordering, SQLite, workers, lock acquisition/contention/release and dynamic ESM completed; network tests were attempted but their flags were not returned. Crypto result generation and full serialization did not complete. These are partial user-reported observations, not developer-run instrumentation.

Node 24.22.1 src/node_internals.h excludes Android from NODE_IMPLEMENTS_POSIX_CREDENTIALS, and bootstrap omits the associated methods. V4 (0.1.3-android-identity, version code 4) preserves uid null and uidApiAvailable false when unavailable. Kotlin records separate androidUid/androidPid and identitySource android.os.Process after matching Node's PID to the service PID, and persists the combined evidence. No global process polyfill or fabricated UID is supplied. Instrumentation still requires app UID, non-root identity, correct process separation and all original API results.

Six host tests passed, including an isolated Linux Node preloader that removes getuid to exercise feature-absence reporting; this is not Android execution evidence. Runtime/test APK assembly and Android lint passed: 78 tasks in 15s. APK signatures, alignment, dependencies, notices and source/artifact hashes passed. Evidence is in apps/android/evidence/runtime-identity-build.json. Repeat the full phone probe. Gate 2 remains BLOCKED; production consumers of POSIX credentials, including spill ownership validation, need Android adaptation before enabling those paths.

V4 update checks passed: quick documentation 21/21, full documentation 43/43, and repository lint with the existing unused-disable warning. The Filebin ZIP and its contained APK were downloaded and hash-verified. No v4 Android instrumentation or successful phone result is claimed.

## User-reported JNI API success and executable comparison

The user's complete v4 JSON reports Node v24.22.1/android/arm64, SQLite/worker/ESM/crypto/native-lock success and successful DNS/TLS. Node PID matches native Android PID; UID 10750 is non-root. Node getuid is unavailable as expected. The exact user-provided result and its limits are in `apps/android/evidence/phone-v4-user-result.json`. This is manual user-reported phone evidence, not developer-controlled ADB instrumentation. Android 11 is still unconfirmed by ADB. Harness was explicitly not started.

The reported execPath is `/system/bin/app_process64`; childNodeLaunch remains not-tested. The existing Harness SDK and managed runner use process.execPath, so JNI API success alone cannot establish process launch compatibility. V5 (`0.1.4-executable-proof`, code 5) packages the unchanged original Node UNIX entry as an inspected PIE, with Android-installer extraction into nativeLibraryDir. The app rejects a missing/writable executable and runs only the fixed APK-owned comparison scripts. No native executable is copied into writable app files. The second native button displays the fixed invocation before running; it does not prove Harness tool authorization.

The executable comparison runs the same API probe and launches one real fixed child Node program. It checks actual stdout/exit and separate parent/child PID/UID from each process's own kernel status. Native supervision checks the Node parent and app UID. A single-use process owner synchronizes startup/cancellation, signals TERM then KILL on bounded deadlines, waits for exit, closes streams and preserves interruption. Android OS process-kill/background behavior remains untested; these are diagnostic lifecycle controls, not a sandbox or general command provider.

Eleven host API/process-owner tests and ten ELF/metadata tests passed. The actual Linux parent/child program ran; JVM tests observed exit status, live-child cleanup, interrupted cleanup and cancellation before launch. These do not establish Android execution. Final APK/test assembly and Android lint passed: 79 tasks in 51s. Signatures, alignment, packaged executable interpreter/entry/dependencies and required assets were inspected. Evidence is `apps/android/evidence/runtime-executable-build.json`. Both Android test classes are present and separately selectable; device instrumentation remains unrun.

The genuine public Harness SDK initialized the shipped sdk-minimal profile on Linux, created persistent session state, closed the runtime, initialized a new runtime and resumed the same nondefault working directory. A real session.v4.jsonl file was hashed. No model request, fake model server or replacement agent loop was used. The reproducible host reference and results are `apps/android/tests/host-profile-reference.mjs` and `apps/android/evidence/host-profile-reference.json`. This is not Android Harness startup or storage acceptance.

The completed phone comparison and selected next experiment are recorded below. Before Android Harness profile boot, adapt the native lock selector, unavailable UID ownership checks and desktop shell/PTY composition. Gate 2 and later gates remain unpassed; no Termux/root support or original frontend changes were introduced.

V5 validation passed: quick documentation 21/21, full documentation 43/43 and repository lint with the existing unused-disable warning. The Filebin archive and contained APK were downloaded and hash-verified. At APK delivery, executable/child execution was pending; the phone result below now establishes that bounded proof. Android Harness profile results remain unverified.

## V5 physical-phone runtime comparison

Status: fixed Node API and packaged-child proof VERIFIED by user-reported manual testing on Redmi Note 8 Pro, Android 11/API 30; developer-controlled phone instrumentation remains NOT STARTED. Both JNI and installed-executable results report Node v24.22.1/android/arm64, native locking, SQLite, workers, ESM, crypto and DNS/TLS passing. The installed Node child returned real JSON stdout and exit zero; kernel identity matches the non-root supervisor UID and the executable is reported non-writable. The [phone record](apps/android/evidence/phone-v5-user-results.json) preserves results and explicit redaction/attribution limits.

The child emitted an unused processor-specific DT-entry linker warning; it was nonfatal in this run and is retained in evidence. It is not evidence of compatibility on other Android versions. The [architecture recommendation](ANDROID_ARCHITECTURE.md) selects the packaged executable for the next bounded original-profile experiment because it provides a real Node execPath and child launch. JNI remains a reference.

Phase 2 remains IN PROGRESS and Gate 2 remains BLOCKED: both phone results explicitly state harnessStarted false. Next engineering milestone: adapt Android lock selection, trusted ownership checks and the minimal profile's shell/PTY composition; then start the authentic profile on Android and verify durable session recovery plus an explicitly authorized harmless tool command. Optional Termux/root and original frontend changes remain outside this milestone.

## Developer-controlled emulator retry

Status: BLOCKED before instrumentation. A fresh official API 30 Google APIs x86_64 AVD ran with software acceleration, two guest cores, 4 GiB RAM and a 256 MiB heap. Android reached boot_completed and temporarily exposed package/settings services, then those services disappeared. Both real v5 runtime test-runner attempts failed APK installation with `Can't find service: package`; no Android assertion executed. Crash-buffer output includes DeadSystemException; the framework root cause is not established. This cannot negate or independently confirm the user's physical-phone result.

Commands used the selected emulator with `python3 apps/android/scripts/test_device.py --adb /workspace/android-sdk/platform-tools/adb --serial emulator-5554 --proof runtime --output /tmp/android-validation-jni-run1` and a second run into `/tmp/android-validation-jni-run2`; both exited 1 with BLOCKED evidence. The [emulator record](apps/android/evidence/emulator-v5-validation.json) retains actual properties, APK digests, failure output, readiness observations and local log fingerprints. Its x86_64/ARM-translation configuration is separate from native ARM64 phone testing. No test assertions, OS security controls or ABI properties were weakened.

This evidence/documentation update passed quick documentation checks (21/21) and full doc-sync (43/43, 216.58s). Repository lint completed with the existing unused-disable warning in experimental client-ui-cot-translation; no new lint errors were reported. No application source or historical baseline evidence was changed by this update.
