# Android CI and signed releases

## CI build

`.github/workflows/android-ci.yml` builds the current Android app on Linux x86_64 for pull requests, pushes to `feature/android-port` or `master`, and manual runs. The reusable `.github/workflows/android-build.yml` installs the pinned Android SDK/NDK, builds Node 24.22.1 and the Android native add-ons from pinned inputs, creates and validates the host profile image, assembles the unsigned release APK, runs release unit tests, and runs Gradle lint. The unsigned release APK is retained as the `android-release-unsigned` Actions artifact.

The first clean run compiles Node from source and can take a while. The workflow now stores the prepared `apps/android/runtime/out` bundle in a GitHub Actions cache keyed by the workflow, lockfile, Android runtime/profile sources, web/CLI sources, native packaging graph, Node/NDK versions and patch inputs. Later runs with the same key restore and verify the bundle instead of repeating native compilation and profile tracing. Generated binaries and keystores are not committed; a cache hit is not treated as Android device-execution evidence.

## Signing setup

Use a trusted computer with a JDK (`keytool`), Python 3, and GitHub CLI `gh` authenticated to the target repository. The one-step helper creates a local PKCS#12 key and uploads the values directly to the `android-release` environment:

```sh
bash apps/android/scripts/create-and-upload-android-signing.sh "$HOME/android-signing/release.p12" OWNER/REPOSITORY
```

The helper prompts privately for one password (PKCS#12 uses the same password for the keystore and key), refuses to overwrite a local keystore, and asks before replacing any of the four existing GitHub secrets. Keep a secure offline backup of the keystore. Do not commit it or send it through chat.

The original two-step scripts are also available if you prefer to create the keystore and upload it separately:

```sh
bash apps/android/scripts/create-android-signing-key.sh "$HOME/android-signing/release.p12" android-release
bash apps/android/scripts/set-android-signing-secrets.sh "$HOME/android-signing/release.p12" OWNER/REPOSITORY
```

Both methods use `gh secret set` for `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEY_ALIAS`, `ANDROID_STORE_PASSWORD`, and `ANDROID_KEY_PASSWORD`. The helper creates or reuses the `android-release` environment; values are streamed to `gh` and are not printed.

Before signing, open **Settings → Environments → android-release** and add required reviewers and deployment branch/tag restrictions. Protect the `android-v*` tag pattern so releases are made only from reviewed, merged commits.

## Signed release

After the workflows are on `master` and the environment is protected, create a release tag on a commit already merged into `master`, using the form `android-vMAJOR.MINOR.PATCH` (an optional prerelease suffix is allowed). Run **Actions → Android Signed Release** from `master` and enter that tag. The reusable workflow builds the selected tag without signing secrets, pauses at the protected environment, installs the Android APK signing tool, then signs and verifies the APK after approval. The signed output is retained as the `android-release-signed` artifact.

The workflow signs an APK for distribution; it does not publish a store release or upload to Google Play.
