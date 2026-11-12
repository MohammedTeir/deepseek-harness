# Android port status

## Summary

Phase 0 is VERIFIED. The [Gate 1 review](ANDROID_GATE1_REVIEW.md) accepts the reviewed audit and a bounded Phase 2 runtime experiment. Phase 2 is IN PROGRESS; Gate 2 is not passed. A genuine Node ARM64 runtime API debug APK and its instrumentation APK build successfully. The user reported a failed phone probe with exit code 1. The original frontend and Harness engine are preserved. No successful Android API qualification, authentic profile readiness, session recovery or authorized tool result has been verified.

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
