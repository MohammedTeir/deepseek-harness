---
description: "Prebuilt system primitives for Linux confinement and POSIX Session write locks."
kind: "package-library"
---
# @deepseek-ai/node-addon-system

English | [中文](README.zh.md)

## Summary

Use the Linux `landlock-run` executable to confine subprocesses, or the `./flock` entry to acquire a POSIX write lock. Platform packages contain the precompiled binaries; consumer installation never builds native code. Landlock policy and Session lifecycle remain with callers.

## Table of Contents

- [Use](#use)
- [Support](#support)
- [Development](#development)

## Use

`@deepseek-ai/node-addon-system/landlock-run` exports `launcherPath`, `probe`, and `grantArgs` for Landlock. Its executable name, flags, and failure semantics are defined by the [CLI contract](docs/cli-contract.md).

The [flock behavior contract](docs/flock-contract.md) maps descriptor, process, and advisory-lock semantics to independent native tests.

`@deepseek-ai/node-addon-system/flock` exports `tryLockExclusive(fd): Promise<void>`. Keep the descriptor open until completion. Acquisition uses nonblocking exclusive flock; contention rejects with `EAGAIN` or `EWOULDBLOCK`, and closing the final descriptor for the open file description releases the lock. See the [entry README](packages/entry/README.md).

Importing either entry does not load an addon. A missing Landlock executable probes unusable; a missing flock binding rejects acquisition. Neither path compiles or silently grants unsupported behavior.

`@deepseek-ai/node-addon-system/publish` exports `publishPreparedFileExclusive(source, destination)`. Non-Android callers retain fs.link semantics. Android ARM64 uses a fixed carrier-owned libharness_atomic.so and asynchronous Node-API v8 work to publish within one normalized, owned 0700 directory using renameat2(RENAME_NOREPLACE). Staging names must be distinct lowercase ASCII letters/digits/dot/hyphen basenames of at most 120 bytes. Success consumes staging on Android; it remains elsewhere. Callers fsync data before publication, fsync the destination directory afterward, and clean staging with ENOENT tolerated. EEXIST never replaces a destination; loader, permission and unsupported errors reject without fallback. Node names errno 95 ENOTSUP (the EOPNOTSUPP alias). A failure after publication is not rollback. Same-UID hostile staging mutation, cross-directory publication and retained-source aliases are outside this API. The Android carrier supplies the matching binding; npm platform packages do not.

## Support

Linux x64/arm64 packages contain the static Landlock executable and separate glibc/musl `system.node` files. macOS x64/arm64 packages contain `system.node` only. Landlock additionally needs an enforcing Linux kernel; Windows uses the Harness's existing locking implementation. The [support matrix](docs/support-matrix.md) names builders and verification owners.

## Development

From this directory, `pnpm build:ts` builds the entry, `pnpm build:native` builds the host's declared native payload, and `pnpm build:test-oracle` builds an independent flock syscall fixture. Then `pnpm test` exercises entry, lock, packaging, and available kernel behavior. Linux requires musl-gcc for a complete build; macOS uses cc. The root `pnpm run build:native-system` builds only the current host addon for source tests.

The [architecture](docs/architecture.md), [packaging](docs/packaging.md), and [release procedure](docs/release.md) own implementation and publication details.

### Dev Note

None.
