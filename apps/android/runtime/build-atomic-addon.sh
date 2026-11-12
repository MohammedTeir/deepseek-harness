#!/usr/bin/env bash
# Build the same-directory Android publication binding after APK #1 physical acceptance.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "$script_dir/../../.." && pwd)"
: "${ANDROID_NDK_HOME:?Set NDK 28.2.13676358}"
: "${ANDROID_NODE_BUILD_DIR:?Set the source-built Node directory}"
grep -qx 'Pkg.Revision = 28.2.13676358' "$ANDROID_NDK_HOME/source.properties"
headers="$ANDROID_NODE_BUILD_DIR/node-v24.22.1/src"
node_library_dir="$ANDROID_NODE_BUILD_DIR/node-v24.22.1/out/Release"
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64"
mkdir -p "$script_dir/out/atomic"
"$toolchain/bin/aarch64-linux-android29-clang" \
  -std=c11 -O2 -Wall -Wextra -Werror -fPIC -fvisibility=hidden \
  -DNAPI_VERSION=8 -I "$headers" -shared -Wl,-z,max-page-size=16384 \
  "$repo_dir/native/system/packages/entry/src/atomic_publish.c" \
  -Wl,-z,defs -L "$node_library_dir" -l:libnode.so \
  -Wl,-rpath-link,"$toolchain/sysroot/usr/lib/aarch64-linux-android" \
  -o "$script_dir/out/atomic/libharness_atomic.so"
"$toolchain/bin/llvm-readelf" -h -l -d -W "$script_dir/out/atomic/libharness_atomic.so"
python3 - "$repo_dir" "$script_dir/out/atomic" "$node_library_dir/libnode.so" <<'PY'
import sys,json,hashlib
from pathlib import Path
root,output,node=map(Path,sys.argv[1:])
hash_file=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
record={'schemaVersion':1,'minimumApi':29,'abi':'arm64-v8a','napiVersion':8,'ndkVersion':'28.2.13676358',
        'sourceSha256':hash_file(root/'native/system/packages/entry/src/atomic_publish.c'),
        'nativeSha256':hash_file(output/'libharness_atomic.so'),'nodeLibrarySha256':hash_file(node)}
(output/'build.json').write_text(json.dumps(record,indent=2)+'\n')
PY
