# Android CI and signed releases

## CI build

`.github/workflows/android-ci.yml` builds the current Android app on Linux x86_64 for pull requests, pushes to `feature/android-port` or `master`, and manual runs. The reusable `.github/workflows/android-build.yml` installs the pinned Android SDK/NDK, builds Node 24.22.1 and the Android native add-ons from pinned inputs, creates and validates the host profile image, assembles the unsigned release APK, runs release unit tests, and runs Gradle lint. The unsigned release APK is retained as the `android-release-unsigned` Actions artifact.

The first clean run compiles Node from source and can take a while. Build inputs stay in the runner's temporary directory; generated binaries and keystores are not committed.

## Signing setup

Use a JDK with `keytool` and GitHub CLI `gh` authenticated to the target repository. Generate a key locally:

```sh
bash apps/android/scripts/create-android-signing-key.sh "$HOME/android-signing/release.p12" android-release
```

`keytool` prompts for the passwords and certificate identity. Store the keystore and its backup securely. Do not commit it or send it through chat.

Upload the keystore and values directly to GitHub Actions environment secrets:

```sh
bash apps/android/scripts/set-android-signing-secrets.sh "$HOME/android-signing/release.p12" OWNER/REPOSITORY
```

The script creates the `android-release` environment and uses `gh secret set` for `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEY_ALIAS`, `ANDROID_STORE_PASSWORD`, and `ANDROID_KEY_PASSWORD`. Values are read interactively or streamed from the local key file; they are not placed in shell arguments or printed.

Before signing, open **Settings → Environments → android-release** and add required reviewers and deployment branch/tag restrictions. Protect the `android-v*` tag pattern so releases are made only from reviewed, merged commits.

## Signed release

After the workflows are on `master` and the environment is protected, create a release tag on a commit already merged into `master`, using the form `android-vMAJOR.MINOR.PATCH` (an optional prerelease suffix is allowed). Run **Actions → Android Signed Release** from `master` and enter that tag. The reusable workflow builds the selected tag without signing secrets, pauses at the protected environment, installs the Android APK signing tool, then signs and verifies the APK after approval. The signed output is retained as the `android-release-signed` artifact.

The workflow signs an APK for distribution; it does not publish a store release or upload to Google Play.
