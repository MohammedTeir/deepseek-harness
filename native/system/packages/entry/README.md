---
description: "JavaScript entry for the prebuilt Landlock launcher and asynchronous POSIX flock."
kind: "package-library"
---
# @deepseek-ai/node-addon-system

English | [中文](README.zh.md)

The `./landlock-run` entry exports the Landlock launcher path, enforcement probe, grant arguments, and protocol constants. The independent `./flock` entry exports `tryLockExclusive(fd): Promise<void>`; importing either entry does not load `system.node`. The package has no root export.

The lock operation attempts `LOCK_EX | LOCK_NB` asynchronously. Keep the caller-owned descriptor open until completion; contention rejects with `EAGAIN`/`EWOULDBLOCK`, other syscall failures also reject, and errors carry their code, positive errno, and `syscall: 'flock'`. Native setup errors reject the same promise. Closing the last descriptor for the open file description releases the lock. The binding does not open, duplicate, close, or explicitly unlock descriptors.

Optional OS/CPU platform packages carry the binaries. Their `~x.y.z` dependency ranges allow later patches within the same minor version. Linux has `bin/landlock-run` and separate `bin/glibc/system.node` / `bin/musl/system.node`; macOS has `bin/system.node`. Missing or unloadable flock bindings reject acquisition, without installation-time compilation. Landlock remains a separate executable with its existing fail-closed protocol; unsupported kernels/platforms probe unusable.

Android ARM64 embedding uses a lazy, fixed `libharness_system.so` SONAME through the carrier's native-library linker namespace. The Android carrier must package a matching Bionic Node-API binding and its Node dependency; npm platform packages do not supply it. Loading failure rejects acquisition without falling back or granting a lock. The Android probe uses this entry, but Android Harness session persistence remains unverified.

`@deepseek-ai/node-addon-system/publish` exports `publishPreparedFileExclusive(source, destination)`. Non-Android callers retain fs.link semantics. Android ARM64 uses a fixed carrier-owned libharness_atomic.so and asynchronous Node-API v8 work to publish within one normalized, owned 0700 directory using renameat2(RENAME_NOREPLACE). Staging names must be distinct lowercase ASCII letters/digits/dot/hyphen basenames of at most 120 bytes. Success consumes staging on Android; it remains elsewhere. Callers fsync data before publication, fsync the destination directory afterward, and clean staging with ENOENT tolerated. EEXIST never replaces a destination; loader, permission and unsupported errors reject without fallback. Node names errno 95 ENOTSUP (the EOPNOTSUPP alias). A failure after publication is not rollback. Same-UID hostile staging mutation, cross-directory publication and retained-source aliases are outside this API. The Android carrier supplies the matching binding; npm platform packages do not.

The three C sources ship for auditability. See the workspace [architecture](../../docs/architecture.md), [support matrix](../../docs/support-matrix.md), and [CLI contract](../../docs/cli-contract.md).
