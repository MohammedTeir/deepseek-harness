#!/usr/bin/env bash
# Compile the original Node-API lock implementation; this does not select it in Harness.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/../../.." && pwd)"
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to NDK 28.2.13676358}"
grep -qx "Pkg.Revision = 28.2.13676358" "$ANDROID_NDK_HOME/source.properties"
: "${ANDROID_NODE_BUILD_DIR:?Set the directory used by build-node.sh}"
headers="$ANDROID_NODE_BUILD_DIR/node-v24.22.1/src"
test -f "$headers/node_api.h"
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64"
mkdir -p "$script_dir/out/system"
"$toolchain/bin/aarch64-linux-android29-clang" \
  -std=c11 -O2 -Wall -Wextra -Werror -fPIC -fvisibility=hidden \
  -DNAPI_VERSION=8 -I "$headers" -shared -Wl,-z,max-page-size=16384 \
  "$repo_dir/native/system/packages/entry/src/flock.c" \
  -o "$script_dir/out/system/libharness_system.so"
cp "$repo_dir/native/system/LICENSE" "$script_dir/out/system/LICENSE"
"$toolchain/bin/llvm-readelf" -h -l -d -W "$script_dir/out/system/libharness_system.so"
echo 'Original flock source cross-compiled; Android loading and locking remain unverified.'
