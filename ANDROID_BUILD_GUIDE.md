# Phase 1 audit reproduction

## Summary

This branch contains audit evidence and a bounded Phase 2 native runtime proof. No standalone Harness agent APK has been verified.

## Prerequisites and commands

Use the checked-out fork and its pinned Node/pnpm versions. Installed dependencies must match `pnpm-lock.yaml`; do not refresh the lockfile. The evidence collector requires Python 3, PyYAML and GNU readelf. Run `python3 audit/android/collect.py` from the repository root to reconstruct the locked graph and installed-payload inventory. It reads manifests and binary headers without running dependency install hooks and fails on unresolved graph targets or ELF-read errors. Installed payload availability varies by host; the checked-in snapshot states this host's coverage.

Run `pnpm run build:web` to compile the original frontend after the repository's built workspace artifacts are available. This verifies the host frontend build only. `apps/web/dist` is generated output and is not committed. Record node/pnpm versions, lock digest and command result in [status](ANDROID_PORT_STATUS.md).

Registry metadata for noninstalled packages and official-platform excerpts are dated investigation evidence, not a silently refreshed source of executable code. Re-fetch their recorded URLs and compare `dist.integrity` against the lockfile before updating those records. No Android SDK/NDK install, signing or packaging step is needed for this documentation phase.

## Runtime proof build

Use Java 21, Android SDK/platform/build-tools 36, NDK 28.2.13676358 and CMake 3.22.1. Set `ANDROID_HOME` and read the [runtime experiment](ANDROID_RUNTIME_GUIDE.md). The wrapper pins Gradle 8.13 with a distribution checksum.

Run the Node source cross-build and `bash apps/android/runtime/build-system-addon.sh` with the documented environment variables. Once they succeed, run `python3 apps/android/scripts/package_node.py --build "$ANDROID_NODE_BUILD_DIR" --ndk "$ANDROID_NDK_HOME"`, then `./apps/android/gradlew -p apps/android :app:assembleDebug :app:assembleDebugAndroidTest`. Runtime compilation/packaging are still in progress; these commands do not imply successful APK output. The package is `ai.deepseek.harness.android.runtimepoc`; it supplies native diagnostic controls only and does not replace the original frontend.

Code-only validation used `:app:compileDebugKotlin :app:externalNativeBuildDebug -x :app:prepareRuntimeAssets`; that bypass is limited to compiler checks and cannot produce runtime acceptance evidence. Normal APK preparation requires inspected runtime bytes. Never publish a prototype lacking its genuine runtime as a working Harness app.

## Test signing and packaging fixture

Both modules use an ignored `.local/debug.keystore` under `apps/android` instead of a read-only home directory. This is disposable debug signing only. Create a standard Android debug keystore there with Java keytool before assembling APKs; keep production signing separate and never commit the key. The first fixture build reached signing and failed because the home directory was read-only; a local debug key resolved that failure.

The separate `:packaging-proof` module contains two tiny original C fixtures, not Node or Harness: one calls real UID/PID/page-size APIs through JNI; the other calls the same OS APIs as a packaged executable. Its APK requests installer extraction of native libraries and rejects an executable reported writable by the app. `:packaging-proof:assembleDebug :packaging-proof:assembleDebugAndroidTest` built both APKs. This fixture does not bypass the runtime module's requirement for genuine inspected Node bytes, and its results cannot pass the Harness/runtime gates.
