# Android process and PTY capability proof

Status: IN PROGRESS. APK #4 contains a fixed native diagnostic, not a general shell provider or the original terminal backend. Gate 2 acceptance remains scoped by the existing review; Gate 3 needs phone results and further integration.

## Architecture and scope

The existing subprocess-local implementation in `packages/subprocess/subprocess-local/src/index.ts` lazily loads node-pty and contains Linux host assumptions. The original terminal registry in `packages/terminal/terminal/src/index.ts` owns terminal backends; terminal-bash's session implementation expects its controlled Bash prompt protocol. Those components are preserved. This diagnostic determines available Android primitives before adapting their existing interfaces.

The fifth button in Harness runtime proof asks for explicit native authorization of one fixed suite. The unexported ProcessCapabilityService accepts a same-UID Binder start message, creates a new canonical private 0700 directory, and launches the installer-owned ARM64 PIE executable. There is no caller-selected executable or script interface. The one fixed system-shell script emits stdout and stderr, prints cwd and exits 7. Tool discovery only checks twelve explicit /system/bin paths and does not enumerate every installed tool.

This diagnostic is separate from the original registered-tool approval test. It does not replace that pipeline or demonstrate a new Harness execution provider. Same-UID code is not a malicious-plugin security boundary. No Root, Termux, new storage permission, writable extracted executable or exported component is introduced.

## Fixed tests

- Separate live stdout/stderr and stdin acknowledgment before completion, exit 7.
- Concurrent draining of 16384 bytes per stream, exit 9.
- Missing executable with actual errno and exit 127.
- Explicit TERM cancellation and waitpid acknowledgment.
- Readiness-triggered timeout with TERM then KILL escalation and waitpid.
- Cooperative child/group termination with grandchild reap acknowledgment; not arbitrary process trees.
- Fixed /system/bin/sh script and read-only tool availability checks.
- Actual openpty, controlling terminal, isatty, input and resize from 24x80 to 40x100. PTY stderr is merged by design.

Native worker setup requires parent-death SIGKILL and checks parent identity. This does not prove behavior across Android framework death, detached processes or arbitrary descendants. File descriptors and owned child processes are bounded; failure to reap is a failure. Cancellation polling uses signals without unsafe signal-handler work. No performance or power-loss claims are made.

Missing PTY or shell capability yields PARTIAL with actual diagnostics; setup/protocol errors yield FAIL. There is no desktop fallback on Android. Every result deliberately retains gate3Passed=false, generalShellProviderImplemented=false and originalTerminalIntegrated=false.

## Executed checks and artifacts

[Host native evidence](../../evidence/process-host-native.json) records real Linux fork/exec/pipe/PTY operations; it is not Android evidence. Three native regression tests and two parser regression tests passed. Parser fixtures are explicitly synthetic. The first cancellation observer used procfs child polling and failed to observe readiness before process exit; the cause was not established. The corrected test waits for an actual stderr readiness event, sends SIGTERM, then requires the actual waitpid reap event. No process result is simulated.

[Build evidence](../../evidence/process-apk4-build.json) records Android debug APK, instrumentation companion and lint compilation, signing, ZIP/ELF alignment, original profile validation, NDK notices and hashes. All seven Gate 2 native libraries are byte-identical to APK #3. The eighth library is the API 29 ARM64 diagnostic executable with a static C++ runtime. Compilation and signature checks are not physical execution. The companion instrumentation APK is not distributed to the user.

## Phone test

1. Download the archive from the delivery record and install its single APK as an update to the large Harness runtime proof app. Do not uninstall or clear data. The small atomic test app is unrelated.
2. Open Harness runtime proof and select the fifth button, **Run fixed process + PTY capability tests**.
3. Read the fixed-suite authorization dialog and choose **Run fixed suite once**. Keep the Activity visible until the result appears.
4. Choose **Copy complete result** and send the complete output, including PARTIAL or BLOCKED diagnostics. Do not rerun a failed test without retaining its first output.

No ADB device was attached during this build. Native UI rendering, actual Bionic process behavior, PTY permissions and Android cancellation remain BLOCKED on phone testing. The new suite uses fresh process-probe directories and does not modify old session trees.

Validate a returned JSON with:

```sh
python3 apps/android/scripts/validate_process_result.py result.json --build-record apps/android/evidence/process-apk4-build.json
```

Use --allow-partial only to inspect explicit unavailable-capability diagnostics; it never accepts Gate 3. Attribute user-executed evidence separately from developer-controlled instrumentation.

## Next milestone

Review device results and map verified primitives into the original Subprocess and TerminalBackend interfaces. Do not enable the Bash backend merely because openpty works. Broader PTY job control, Ctrl-C, cancellation during Activity/OS death, general process cleanup, API 29 and recent-device qualification remain separate tests. No original frontend integration or general shell availability is claimed by this APK.

## Physical checkpoint received

The [selected-device review](../../../../ANDROID_GATE3_REVIEW.md) accepts the submitted matching APK #4 report on Android 11/API 30 ARM64. Earlier blocked-at-build statements above retain the history of that milestone. Overall Gate 3 remains IN PROGRESS for coverage and limits; the original terminal and a general shell provider remain unimplemented. No additional device run is required to accept this particular submitted report.
