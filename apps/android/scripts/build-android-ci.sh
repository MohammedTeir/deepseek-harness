#!/usr/bin/env bash
# Build the pinned Android runtime inputs and qualified host profile image from source.
set -euo pipefail

repo_dir="$(git rev-parse --show-toplevel)"
android_dir="$repo_dir/apps/android"
: "${ANDROID_HOME:?Android SDK root is required}"
export ANDROID_NDK_HOME="${ANDROID_NDK_HOME:-$ANDROID_HOME/ndk/28.2.13676358}"
export ANDROID_NODE_BUILD_DIR="${ANDROID_NODE_BUILD_DIR:-${RUNNER_TEMP:-/tmp}/android-node-build}"
export ANDROID_NODE_JOBS="${ANDROID_NODE_JOBS:-2}"

case "$ANDROID_NODE_BUILD_DIR" in
  /*) ;;
  *) echo 'ANDROID_NODE_BUILD_DIR must be absolute' >&2; exit 2 ;;
esac
case "$(realpath -m "$ANDROID_NODE_BUILD_DIR")/" in
  "$(realpath "$repo_dir")/"*) echo 'Keep the Node source/build outside the checkout' >&2; exit 2 ;;
esac

grep -qx 'Pkg.Revision = 28.2.13676358' "$ANDROID_NDK_HOME/source.properties"
node --version | grep -qx 'v24.22.1'

# Build the pinned upstream Node source and all native libraries consumed by the APK.
bash "$android_dir/runtime/build-node.sh"
bash "$android_dir/runtime/build-system-addon.sh"
bash "$android_dir/runtime/build-atomic-addon.sh"
bash "$android_dir/runtime/build-node-executable.sh"

mkdir -p "$ANDROID_NODE_BUILD_DIR"
require_source="$ANDROID_NODE_BUILD_DIR/require-builtin-source"
if [[ ! -d "$require_source/.git" ]]; then
  git clone --filter=blob:none https://github.com/deepseek-ai/dsh-node-addon-require-builtin.git "$require_source"
fi
git -C "$require_source" fetch --depth=1 origin a58d3599a2e551d7d706d1ff796c9fd4bbaff63c
git -C "$require_source" checkout --detach a58d3599a2e551d7d706d1ff796c9fd4bbaff63c

addon_api_archive="$ANDROID_NODE_BUILD_DIR/node-addon-api-8.9.0.tgz"
if [[ ! -f "$addon_api_archive" ]]; then
  npm pack node-addon-api@8.9.0 --pack-destination "$ANDROID_NODE_BUILD_DIR" >/dev/null
  mv "$ANDROID_NODE_BUILD_DIR/node-addon-api-8.9.0.tgz" "$addon_api_archive"
fi
python3 "$android_dir/runtime/build_require_builtin.py" "$require_source" "$addon_api_archive"
python3 "$android_dir/runtime/build-node-pty.py"
python3 "$android_dir/scripts/package_node.py" \
  --build "$ANDROID_NODE_BUILD_DIR" --ndk "$ANDROID_NDK_HOME"

# This trace-backed packager validates the original profile, command, and terminal
# host references before producing the profile-v9 image consumed by Gradle.
python3 "$android_dir/scripts/package_profile.py" "$android_dir/runtime/out/profile-v9"

printf '\nPrepared Android native runtime inputs and profile-v9 image.\n'
sha256sum \
  "$android_dir/runtime/out/runtime-build.json" \
  "$android_dir/runtime/out/node-pty/build.json" \
  "$android_dir/runtime/out/profile-v9/profile-image.zip"
