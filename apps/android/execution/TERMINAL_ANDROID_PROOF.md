# Original terminal on Android: APK #7 qualification

Reference scope: a fixed benign TTY fixture through the original Harness tool, approval and owner-scoped terminal services. Status: IMPLEMENTED with host tests, relocated-image qualification and Android APK build/inspection. Physical-device execution is BLOCKED pending the submitted phone result. This is not general shell support or the final original Web UI.

## Installed flow

The original sdk-minimal profile registers android_qualified_terminal and the original TerminalSessionService. Its allocation spec supplies the real registry terminal ID and Agent owner. The existing ApprovalService records the exact immutable request and forwards it through authenticated AF_UNIX transport to TerminalAllocationBroker. TerminalProbeService owns the private broker and runtime; RuntimeProofActivity renders the native human request and sends decisions through its UID-checked private Binder connection. No agent-accessible approve action exists.

The fixed request names the installer-owned libharness_pty_fixture.so, --tty-child, canonical app-private workspace, session/call/owner/terminal, UID and initial 80 x 24 geometry. Native configuration and resource identity checks are unchanged. Two concurrent native consume requests must yield one receipt and one USED rejection before one real PTY is allocated. Changed and replayed receipt objects fail before process creation. The fixture receives only pty-input, is resized to 100 x 40, and exits. Actual output, exit, native child UID/PID/parent, owner cleanup and original tool/approval records are checked. PTY stderr is genuinely merged with stdout, not invented as a separate stream.

The controller performs acknowledged shutdown, starts a fresh original runtime and compares recovered original records. This proves runtime restart only after a successful device run; app restart and OS process death are separate. No model request or model tool-call event is fabricated. All ten packaged ELF binaries remain byte-identical to APK #6.

Host-only factories remain Linux-only. A separate Android fixed-fixture factory is used only by the reviewed qualification composition after the exact native receipt. Neither function is a security boundary against arbitrary same-UID plugins; original node-pty itself can execute code inside that UID. No malicious-plugin isolation or filesystem confinement is claimed. Unknown foreground groups still fail closed. There is no Root or Termux dependency.

## Build and artifact evidence

[Build inspection](../evidence/runtime-terminal-apk7-build.json) records actual APK/signature/alignment/ABI/native-library/image checks. [Host reference](../evidence/terminal-runtime-host-reference.json) runs the same controller and plugin with a real original profile/registry/PTY, using an explicitly labelled automated broker contract double. It does not verify Android sockets or human approval. [Delivery evidence](../evidence/runtime-terminal-apk7-delivery.json) records the uploaded ZIP and a downloaded-byte verification.

The observed profile-v8 image adds the actual terminal dependencies. Host ELF addons are excluded from APK data, then restored only in a separate Linux relocation tree. Original profile, pwd and terminal recovery checks run outside the checkout before packaging. Local TypeScript adapters are compiled to ESM; source/lockfile digests reject a stale image. Automated approval fixtures are forbidden in the interpreted image. Existing profile-v7 evidence is preserved.

With the SDK/NDK, original native binaries and workspace artifacts prepared as described in the Android build guide:

```sh
python3 apps/android/scripts/package_profile.py apps/android/runtime/out/profile-v8
./apps/android/gradlew -p apps/android :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug --console=plain
python3 apps/android/scripts/inspect_terminal_apk.py --build-log /path/to/build.log --output /path/to/inspection.json
```

The profile packager requires a new output directory; retain a prior image and select a fresh build directory when inputs change. Standard APK preparation now requires qualified profile-v8. The build does not fetch new native runtimes or execute binaries extracted into writable Android data. Generated bundles are recreated by the packager and ignored by Git. No production release is published.

## Phone test instructions

1. Download the ZIP from the delivery record and install its single main runtime APK as an update. Keep app data and existing sessions; do not uninstall or clear storage.
2. Open Harness runtime proof. Select RUN ORIGINAL TERMINAL + NATIVE APPROVAL, immediately above COPY COMPLETE RESULT.
3. Select Start test in the overview. DENY the first native request, then APPROVE ONCE on the second. Check the exact fixture, arguments, working directory, identifiers and ordinary UID shown. Keep the application visible throughout.
4. Wait for the complete JSON or BLOCKED result. Select COPY COMPLETE RESULT and send the entire text. A failure is evidence and must not be edited or replaced.

Expected successful evidence includes harnessStarted, sessionRecoveredAcrossRuntimeRestart and report.originalTerminalRegistry true; one process start, two concurrent consumers, one rejection, native allocationsConsumed=1, real TTY output/exit and matching ordinary UID. Denial, changed fields and replay must fail. gate3Passed remains false for review; it is not an error by itself. Existing linker/SDK shutdown diagnostics are retained. Resource identity failures appear in nativeBroker.resourceFailure; do not infer SELinux as their cause.

The ZIP contains one app, not the instrumentation APK or the older separate atomic app. No ADB connection was available during this build. Leaving or rotating the Activity cancels the qualification and revokes pending grants; broad Android lifecycle, arbitrary process trees, power loss, API 29/recent-device coverage, Bash semantics and original terminal frontend remain separate unverified work.

## Cleanup failure diagnosis

A user-reported APK #7 run returned only `Terminal broker cleanup failed`; this does not establish whether terminal qualification passed before disposal. The broker shuts down the listening socket before closing it and still requires accept-thread and worker termination. Cleanup errors remain blocking. The service preserves a completed qualification report as `qualificationBeforeCleanup` and includes bounded cause/suppressed details when reporting cleanup failure. These diagnostics do not upgrade device acceptance. The idle-listener and incomplete-request shutdown instrumentation cases require Android execution; host compilation cannot verify Android socket wakeup.
