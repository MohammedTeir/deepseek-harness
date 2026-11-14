# Android port status

## Summary

Current snapshot (2026-11-14): Phase 0 is VERIFIED; Gate 1 is ACCEPTED; Gate 2 is ACCEPTED only within its documented bounded local-engine scope. Gate 3 remains IN PROGRESS: fixed process/shell/PTY, original terminal/native approval and the APK #8 timeout/cancellation/session-recovery lifecycle scope have user-reported Android 11/API 30 ARM64 evidence, but API 29/recent-device coverage, broader lifecycle/process-tree behavior and general terminal support remain unverified. Phase 3A / Gate 4 is IN PROGRESS: original web assets are packaged and the original Web Profile has bounded Linux-host bootstrap/composition evidence, but no Android Web Runtime Image, Android WebView-to-backend integration, original chat UI, streamed model response or Android device boot proof has been accepted. Gates 5 and 6 and Phases 4–7 remain incomplete. Historical milestone entries below retain their original status and failures; later dated sections supersede stale next-step wording.

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

## Original lock entry and no-execution profile checkpoint

Status: IMPLEMENTED, with host checks and APK build VERIFIED; updated Android loader execution remains NOT STARTED. V6 (0.1.5-session-lock-loader, version code 6) adds Android ARM64 selection to the original lazy flock entry. Both fixed API probes now exercise that public entry instead of directly loading the C binding. Acquisition, contention rejection and reacquisition remain required; nativeLockProvider identifies upstream-system-entry. No Node or C binding rebuild/replacement was needed, and no environment-variable binary override or lock-success fallback was added. The [v6 build record](apps/android/evidence/runtime-session-lock-build.json) records actual artifacts and inspected assets.

