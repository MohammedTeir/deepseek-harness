# Original node-pty Android qualification

Status: IMPLEMENTED and host tested; Android execution BLOCKED pending APK #6 phone evidence. This qualifies the original dependency before selecting a terminal adapter. It does not enable a Harness terminal backend or a generic command interface.

## Source findings and decision

The locked dependency is node-pty 1.2.0-beta.15 with the repository's existing patch. Its Unix C++ source chooses forkpty on Linux, including Android's actual __linux__ compilation target. The separate spawn-helper and posix_spawn path are Apple-specific in this revision. The existing JavaScript helper-path patch remains unchanged; no helper executable is required for this Android experiment. Node's process.platform remains android throughout; no Linux identity is spoofed.

| Candidate | Executed evidence | Decision |
| --- | --- | --- |
| Original node-pty C++ and JavaScript | Unmodified pty.cc compiles for API 29 ARM64; real Linux source-addon/loader tests pass | Select for physical qualification, not production acceptance |
| Stock Linux ARM64 prebuild | Earlier audit establishes GNU/Linux linkage | Reject for Android |
| New native PTY bridge | Existing low-level Android fixture passes, but no evidence yet requires replacing node-pty | Defer; no custom multiplexer |
| External Termux | Separate optional execution world | Future provider, never a silent fallback |

The upstream binding.gyp links libutil for Unix; Bionic exposes forkpty from libc, so the standalone cross-build omits libutil. The addon explicitly links libnode.so and uses NAPI_VERSION=8, C++ exceptions, a static C++ runtime, stack protection and 16KB ELF alignment. The native source is not patched. Android loading and Node-API thread-safe callback behavior remain subject to device tests.

## Narrow loader and packaging adapter

A dedicated qualification Node process loads original package JavaScript from reviewed bundled assets. A synchronous adapter temporarily replaces only that package's loadNativeModule export, calls process.dlopen on the installer-owned addon and restores the export after initialization. No global require hook, platform spoof, writable ELF extraction or native source rewrite is used. This is reviewed code scope, not isolation from hostile same-UID plugins.

The cross-build records original source/package/lock-patch hashes, compiler command, ABI/API, notices and binary digests. Binaries are stripped before hashing because Android Gradle strips them during packaging. The preparation guard rejects changed sources, original package bytes and native binaries. APK inspection independently verifies packaged bytes, signatures, ZIP/ELF alignment, explicit Node dependency, all original JavaScript hashes and the exact library inventory. Existing eight native libraries are unchanged; two new installer-owned files are the original addon and fixed benign fixture.

The original package MIT license, full original pty.cc including its borrowed ISC notices, node-addon-api license and existing NDK notices are included. No npm install scripts, downloads, executable permissions in writable app storage, Root or Termux are needed at run time.

## Fixed test scope

The unexported same-UID service exposes only a one-shot fixed-suite start. Native human consent precedes the test. No caller-selected command or script is accepted. It runs the original node-pty implementation against a benign native fixture with five fixed roles:

- Controlling TTY, initial 80 columns/24 rows, actual input and resize to 100 columns/40 rows; stderr is merged by PTY design.
- Natural exit code 7 with real output.
- Ctrl-C written through the terminal, requiring SIGINT 2.
- Explicit TERM, requiring signal 15.
- Readiness-triggered deadline, ignored TERM then KILL, requiring signal 9.

The fixture reports its real UID/PID/parent PID and requires the expected parent plus PR_SET_PDEATHSIG(SIGKILL) setup before output. This is setup evidence, not an executed parent-death test. The fixture cannot launch descendants or a shell. Each result requires the original exit event and ESRCH when checking that child's PID. This proves only the fixed direct-child cases; arbitrary shell jobs, inherited-descriptor stress, process groups, stopped jobs and general terminal-session quiescence remain unverified.

The suite does not initialize an agent or create fake session events. Its harnessStarted=false and originalTerminalIntegrated=false distinguish it from the existing fourth original-tool test. Cancellation on leaving the Activity is designed to close the Node owner, and fixtures require parent-death setup; actual Android lifecycle behavior is unverified.

## Build and host checks

```sh
ANDROID_NDK_HOME=/workspace/android-sdk/ndk/28.2.13676358 ANDROID_NODE_BUILD_DIR=/workspace/android-node python3 apps/android/runtime/build-node-pty.py
python3 -m unittest discover -s apps/android/tests -p 'test_node_pty*.py' -v
```

The host test uses the actual original C++ source, original JavaScript and loader seam, real forkpty/input/resize/signals, a unique private directory and bounded cleanup. Parser and asset guards use explicitly synthetic negative inputs. No host result is Android proof.

Use the existing JDK/SDK/Gradle environment from ANDROID_BUILD_GUIDE.md, then:

```sh
./apps/android/gradlew -p apps/android :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug --console=plain -Pkotlin.compiler.execution.strategy=in-process
python3 apps/android/scripts/inspect_process_apk.py --node-pty-proof --build-log BUILD_LOG --output BUILD_RECORD
```

The first APK build exposed the expected stripping/hash difference before delivery; stripping before hashing preserves the strict installed-byte check. An inspection-script return-value error was corrected while retaining explicit Node linkage and ELF validation. Historical failure evidence and existing phone acceptances remain unchanged.

## Phone procedure and next gate

Install the single APK in the APK #6 delivery archive as an update to the large Harness runtime proof app. Preserve data. Select **Run original node-pty proof**, below the prior fixed process/PTY test. Read the fixed-suite prompt, choose **Run fixed suite once**, keep the Activity visible and send **Copy complete result**. Send complete BLOCKED output too; do not treat compilation as a phone pass.

```sh
python3 apps/android/scripts/validate_node_pty_result.py result.json --build-record apps/android/evidence/runtime-node-pty-apk6-build.json
```

No attached ADB device is available for this milestone. Native UI rendering and actual addon behavior are BLOCKED on phone execution. Overall Gate 3 remains IN PROGRESS. If the phone passes, adapt the original SubprocessTerminalHandle and terminal registry with explicit authorization and actual ownership/foreground/termination observations. Existing Linux process-inspection, shell activity, Bash prompt assumptions and broader lifecycle handling still require adaptation; do not enable them merely because this fixture passes.
