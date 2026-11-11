#!/usr/bin/env bash
# Cross-compile the pinned Node source; failure is a feasibility result, never a fallback.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to NDK 28.2.13676358}"
grep -qx "Pkg.Revision = 28.2.13676358" "$ANDROID_NDK_HOME/source.properties"
: "${ANDROID_NODE_BUILD_DIR:?Set an absolute build directory outside the checkout}"
case "$ANDROID_NODE_BUILD_DIR" in /*) ;; *) echo 'Build directory must be absolute' >&2; exit 2;; esac
mkdir -p "$ANDROID_NODE_BUILD_DIR"
cd "$ANDROID_NODE_BUILD_DIR"
repo_dir="$(cd -- "$script_dir/../../.." && pwd -P)"
case "$(pwd -P)/" in "$repo_dir/"*) echo 'Build directory must stay outside the checkout' >&2; exit 2;; esac
archive=node-v24.22.1.tar.xz
if [ ! -f "$archive" ]; then
  curl -fL --max-time 300 "https://nodejs.org/dist/v24.22.1/$archive" -o "$archive"
fi
echo "4f5379796280cdaeb0c2f358fd04b6a16cc4fb7dfa83b5a8c91a9d963b435231  $archive" | sha256sum -c -
if [ ! -d node-v24.22.1 ]; then tar -xJf "$archive"; fi
cd node-v24.22.1
# GYP's Make generator needs a source-relative path for this NDK source.
cp "$ANDROID_NDK_HOME/sources/android/cpufeatures/cpu-features.c" deps/zlib/android-cpu-features.c
cp "$ANDROID_NDK_HOME/sources/android/cpufeatures/NOTICE" deps/zlib/ANDROID_CPU_FEATURES_NOTICE
for source_patch in "$script_dir"/patches/*.patch; do
  if patch --batch --forward --dry-run --silent -p1 < "$source_patch"; then
    patch --batch --forward -p1 < "$source_patch"
  elif ! patch --batch --force --dry-run --silent -R -p1 < "$source_patch"; then
    echo "Patch does not match pinned Node source: $source_patch" >&2
    exit 1
  fi
done
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64"
export PATH="$toolchain/bin:$PATH"
export CC="$toolchain/bin/aarch64-linux-android29-clang"
export CXX="$toolchain/bin/aarch64-linux-android29-clang++"
export AR="$toolchain/bin/llvm-ar"
export CC_host=gcc CXX_host=g++ AR_host=ar
# Host-only generators do not ship. V8 always_inline code requires optimization.
export CFLAGS_host=-O1 CXXFLAGS_host=-O1
export GYP_DEFINES="target_arch=arm64 v8_target_arch=arm64 android_target_arch=arm64 host_os=linux OS=android android_ndk_path=$ANDROID_NDK_HOME"
export LDFLAGS='-Wl,-z,max-page-size=16384'
./configure --dest-cpu=arm64 --dest-os=android --openssl-no-asm --cross-compiling --shared
make -j"${ANDROID_NODE_JOBS:-2}"
find out/Release -name 'libnode.so*' -type f -print
