# Android build guide

Contributor tutorial. This builds a prototype carrier, not the standalone agent port. Prerequisites: Node >=24.9 with development headers, project pnpm version, JDK17+, Gradle8.11.1, Android SDK35/build-tools35.0.0 and SDK licenses. Configure ANDROID_HOME and writable Gradle/Android user caches. No signing credentials are committed.

From the repository root, install locked dependencies and build original artifacts:

```sh
pnpm install --frozen-lockfile
pnpm run build:artifacts
pnpm run build:check
cd apps/android
./gradlew testDebugUnitTest lintDebug assembleDebug
```

The Gradle Sync task copies actual `apps/web/dist` into generated APK assets, excludes maps/experimental preview, and fails if index.html is missing. It does not create a replacement UI or boot manifest. Debug APK: `apps/android/app/build/outputs/apk/debug/app-debug.apk`. Only call it built after successful Gradle output. Install/launch and mobile navigation require a connected device; no physical-device result is inferred from packaging. The host currently shows the upstream boot failure because backend injections are unavailable.

The wrapper pins the Gradle distribution SHA256. This cloud environment used writable caches and explicit inherited proxy/CA configuration; Java downloads require Java proxy settings, not only HTTP_PROXY. The preinstalled JRE lacked javac, so a local JDK17 was supplied.

Release builds must keep debugging disabled and separately configure signing. No production release is published. Original MIT license is retained; font notices emitted by frontend build remain in assets. AndroidX, Kotlin, Node/native and full transitive license inventory remains required before public distribution.

See [status](ANDROID_PORT_STATUS.md) for actual commands/results and limitations; the workflow is additive at `.github/workflows/android-prototype.yml`.
