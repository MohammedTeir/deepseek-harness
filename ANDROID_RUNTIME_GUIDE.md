# Android runtime investigation

## Summary

Investigation record, not installation instructions for a working runtime. The root manifest requires Node >=24.9.0. Node 24.22.1's `BUILDING.md` explicitly calls Android unsupported and untested in its CI, despite retaining `android-configure`. This is a feasibility risk, not proof that a port is impossible.

[Node source guidance](https://github.com/nodejs/node/blob/v24.22.1/BUILDING.md#android) and [retrieved platform references](audit/android/platform-references.json) support the candidate comparison in [architecture](ANDROID_ARCHITECTURE.md). The local source headers are investigation inputs, not evidence that Android Node executes.

## API and binary requirements

The source index records filesystem/fs-promises, crypto, networking/TLS/DNS, streams, workers, VM, SQLite, process/child_process, TTY, async hooks, inspector, SEA and other builtins. The synchronized PTC evaluator also imports `node:domain`; qualify its evaluator/error path if that plugin is included. Their presence across the repository does not make each mandatory for the minimum profile. Trace imports and the actual chosen plugin tree before excluding a builtin. `node:sqlite` and native session locks are concrete persistence dependencies; browser shims do not establish equivalent semantics.

AArch64 ELF is necessary but insufficient: verify Android/Bionic linkage, public NDK symbols at API 29, DT_NEEDED, interpreter where applicable, addon N-API/V8 compatibility, packaged-library access, 16 KB segment/ZIP alignment and actual load/execute behavior. A glibc or musl Linux ARM64 binary is not an Android binary. Native addon platform selection can fail even after successful C cross-compilation.

Android NDK r28c's `pty.h` declares openpty/forkpty since API 23, so API availability alone does not block API 29. Actual app access, SELinux, child lifecycle and node-pty loading remain unverified. Probe existing APIs before designing a custom PTY bridge.

## Deferred proof

After review, compare shared-library and supported packaged-executable candidates using identical tests. Capture exact source/toolchain, compiler/linker output, ABI/API/device identifiers, errors and lifecycle results. No current Android execution, Harness initialization, persistent session or tool result is claimed. Earlier local prototypes and compilation attempts are outside this branch and do not pass any device gate.
