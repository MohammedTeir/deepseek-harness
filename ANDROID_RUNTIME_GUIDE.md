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

## Phase 2 source-build experiment

Gate 1 accepts a bounded shared-library experiment; Gate 2 remains unverified. `apps/android/runtime/build-node.sh` verifies the pinned Node 24.22.1 archive checksum, requires NDK 28.2.13676358 and compiles for Android ARM64/API 29. Set `ANDROID_NDK_HOME` and an absolute `ANDROID_NODE_BUILD_DIR` outside the checkout. Existing matching source/build output can be reused. Host generators use `-O1`; Android target release flags remain intact. The prior `-O0` attempt failed V8 always-inline compilation and is not a successful build result.

Two traceable external-source patches link the NDK CPU-feature implementation into zlib and disable unsupported V8 trap handling (including the cross-build host simulator). Their source is under `apps/android/runtime/patches`; forward/reverse dry runs reject mismatched input and recognize applied patches. Node, NDK CPU-feature, NDK runtime and original system-addon notices must accompany distributed binaries.

`build-system-addon.sh` compiles unchanged upstream flock C source as a Node-API v8 Android shared library. The API probe uses that original binding to attempt acquisition, contention and release; the production Harness lock selector still rejects Android and is not modified by this experiment.

After successful compilation, `scripts/package_node.py` checks ARM64 ELF, LOAD alignment, allowed dependencies and the Node entry symbol before staging libraries and license records. Asset preparation requires matching native hashes and refuses an APK without the inspected runtime. JNI loads the library in a dedicated nonexported service process; disposal terminates that process to release V8 globals. This process shares the app UID and is not an isolation boundary against hostile plugins. The probe has no arbitrary command/script input and does not start Harness.

The fixed script tests SQLite, workers, ESM, crypto, private-file output and the native binding; DNS/TLS target only public example.com without credentials. Linux execution verified the local APIs but DNS returned EAI_AGAIN, leaving DNS/TLS unverified. Android behavior, including linker namespace and addon loading, is unverified. No device is attached. Do not report a packaged or compiled probe as an authentic Harness session or approved tool result.

The shared-library host must also qualify `process.execPath` and child-Node launch. `packages/subprocess/subprocess-local/src/runner-launch.ts` uses that path for the managed Node runner; in an embedded Android process it may identify the application process executable rather than Node. The probe records the actual value and marks child-Node launch untested. Do not treat successful worker_threads execution as evidence for child_process.fork or runner launch. A packaged executable or a deliberate Android runner adapter may still be needed.
