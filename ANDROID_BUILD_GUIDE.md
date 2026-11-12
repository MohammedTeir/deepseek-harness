# Phase 1 audit reproduction

## Summary

This branch contains audit evidence and a bounded Phase 2 native runtime proof. No standalone Harness agent APK has been verified.

## Prerequisites and commands

Use the checked-out fork and its pinned Node/pnpm versions. Installed dependencies must match `pnpm-lock.yaml`; do not refresh the lockfile. The evidence collector requires Python 3, PyYAML and GNU readelf. Run `python3 audit/android/collect.py` from the repository root to reconstruct the locked graph and installed-payload inventory. It reads manifests and binary headers without running dependency install hooks and fails on unresolved graph targets or ELF-read errors. Installed payload availability varies by host; the checked-in snapshot states this host's coverage.

Run `pnpm run build:web` to compile the original frontend after the repository's built workspace artifacts are available. This verifies the host frontend build only. `apps/web/dist` is generated output and is not committed. Record node/pnpm versions, lock digest and command result in [status](ANDROID_PORT_STATUS.md).

Registry metadata for noninstalled packages and official-platform excerpts are dated investigation evidence, not a silently refreshed source of executable code. Re-fetch their recorded URLs and compare `dist.integrity` against the lockfile before updating those records. No Android SDK/NDK install, signing or packaging step is needed for this documentation phase.

## Runtime proof build

Use Java 21, Android SDK/platform/build-tools 36, NDK 28.2.13676358 and CMake 3.22.1. Set `ANDROID_HOME` and read the [runtime experiment](ANDROID_RUNTIME_GUIDE.md). The wrapper pins Gradle 8.13 with a distribution checksum.

Run the Node source cross-build and `bash apps/android/runtime/build-system-addon.sh` with the documented environment variables. Once they succeed, run `python3 apps/android/scripts/package_node.py --build "$ANDROID_NODE_BUILD_DIR" --ndk "$ANDROID_NDK_HOME"`, then `./apps/android/gradlew -p apps/android :app:assembleDebug :app:assembleDebugAndroidTest`. The real source build, inspection/staging and normal APK assembly passed; detailed evidence is in `apps/android/evidence/runtime-apk-build.json`. The package is `ai.deepseek.harness.android.runtimepoc`; it supplies native diagnostic controls only and does not replace the original frontend.

Code-only validation used `:app:compileDebugKotlin :app:externalNativeBuildDebug -x :app:prepareRuntimeAssets`; that bypass is limited to compiler checks and cannot produce runtime acceptance evidence. Normal APK preparation requires inspected runtime bytes. Never publish a prototype lacking its genuine runtime as a working Harness app.

## Test signing and packaging fixture

Both modules use an ignored `.local/debug.keystore` under `apps/android` instead of a read-only home directory. This is disposable debug signing only. Create a standard Android debug keystore there with Java keytool before assembling APKs; keep production signing separate and never commit the key. The first fixture build reached signing and failed because the home directory was read-only; a local debug key resolved that failure.

The separate `:packaging-proof` module contains two tiny original C fixtures, not Node or Harness: one calls real UID/PID/page-size APIs through JNI; the other calls the same OS APIs as a packaged executable. Its APK requests installer extraction of native libraries and rejects an executable reported writable by the app. `:packaging-proof:assembleDebug :packaging-proof:assembleDebugAndroidTest` built both APKs. This fixture does not bypass the runtime module's requirement for genuine inspected Node bytes, and its results cannot pass the Harness/runtime gates.

## Phone test evidence

The device runner is `apps/android/scripts/test_device.py`. From the repository root, select the intended USB-debugging device with `--serial`, choose `--proof packaging` or `--proof runtime`, and supply a new directory with `--output`. `--adb` accepts the SDK platform-tools executable if it is absent from PATH. The runner installs the corresponding debug and instrumentation APKs from their Gradle output directories, then runs only that proof package's tests. It removes the previous runtime-probe result JSON to prevent stale evidence; it does not wipe the package's data or collect device-wide logs.

The output directory contains device API/ABI, kernel architecture, page size, native-bridge properties, APK digests, installation output and instrumentation output. Runtime tests also retrieve their fixed API-result JSON when available, including after a failing assertion. A failed, incomplete, zero-test or wrong-count run cannot report VERIFIED. This status applies only to the selected proof; `harnessVerified` remains false. Missing hardware was exercised and reports BLOCKED with a nonzero exit. Successful phone execution remains the phone tester's verification task.

The current runtime artifacts are `apps/android/app/build/outputs/apk/debug/app-debug.apk` and `apps/android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk`. Both passed signature and alignment checks. The current version is `0.1.7-session-diagnostics`, code 8, installable over earlier proofs with the same debug key. The original JNI button remains. The second button, Run packaged Node + child probe, asks to run a fixed diagnostic invocation; approve Run once and retain its full JSON or failure. The user reports both v5 modes passing on Android 11/API 30. V6's updated original flock-entry path remains untested on Android; require nativeLockProvider upstream-system-entry in both results. Formal acceptance still requires instrumentation and separate Harness/profile/session/tool tests.