The original sdk-minimal profile plus the no-execution overlay starts and recovers a durable session on Linux using the existing public SDK. The [host record](apps/android/evidence/host-no-execution-profile-reference.json) reports a nondefault working-directory recovery after full runtime restart, without a model request. The overlay disables subprocess, PTY, persistent shell and image-file tools; spill-local is absent, so its unqualified ownership cleanup is not enabled. This is not an Android profile result, command provider or security sandbox. See [runtime scope](ANDROID_RUNTIME_GUIDE.md#original-lock-selector-and-bounded-profile).

Executed checks: original native entry TypeScript build/typecheck; 27 native flock tests, including four clearly labeled host policy tests with simulated Android metadata; 19 session lease consumer tests; 11 Android host tests; and 10 ELF/metadata tests passed. APK/test assembly and Android lint passed in 23s, 79 tasks. Kotlin daemon startup failed and Gradle's compiler fallback completed the successful build. Actual APK signatures, ZIP/ELF alignment, native dependencies and byte equality of the compiled original-entry asset were inspected. The phone's earlier v5 result remains valid only for that older direct-binding probe.

Gate 2 remains BLOCKED. Next: run v6's two fixed probes on the phone, then package the real Harness profile/dependency closure for Android and verify profile readiness and persistent session recovery. A trusted approved command provider and its denial tests remain required before Gate 2 acceptance; neither the host reference nor this APK contains that proof. No original frontend redesign, optional Termux/root, unrelated workflow changes, merge or release was introduced.

Upstream patch inventory for this checkpoint: `native/system/packages/entry/src/flock.ts` adds only the lazy Android ARM64 carrier branch; its English/Chinese README, support matrix and native test scripts describe and cover the addition. The original C binding, agent loop, session format and desktop/browser frontend remain unchanged. The APK asset is the compiler output of that same original entry, not an independently maintained JavaScript replacement.

Checkpoint validation passed: quick documentation 21/21, full doc-sync 43/43, aggregate build checks 2/2 and repository lint with the existing experimental client-ui-cot-translation unused-disable warning. The initial quick documentation run found an out-of-sync bilingual README record; both language edits were retained, the pairing record was regenerated and validation then passed. The uploaded Filebin ZIP was downloaded and both archive and contained APK SHA-256 digests matched. No on-device result for v6 is claimed.

## V6 selected-mode phone evidence

Status: VERIFIED by user-reported manual testing of the packaged-executable mode on Redmi Note 8 Pro, Android 11/API 30. The [v6 result](apps/android/evidence/phone-v6-user-result.json) reports nativeLockProvider upstream-system-entry, lock success, actual child exit zero, non-root kernel identity, non-writable installed executable and all original API checks passing. No new JNI result was supplied. Harness was explicitly not started. The nonfatal linker warning and install-path redaction remain recorded. This is not developer-controlled instrumentation.

## V7 original profile/session carrier

Status: IMPLEMENTED; host relocation, source build and APK packaging VERIFIED. Android profile execution remains NOT STARTED. V7 (0.1.6-original-profile, code 7) adds a third native diagnostic action that runs the original sdk-minimal profile through its public SDK, creates a real JSONL session, closes the runtime, starts another runtime and recovers the nondefault working directory. A successful subsequent invocation also recovers the prior saved session checkpoint. The controller records actual results; modelRequestExecuted, approvedCommandExecuted, appRestartVerified and gate2Passed remain false. An app restart is not inferred from Node runtime restart or repeated invocation.

The image packer traces successful reads of the original no-execution profile, preserves interpreted bytes and contained module links, and rejects unknown native dependencies. Its 1,336 files, 844 links and 647 inspected package manifests form a bounded startup/session image, not a complete dependency distribution or plugin/model qualification. Two Linux native bindings are excluded from the Android image. The [relocated host proof](apps/android/evidence/host-relocated-profile-reference.json) runs both the image and its state outside the checkout with only PATH/TMPDIR/LANG inherited and the original published Linux bindings supplied solely to the host validation tree. Both runtime restart and prior-invocation recovery passed.

The first packing attempt rejected node-addon-require-builtin 0.1.9 as a second native dependency. Its checksum-pinned original C++ source now cross-compiles unchanged for Android ARM64/API 29 using NDK 28.2 and integrity-verified node-addon-api 8.9.0 headers. A private Android optional-package carrier loads only the installed libharness_require_builtin.so; the original loader validates its exported product/backend/ABI. No Linux binding, native cache extraction, internal-offset override or replacement engine is used on Android. Private Node runtime probes remain a critical device compatibility question until v7 actually runs.

Executed checks: 13 host tests and 17 ELF/metadata/archive tests passed, including real delayed child shutdown, path escape rejection, symlink-cycle cleanup without deleting an outside file, credential exclusion and rejection of modified/native image bytes. Normal final APK/test assembly and Android lint passed in 14s, 79 tasks. Signatures, APK/ELF alignment, Android-only dependencies, additional licenses, exact profile image and compiled original flock asset were inspected; see the [v7 build record](apps/android/evidence/runtime-profile-build.json). No Android device is attached. The third button's rendered layout and interaction remain uninspected on Android; phone testing must exercise start, success/error and cancellation.

Gate 2 remains BLOCKED. Next: execute the third diagnostic on Android ARM64 and retain original-loader readiness, session recovery and failure telemetry. After that proof passes, implement a trusted approved-command provider and denial tests. Provider requests, original Web UI integration, PTY, background/process-death recovery, general plugins, optional Termux/root and later gates remain unverified. No unrelated workflow, merge or release was changed.

V7 repository checks passed: quick documentation 21/21, full doc-sync 43/43 and repository lint with the existing experimental client-ui-cot-translation unused-disable warning. The first quick documentation run correctly rejected third-party header README files under generated checkout output; the header archive now extracts outside the checkout, and verification passed without changing documentation validation or baseline evidence. A stale host qualification marker is rejected before normal APK preparation. The final Filebin archive and contained APK were downloaded and hash-verified. Native button rendering and Android execution remain pending physical-device testing; no UI acceptance or designer review is claimed.

Guarded preparation also passed normal APK/test assembly and Android lint (4s, 79 tasks). App-private image/state roots are canonicalized before alias checks and SDK directory comparisons to accommodate Android data-directory aliases; final artifact digests are recorded separately. Aggregate build checks passed 2/2, and the selected profile class remains device-unrun. Source fingerprints and the successful isolated host qualification marker are recorded in the build evidence; no partial/failed host packing run can satisfy normal preparation.

## V7 physical startup and session-recovery failure

Status: original startup IMPLEMENTED with partial user-reported evidence; session recovery FAILED. The [phone transcript](apps/android/evidence/phone-v7-session-recovery-failure.json) reports original-profile exit 1 at session-recovery, with harnessStarted true and the new session absent. V7 reaches that stage only after its internal-loader checks and both SDK initialize calls complete. This supports local startup on the previously reported phone; it does not prove persistence or establish the Android filesystem failure. The current transcript contains no independent device properties or phone APK digest. The unused libc++ DT-entry warning precedes successful initialization and is not identified as the cause.

## V8 confirmed shutdown and storage diagnostics

Status: IMPLEMENTED, with host qualification and APK build evidence; Android cause and recovery remain BLOCKED. V8 (0.1.7-session-diagnostics, code 8) explicitly requires sessionPersistence before its SDK server activates and requires a successful original SDK shutdown reply before close/restart, validates the live directory, probes actual directory/file fsync and exclusive hardlink publication, and records bounded directory/Dirent/stat observations. No session is fabricated, manually repaired or substituted, and recovery assertions remain required. The prior shortened EOF window returns to the SDK's six-second default; the global diagnostic deadline remains bounded.

A real non-root Linux failure test made an original JSONL file read-only. Plain SDK close resolved while retaining an EACCES shutdown note; confirmed shutdown rejected with the actual permission error. The [host failure record](apps/android/evidence/host-sdk-shutdown-failure.json) demonstrates diagnostic suppression, not the Android root cause. A new read-only SDK runtimeStderr method exposes the already-retained stderr/shutdown notes without changing close, persistence or wire semantics. The Android controller retains these notes after cleanup and preserves the primary failure if cleanup also fails. Its keyless profile and scrubbed environment remain unchanged.

Executed host checks: 16 Android host tests, 17 ELF/archive tests and 17 focused SDK stderr/disposal tests passed. The original profile with explicit shutdown acknowledgement and actual storage primitives passes isolated Linux relocation, runtime restart and prior-invocation recovery; see the [confirmed host proof](apps/android/evidence/host-confirmed-session-reference.json). Source/SDK builds and APK evidence are recorded separately. These checks do not repair or reproduce the phone's missing-session failure.

Gate 2 remains BLOCKED. Run v8's third action and retain the complete result, especially storageStage, error, persistenceDiagnostics.runtimeStderr, shutdownAcknowledgements and session inventories. Use those executed Android observations to choose a platform/storage correction; do not replace exclusive publication, skip fsync, weaken session recovery or advance to an approved-command claim while this failure remains unresolved.

The readiness dependency is an Android qualification overlay, not a change to generic SDK launch or the agent loop. It makes persistence mandatory for this test instead of relying on an optional service lookup. Linux composition and recovery pass with that dependency; it is not identified as the phone's root cause. The SDK patch inventory adds only the read-only diagnostic accessor and its documentation/test; normal close and the JSONL backend remain unchanged.

Final v8 validation: debug APK, instrumentation APK and Android lint built successfully (79 tasks, 16 seconds); documentation quick checks 21/21 and full checks 43/43 passed, aggregate TypeScript checks 2/2 passed, and root lint passed with one existing unused-disable warning. The uploaded ZIP was downloaded and its archive and inner APK SHA-256 values matched the local build. Android v8 execution remains NOT YET VERIFIED.

## V8 physical hardlink failure

Status: BLOCKED, with [user-reported Android evidence](apps/android/evidence/phone-v8-hardlink-failure.json). Original Harness initializes on ARM64 Node v24.22.1, but the storage preflight fails at exclusive hardlink publication with EACCES (link, errno -13) inside app-private files. Directory/file sync precede this operation without a reported failure. The retained previous session directories contain only lock files in the reported inventory. This establishes an incompatible publication primitive on this phone; it does not independently establish SELinux as the denying layer or directly replay the earlier v7 write failure.

The original JSONL materialization and generation publication both use hardlinks to preserve existing committed destinations. Plain rename is not an acceptable substitute because it overwrites them. The next engineering milestone is a narrow Android atomic no-replace publication proof (candidate: renameat2 with RENAME_NOREPLACE), including filesystem/kernel availability, existing-destination preservation, concurrent publishers, sync ordering and explicit unsupported errors. Only after that proof should a platform adapter update both publication paths and rerun authentic restart/recovery. No root, broad storage permission or permission-check bypass is justified by this result. Gate 2 remains BLOCKED; no replacement APK or successful Android recovery is claimed.

## Isolated atomic persistence compatibility proof

Status: IN PROGRESS; production integration and physical-device verification BLOCKED. The [owning review](apps/android/atomic-proof/ATOMIC_PERSISTENCE_REVIEW.md) inventories five production hardlink publication callers, compares alternatives and documents Android/Linux evidence. AOSP prohibits untrusted-app hardlinks, consistent with the phone failure; vendor AVC evidence is still unavailable. No original persistence package or session format has been changed.

APK #1 uses a separate atomic-proof app package and fixed NDK API-29 ARM64 executable. Its native suite tests no-replace publication, collision identity, independent-process concurrency and observation, controlled SIGKILL boundaries, sync/cleanup/error handling and app identity. All host results are separate from Android acceptance. Physical A–F results, production adapter integration, APK #2, authentic recovery and trusted command execution remain unverified. Gate 2 stays BLOCKED.

APK #1 cross-build/signing/alignment/ELF/license inspection is VERIFIED; [build evidence](apps/android/evidence/atomic-poc-apk1-build.json) records the 3,116,217-byte debug APK. [Delivery evidence](apps/android/evidence/atomic-poc-apk1-delivery.json) confirms upload followed by download and matching archive/main/test APK hashes. This isolated package omits Node by design; the existing runtime app and its data remain intact.

[Executed validation](apps/android/evidence/atomic-poc-validation.json): 25 Android host/native/checker tests, 17 packaging regressions, 27 original native lock/policy tests and 399 original persistence/filesystem/attachment/SDK tests passed; three unchanged Windows-only tests skipped on Linux. APK/test assembly and Android lint passed (77 tasks, 3 seconds); quick documentation passed 21/21 and repository lint passed with its existing warning. [Native Linux results](apps/android/evidence/atomic-poc-host-native.json) retain actual 128 publisher PIDs, 16 independent observer results and 10 killed-child observations. They are not Android evidence.

[Physical checkpoint](apps/android/evidence/atomic-poc-physical-checkpoint.json): A–F BLOCKED. adb devices reported no attached device; the selected-device runner rejected an unavailable serial with exit 1 before any assertion. The physical tester must install the separate APK #1 and return complete JSON from two runs. APK #2, production persistence adapter, authentic session recovery and the approved-command milestone have not been implemented or represented as passing.

Full documentation verification passed 43/43 in 177.43 seconds. Additional official Android 10 source review finds renameat2 in the common seccomp whitelist despite the Bionic wrapper requiring API 30; vendor policy and actual API-29 execution remain unverified. The native/API-29 build has no imported renameat2 wrapper. Physical-device acceptance still blocks production integration.

The implementation push passed all five incremental TypeScript checks (Host Typert, host/client compilers and host/client aggregates). The committed source fingerprints, local inspected APK and downloaded APK bytes match. Production publication remains unchanged; physical A–F review is the next blocking milestone.

## APK #1 physical checkpoint accepted

Status: VERIFIED for the fixed native proof on one user-tested Redmi Note 8 Pro, Android 11/API 30, native ARM64, kernel 4.14.186 and ordinary UID 10752. Both complete [phone results](apps/android/evidence/atomic-poc-physical-review.json) pass the unchanged validator and match the delivered APK/native digests. A–F pass in two distinct runs: 256 competing publishers, 32 independent observers and 20 controlled kills in total, with EEXIST identity protection, file/directory sync and failure propagation. The physical results are user-reported, not developer-controlled instrumentation.

The SELinux context is untrusted_app; reading the enforcement flag is denied and no matching AVC is captured. Filesystem magic 0xef53 identifies the EXT family; no separate mount inspection or power-loss qualification is claimed. API 29, newer releases, cross-directory staging and retained-source aliases remain unverified. The old unavailable-device record remains historical evidence. This accepts only the narrow mechanism checkpoint: original Harness persistence, native-addon integration, APK #2 and trusted commands still require their own proof. Gate 2 remains BLOCKED.

## APK #2 original persistence integration

Status: IMPLEMENTED with host validation and APK inspection; device recovery BLOCKED. The [adapter reference](apps/android/runtime/ATOMIC_PERSISTENCE_ADAPTER.md) maps the shared Node-API publication binding, both original JSONL paths and exact acceptance steps. Original non-Android linking, Windows publication, file/directory fsync, collision verification and historical generations remain intact. Android consumes staging; consumer regressions cover cleanup and failures after visible publication without deleting committed data. The original flock C binding is unchanged.

The profile preflight uses the production entry, requires EEXIST/inode/content protection and actual syncs, then exercises original profile/SDK session creation, acknowledged shutdown, runtime restart/recovery and second-invocation persistence. A rejected nonexistent-session recovery must leave the existing JSONL hashes unchanged. The installed APK/binding digests and a native Copy complete result action support phone evidence. App restart, active-write termination, power loss, provider requests and approved commands remain separate and unverified. Gate 2 stays BLOCKED.

APK #2 validation: [executed checks](apps/android/evidence/runtime-apk2-validation.json) record 10/10 workspace build gates including the original frontend, aggregate checks 2/2, 401 regressions passed with three Windows-only skips, 27 host/checker tests in two runs, 19 ELF/image guards, four publication-entry tests, 27 original lock tests and 31 native package tests. The real C/Node-API Linux reference covers 32 independent publishers. The original relocated profile passes runtime restart, prior-invocation recovery and JSONL integrity after a rejected resume. None is Android session evidence.

Normal APK/test assembly and Android lint passed (79 tasks, 6 seconds), with signature/alignment/dependency/notices/image checks in the [APK #2 build record](apps/android/evidence/runtime-atomic-persistence-build.json). [Delivery](apps/android/evidence/runtime-apk2-delivery.json) was uploaded, downloaded and verified; its ZIP intentionally contains one APK to avoid confusing the instrumentation companion with a second app. Copying diagnostic output is newly available, but Android rendering remains uninspected. Install this as an update to Harness runtime proof, not the small atomic proof app.

[Wider checks](apps/android/evidence/runtime-apk2-wider-checks.json) disclose the initial hygiene failure: three obsolete generated-only package directories were preserved outside the checkout, then constraints passed; four unchanged rescope sites fail identically in a detached baseline check. The complete native suite stops at a missing Linux Landlock launcher/musl toolchain; the relevant entry, publication, lock and packing checks execute separately. No baseline source or validator was changed to make these checks appear green. The config catalog was regenerated solely for the JSONL import's source-line offset; runtime configuration and session format did not change.

Final APK #2 documentation verification passes 43/43 in 169.01 seconds after the generated source-location correction. An additional guard regression rejects a changed atomic source paired with an old inspected binary. Historical V8 build evidence and Phase 0/1 baseline records match their committed bytes exactly. Device persistence acceptance is still pending; the next required action is two executions of the larger app's original-profile/session test with existing data preserved.

## APK #2 physical persistence acceptance

Status: VERIFIED within the [physical review's scope](apps/android/evidence/runtime-apk2-physical-review.json). Three complete phone reports match the delivered APK/publication-binding digests and pass the unchanged validator; runs two and three additionally pass --require-previous-invocation. Original SDK/profile startup, production no-replace publication, explicit shutdown replies, real JSONL, runtime restart recovery, nondefault directory state and integrity after rejected recovery are demonstrated on Android 11/API 30 ARM64 under UID 10751. Old failed-session directories remain; no app data was cleared or session file manually repaired.

The third result was supplied in response to the explicit manual force-stop/reopen instructions. Its raw appRestartVerified remains false because the controller does not instrument the Activity process; the manual scenario is attributed separately and is not proof of process death during a write or power loss. The original SDK close makes an additional best-effort shutdown request after the controller already received a successful explicit reply, producing the retained closed-input note with exit code 0. Two acknowledged replies per run and executed recovery pass independently; no error is filtered to obtain acceptance.

Gate 2 remains BLOCKED. The next milestone is one genuine registered Harness tool using its existing approval pipeline plus a native exact-request one-shot grant for a fixed harmless local command, with real stdout/stderr/exit and denied, changed and replayed requests. Model inference needs authorized credentials when available; original Web UI, general PTY, optional root/Termux and broader lifecycle/device qualification remain later work.

## Fixed command native components

Status: IN PROGRESS. The [command qualification reference](apps/android/execution/COMMAND_PROOF.md) describes an isolated native one-shot grant and fixed pwd process owner, with host policy/process tests and Android Java/lint checks. They are not yet reachable from the app or original tool pipeline; no new APK or Android command result is claimed. Trusted native approval UI, identity derivation, authenticated IPC, original Harness tool integration and physical-device execution remain required. Gate 2 stays BLOCKED.

## APK #3 original-tool/native approval qualification

Status: IMPLEMENTED with host integration and Android build checks; physical execution BLOCKED. The [command reference](apps/android/execution/COMMAND_PROOF.md) documents the genuine registry/executor/approval path, private native broker/UI, one-shot concurrent consumption, actual output and original command-event persistence/recovery. The host uses explicitly automated decisions and a real Linux subprocess; it does not verify Android IPC, rendering or human consent. Install the delivered update and return the full two-prompt phone result. Gate 2 remains BLOCKED.

## APK #3 physical command acceptance and Gate 2 review

Status: VERIFIED for the bounded local-engine criteria in the [Gate 2 review](ANDROID_GATE2_REVIEW.md). The user-reported Android 11 ARM64 result matches APK/native hashes and passes the unchanged validator: original profile/tool/approval, explicit Deny then Approve, one actual pwd process with stdout/stderr/exit, concurrent/replay/mutation denial and identical recovered original records. Raw gate2Passed remains false; the review decision is recorded separately. External model inference remains unverified without credentials.

Leaving the Activity during confirmation produced the intended cancellation message according to the tester. This is UI evidence only, not proof of native child termination or full background/lifecycle behavior. Retained nonfatal linker and SDK shutdown notes are explained in the owning review; historical failures remain untouched. The next milestone is Gate 3 process/shell/PTY qualification, with original UI, cross-UID isolation, device matrix and release acceptance still separate.

## Gate 3 process and PTY qualification

Status: IN PROGRESS; physical execution BLOCKED pending phone results. The [fixed native diagnostic](apps/android/execution/process-proof/PROCESS_CAPABILITY_PROOF.md) adds an explicitly authorized fifth test button. Host tests pass, Android assembly/lint and APK inspection pass, and the original seven native libraries remain unchanged. This is OS capability evidence collection, not a general shell provider or original terminal integration. Historical failures and Gate 2 review remain intact. See the separate APK #4 build and delivery records under apps/android/evidence.

## APK #4 physical process capability review

Status: VERIFIED for the selected-device fixed suite; overall Gate 3 remains IN PROGRESS. The [Gate 3 review](ANDROID_GATE3_REVIEW.md) accepts matching APK/native fingerprints, separate streams, stdin, nonzero exits, launch errors, TERM cancellation, timeout/KILL/reaping, cooperative descendant cleanup, fixed system-shell execution and PTY input/resize on Redmi Note 8 Pro / Android 11 API 30. The complete user-reported result is retained without changing gate3Passed=false. API 29/recent-device coverage, Activity/OS-death cleanup, general shell and original terminal integration remain unverified. Next: map the demonstrated capabilities into existing subprocess/terminal contracts with authorization preserved.

## Original subprocess adapter checkpoint

Status: IMPLEMENTED and host verified; physical execution BLOCKED pending APK #5. The [fixed adapter](apps/android/execution/SUBPROCESS_ADAPTER.md) mounts the original SubprocessRuntime service in the authentic profile and routes the existing approved pwd tool through its spawn/done/collected/waitForExit contract. Unsupported pipes, spill, custom environment, commands and interactive PTY fail closed. Native authorization and session format remain unchanged. Gate 3 remains IN PROGRESS; APK #4 phone evidence does not verify this new integration.

## APK #5 physical original-service acceptance

Status: VERIFIED for fixed pwd through the original SubprocessRuntime service on Redmi Note 8 Pro / Android 11 API 30 ARM64. The [physical review](apps/android/evidence/phone-subprocess-apk5-review.json) accepts the delivered APK/native fingerprints, original service marker, native Deny then Approve, one actual process, exact-request/replay rejection, genuine stdout/exit and identical recovered session records. The complete submitted report and historical failures are retained. Earlier host-only/pending-device statements describe the build checkpoint. Gate 3 remains IN PROGRESS; live PTY/original terminal, adapter cancellation on Android, API 29/recent devices and broader lifecycle remain unverified. No new APK is required for this acceptance.

## Original node-pty qualification checkpoint

Status: IMPLEMENTED and host tested; physical execution BLOCKED pending APK #6. The [original dependency experiment](apps/android/execution/NODE_PTY_QUALIFICATION.md) cross-builds unmodified node-pty C++ for API 29 ARM64 and reuses its original JavaScript through a narrow installed-library loader. The Android compile path uses forkpty directly, not the Apple spawn-helper. Real host source-addon tests cover input/resize, exit 7, SIGINT, TERM and deadline/KILL. Existing engine/tool proofs remain unchanged. Gate 3 stays IN PROGRESS; no original terminal backend or generic command provider is enabled.

## Original node-pty accepted; handle contract prototype

The [APK #6 phone review](ANDROID_GATE3_REVIEW.md) verifies original node-pty loading and all five fixed cases on Android 11 ARM64 with matching fingerprints. A [host-only SubprocessTerminalHandle prototype](apps/android/execution/PTY_HANDLE_QUALIFICATION.md) now passes the original strict type contract and real input/resize, exit/signal and concurrent cleanup tests. It is explicitly disabled on Android and is not shipped or registered as an agent tool. Gate 3 remains IN PROGRESS. Next: native-authorized allocation, original Agent/terminal ownership, foreground identity and rollback/cleanup proof, followed by a new device milestone. No APK #6 replacement or repeat is required to accept its submitted result.

## Original terminal registry checkpoint

The [fixed terminal registry qualification](apps/android/execution/TERMINAL_REGISTRY_QUALIFICATION.md) exercises the original profile, genuine Agent ownership, tool/approval pipeline, registry rollback and persisted history with real host PTY processes. Status: IMPLEMENTED with host verification; Android integration NOT STARTED. Automated host decisions are not native human approval. Android guards remain active and no APK changes are included. Gate 3 remains IN PROGRESS; next implement native-authorized allocation before a new physical-device checkpoint.

## Native terminal allocation grant checkpoint

The [native allocation policy](apps/android/execution/TERMINAL_ALLOCATION_AUTHORIZATION.md) is IMPLEMENTED with JVM tests and Android compile/lint. It binds the registry terminal/Agent and complete fixed request to the existing one-shot grant, rejects resource changes and preserves denial/expiry/replay handling. It is not wired to IPC, UI or runtime allocation. No new APK or device result is claimed. Gate 3 remains IN PROGRESS.

## Native broker and original approval relay checkpoint

The [broker integration reference](apps/android/execution/TERMINAL_BROKER_INTEGRATION.md) records the private native protocol, exact original-service approval adapter and host-only genuine profile/PTY test with an explicit native transport double. Android broker instrumentation is compiled, not executed. UI/runtime activation and full APK/device acceptance remain pending; the existing Android guards are retained. Gate 3 remains IN PROGRESS.

## APK #7 original terminal qualification

The [APK #7 reference](apps/android/execution/TERMINAL_ANDROID_PROOF.md) records the original registry/tool/approval path, authenticated native broker, human UI and fixed Android PTY factory. Host and relocated-profile tests and Android build/inspection pass. Physical execution is BLOCKED pending phone evidence. This is a fixed benign fixture, not general shell or the original Web UI. Gate 3 remains IN PROGRESS; preserve existing data when updating the single runtime app.

## APK #7 phone cleanup blocker

Physical execution reported `Terminal broker cleanup failed` without underlying details. Gate 3 remains BLOCKED for phone acceptance. The [terminal diagnosis](apps/android/execution/TERMINAL_ANDROID_PROOF.md#cleanup-failure-diagnosis) describes the listener shutdown change and preservation of the original qualification report. Device confirmation remains pending.

## APK #7 fixed terminal phone result

The [phone result review](apps/android/evidence/phone-apk7-terminal-result-review.json) records selected fields from the user-provided Redmi Note 8 Pro/API 30 report with a matching inspected APK hash. The bounded original terminal qualification is VERIFIED at user-reported physical-device evidence level: denial, one approved PTY, input/resize, exact-request/replay rejection and original history recovery across runtime restart. The previous broker cleanup failure did not recur in this report; its original cause is not conclusively established. Gate 3 remains IN PROGRESS, with cancellation/timeout through the original terminal integration and device coverage review still required. App restart, model requests, general shell support and malicious-plugin isolation are not established.

## Original terminal lifecycle qualification

The [APK #8 qualification](apps/android/execution/TERMINAL_LIFECYCLE_PROOF.md) adds bounded wait timeout and explicit cancellation through the original terminal service without widening the fixed native allocation. Host execution passes; physical-device execution is pending. Gate 3 remains IN PROGRESS.

## APK #8 phone lifecycle checkpoint

The [phone lifecycle review](apps/android/evidence/phone-apk8-lifecycle-result-review.json) records a matching APK and four native-library hashes on Redmi Note 8 Pro/API 30. The bounded original-terminal wait timeout and SIGINT cancellation are VERIFIED at user-reported physical-device evidence level: timeout kept the single child running, explicit cancellation ended it, repeated cancellation failed, owner activity drained and original records recovered across runtime restart. Controller exit 0 is distinct from the child signal exit with null exitCode. Historical warnings and failures remain retained. Gate 3 remains IN PROGRESS pending a consolidated acceptance review and remaining target-device coverage; no app-restart, general-shell or malicious-plugin isolation claim is added.

## Consolidated Gate 3 review

The [Gate 3 coverage review](apps/android/execution/GATE3_REVIEW.md) accepts the bounded user-reported API 30 subprocess, node-pty and original-terminal capabilities, including APK #8 lifecycle results. Gate 3 remains IN PROGRESS: Android 10/API 29 and recent-Android coverage are BLOCKED by unavailable target execution evidence. The next checkpoint reuses the existing diagnostic APK on those environments; no new general shell or frontend implementation is claimed.

## Original WebView asset inspection

The [original frontend asset inspection](apps/android/execution/ORIGINAL_WEB_ASSETS.md) builds and packages the existing web frontend in a restricted Android activity. Harness boot injection, client plugin bundles, authenticated transport, SPA routing and Android device verification remain incomplete. Gate 4 is IN PROGRESS; the APK does not yet demonstrate original screens or a connected backend.

## Original web host bootstrap checkpoint

The [original host bootstrap check](apps/android/execution/ORIGINAL_WEB_ASSETS.md#original-host-bootstrap-evidence) exercises the actual built web profile, its authenticated index, all advertised client batches and HTTP origin-denial behavior on Linux. Android web composition, appassets-to-runtime authentication, original screens and physical WebView verification remain NOT YET VERIFIED; Gate 4 remains IN PROGRESS.

## Isolated web-profile host trace

The [isolated trace](apps/android/evidence/original-web-profile-isolated-host-trace.json) separates the built Linux web-profile process and its recognized descendants from the Vitest parent. Its limitations and the remaining Android dependency and authenticated transport work are in the [web asset reference](apps/android/execution/ORIGINAL_WEB_ASSETS.md#original-host-bootstrap-evidence). Gate 4 remains IN PROGRESS.

## Bounded web-profile host experiment

The original `web` profile starts on Linux with six explicitly disabled platform rows and still provides its authenticated boot graph and client batches. The [host-only experiment](apps/android/execution/ORIGINAL_WEB_ASSETS.md#bounded-host-composition-experiment) records the actual rows, an active client entry whose provider is disabled, origin denials and remaining security limits. This fixture cannot establish Android startup or enforce a general execution policy. Gate 4 remains IN PROGRESS.


## Current checkpoint — 2026-11-14 (supersedes earlier next-step snapshots)

Development HEAD reviewed: `2c7b6cb12010e6291b7c5a6a1fc0af51664617cb`.

### Gate 3 / Phase 3

- APK #7 original terminal registry + native approval phone result is recorded in `apps/android/evidence/phone-apk7-terminal-result-review.json`.
- APK #8 lifecycle result is recorded in `apps/android/evidence/phone-apk8-lifecycle-result-review.json`; its accepted scope is the submitted timeout/cancellation/process-cleanup/session-recovery scenario on the reported Redmi Note 8 Pro, Android 11/API 30/ARM64.
- These are user-submitted physical-device results reviewed and normalized in-repository, not developer-controlled ADB runs or broad device certification.
- Gate 3 remains IN PROGRESS. Outstanding work includes API 29 and a recent Android target, service/Activity/process-death and orphan-descendant coverage, resource/backpressure limits, and an explicit supported-shell/capability contract. A fixed fixture or the current PTY qualification does not prove arbitrary shell support.

### Gate 4 / Phase 3A

- Original Vite frontend assets are built and packaged for restricted static inspection; see [asset evidence](apps/android/evidence/original-web-assets-build.json) and [inspection notes](apps/android/execution/ORIGINAL_WEB_ASSETS.md).
- The original Web Profile has Linux-host bootstrap and bounded-composition evidence: [host boot](apps/android/evidence/original-web-host-boot.json), [bounded host result](apps/android/evidence/original-web-bounded-host.json), and [isolated trace](apps/android/evidence/original-web-profile-isolated-host-trace.json).
- The host composition disabled six platform-sensitive provider rows. The client graph still exposed an active `ui-open-in-app` entry while its provider was disabled; UI capability-state handling remains an explicit issue.
- The trace counts only a limited set of successful absolute `openat` reads and retains a test observer. It is not dependency-closure proof. The observed Linux native addon must not be packaged for Android.
- The current `sdk-minimal` image is not a valid ready-made Web Runtime Image: the web profile requires additional runtime/frontend/configuration assets, while test fixtures and Linux-only native artifacts must be excluded.
- No Android Web Runtime Image, authentic Android Web Profile startup, connected original UI, secure WebView/backend transport, SPA routing, streaming chat, or model request has been verified. Gate 4 remains IN PROGRESS.

### Immediate Gate 4 execution order

1. Expand runtime dependency observation and static dependency analysis to include relative and absolute file access, `openat/openat2`, metadata/stat/access calls, directory enumeration, symlinks/realpath, dynamic imports, `dlopen`/native addon loading, child processes, configuration and runtime-generated paths. Record trace blind spots; never call a partial trace complete.
2. Separate actual Web Profile runtime dependencies from test runner, observer, fixture, development and Linux-only artifacts.
3. Define a narrow Android ARM64/Bionic packaging allowlist and explicit denylist; validate every native ELF dependency, ABI, linkage and license. Do not loosen the packager globally.
4. Build a deterministic Android Web Runtime Image with a content/hash manifest and reproducible validation.
5. Start the authentic original Web Profile under embedded Android Node and verify boot graph, client batches and provider capability state on a physical Android device.
6. Design and test authenticated WebView-to-runtime HTTP and WebSocket transport, preserving launch-token/cookie and Host/Origin denial properties. Do not enable broad WebView network access or expose credentials to JavaScript.
7. Verify the original UI, SPA navigation, streamed conversation, session recovery and one native-approved tool operation end-to-end on Android.

### Branch and change boundary

`feature/android-port` is the implementation/evidence branch. `master` contains the living planning documents only. The branches are currently divergent; this documentation refresh does not merge them, create a PR, publish a release, or change implementation code.