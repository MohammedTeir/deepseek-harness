#!/usr/bin/env bash
# Build the pinned Node UNIX entry for the installer-owned executable experiment.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to NDK 28.2.13676358}"
grep -qx "Pkg.Revision = 28.2.13676358" "$ANDROID_NDK_HOME/source.properties"
: "${ANDROID_NODE_BUILD_DIR:?Set the directory used by build-node.sh}"
source_dir="$ANDROID_NODE_BUILD_DIR/node-v24.22.1"
echo "c946687691d86754f5d53560b54a70d17cfed62bf23158ac457497b8b912d740  $source_dir/src/node_main.cc" | sha256sum -c -
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64"
output="$script_dir/out/executable"
mkdir -p "$output"
"$toolchain/bin/aarch64-linux-android29-clang++" \
  -std=c++20 -O2 -fPIE -I "$source_dir/src" -I "$source_dir/deps/v8/include" \
  -I "$source_dir/deps/uv/include" -c "$source_dir/src/node_main.cc" -o "$output/node_main.o"
if [ ! -f "$source_dir/out/Release/libnode.so" ]; then
  echo 'BLOCKED: original Node entry compiled, but the shared Node build is not complete' >&2
  exit 1
fi
"$toolchain/bin/aarch64-linux-android29-clang++" \
  -fPIE -pie -Wl,-z,max-page-size=16384 '-Wl,-rpath,$ORIGIN' \
  "$output/node_main.o" -L "$source_dir/out/Release" -l:libnode.so \
  -o "$output/libnode_executable.so"
"$toolchain/bin/llvm-readelf" -h -l -d -W "$output/libnode_executable.so"
echo 'Node executable linked; installer packaging and Android execution remain unverified.'