Shared Java/Kotlin license assets live under `apps/android/licenses/third-party` and enter the main and instrumentation APKs of both modules. Apache 2.0, the original JUnit license and the original Hamcrest BSD text accompany the dependency notices. Runtime Node/NDK/flock license records remain separate. Artifact inspection verified the shared license bytes inside all four APKs.

The addon cross-build now requires the completed shared Node library and links the original binding explicitly against it. Re-run `build-system-addon.sh`, the packager, then normal Gradle assembly. Packaging rejects an addon missing DT_NEEDED `libnode.so`, and preparation rejects old metadata even when old byte hashes still match. The v3 source build, staging and normal APK assembly passed; Android loading remains the phone tester's verification task.

V5 preparation additionally requires the inspected output of `bash apps/android/runtime/build-node-executable.sh` before running the packager. Normal APK assembly passed with the executable, extra probe scripts and both instrumentation classes. Native libraries are compressed in the APK and extracted by the Android installer; the app verifies its executable is not writable. This explains the smaller APK compared with earlier uncompressed-library builds. It is not a writable-private-directory execution arrangement.

The device runner accepts `--proof executable` for the new class, `--proof runtime` for the original JNI class, and `--proof packaging` for the separate OS fixture. Each runtime proof selects one explicit test class and retains its own private result/stderr directory, preventing the other class or a zero-test run from reporting success. V5 emulator runtime attempts failed during installation because Android's package service disappeared; no instrumentation executed. V6 device instrumentation remains unrun.

V6 runtime asset preparation first builds the original native/system TypeScript entry using the host pnpm toolchain, then copies its exact emitted flock.js bytes as harness-flock.mjs. Both runtime services copy that fixed asset and the probes call its public lock entry; no independent replacement lock wrapper is packaged. The existing build prerequisites therefore include the installed native workspace compiler dependencies. Normal APK/test assembly and Android lint passed with this preparation enabled. The no-execution original-profile reference is a host qualification step and is not yet included in the diagnostic APK.

## V7 original-profile prerequisites

Build workspace JavaScript artifacts before capturing the original profile. This cloud qualification uses Linux x86_64, strace, Node 24.22.1, the existing SDK/native host bindings and the previously completed Android Node build. The require-builtin source checkout must match `apps/android/runtime/require-builtin-source.json`; the node-addon-api 8.9.0 archive must match its SHA-512 integrity. The build script verifies both inputs, keeps third-party headers outside the checkout and executes no package install hook. The exact external revision is recorded in the APK's runtime/require-builtin-build.json; no source offset patch is applied.

Executed build commands, with ANDROID_NDK_HOME and ANDROID_NODE_BUILD_DIR set as in the runtime build, are:

```sh
python3 apps/android/runtime/build_require_builtin.py /workspace/android-node/require-builtin-source /workspace/android-node/node-addon-api-8.9.0.tgz
python3 apps/android/scripts/package_node.py --build /workspace/android-node --ndk /workspace/android-sdk/ndk/28.2.13676358
python3 apps/android/scripts/package_profile.py apps/android/runtime/out/profile-v7
```

The image output must be a new directory; archive the previous generated output before repeating it. The packer validates the resulting original profile and repeated session recovery from an independent temporary tree. Normal Gradle preparation refuses changed image inputs, missing/stale host relocation qualification or missing native metadata and includes the new library and notices. The successful final Gradle run used in-process Kotlin compilation with no runtime-asset exclusion.

Install v7 over the previous debug package with the same key. Run the third action, Run original Harness profile + session recovery, and retain the entire JSON or BLOCKED text. A passing result must identify the original SDK server, N-API v9 loader, actual Android identity, harnessStarted and sessionRecoveredAcrossRuntimeRestart. Repeat the action to test previousRunSessionRecovered. It does not test approved commands or model requests. The selected-device runner also accepts `--proof profile`; its one explicit ProfileProbeTest remains unrun here.

V8 uses the same third action with confirmed-shutdown/storage diagnostics. Build the additive SDK diagnostic API before recapturing the image; the executed commands are `pnpm exec tsc -b packages/sdk/client` and `pnpm exec tsdown --config-loader native --filter @deepseek-ai/dsh-sdk-client`. Then generate a fresh profile image as above and assemble normally. Preserve earlier phone/session evidence; do not clear application data to hide a recovery failure. The new APK must return real storage/shutdown observations or a BLOCKED result; successful Android recovery is not yet claimed.

## Isolated atomic proof APK #1

The separate atomic-proof module builds a fixed native syscall test and small Android host without Node, Harness image assets or production persistence changes. Use the [build/install tutorial](apps/android/atomic-proof/ATOMIC_PERSISTENCE_REVIEW.md#build-and-install-tutorial) and [inspected build record](apps/android/evidence/atomic-poc-apk1-build.json). Its package differs from the runtime proof and preserves that app's existing data. Native execution and UI behavior remain physical-device checks.
