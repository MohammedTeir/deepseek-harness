# Original subprocess service: fixed Android adapter

Status: IMPLEMENTED and host tested; Android execution BLOCKED pending APK #5 phone output. This is a narrow step after the verified Android 11 process/PTY capability suite. It is not a general command provider or interactive terminal backend.

## Original service integration

The original profile mounts AndroidFixedPwdSubprocess as a subclass of the unchanged SubprocessRuntime service. The existing registered tool injects ctx.subprocess and uses resolveExecutable, spawn, collected readers, done and waitForExit. It no longer sends positive execution RPCs directly. Existing tool guards, approval service, human native approval, one-shot broker and original session event/recovery pathways remain in use.

A private AsyncLocalStorage scope binds the reviewed tool's session/call identity and native-described workspace to the spawn. The service cannot mint approval. Native authorization still owns exact executable, arguments, UID and cwd checks. This is reviewed bundled-code scope, not isolation from malicious same-UID plugins or arbitrary Node code.

## Supported and rejected requests

Only /system/bin/pwd with no arguments, native canonical workspace, ignored stdin, bounded collected stdout/stderr, no environment override, no control descriptor and exactly 2000ms termination grace is accepted. The grace matches the existing native owner's two-second TERM tier, followed by its bounded KILL wait. Native fixed execution has its existing five-second command deadline; caller aborts revoke and close the owner. Native broker RPC bounds are separate and are not the command's execution duration.

The returned live handle represents an in-flight native request. Collection becomes available when the broker returns its complete captured result; this is not incremental streaming. Readers use independent byte offsets and report tail loss. Raw pipes, inherited descriptors, spill, custom environment, other commands and interactive input are rejected before execution RPC. ResolveExecutable additionally requires the host's actual executable-availability check. No shell string, fallback, Root or Termux is exposed.

The fixed successful pwd returns actual stdout/stderr, exitCode=0 and signal=null. A nonzero or interrupted native Java result rejects with raw native status retained, because this transport does not expose normal-exit versus POSIX signal classification. No signal is guessed or manufactured. General nonzero/signal support needs a richer process transport before broadening this provider.

Cancellation cannot establish quiescence merely by closing a socket. The adapter waits for a native cancel acknowledgment after OwnedProcess.close. If cleanup cannot be acknowledged, waitForExit rejects and the provider cleanup effect throws. The original root Context disposal collects errors without propagating this rejection; successful root disposal alone is therefore not proof of quiescence. Disposal cancels all active handles and awaits the same observed ranges. This retains the existing owner's limited managed range; arbitrary descendants and Android OS-death cleanup remain unverified.

SpawnTerminal returns the original SUBPROCESS_PTY_UNAVAILABLE error. TerminalEnvironment returns posix without advertising a default interactive shell. The native capability suite proved openpty on the phone, but there is not yet a persistent authenticated terminal-I/O transport. No custom multiplexer or Bash prompt emulation is introduced.

## Executed evidence

The real original SDK/profile test passes registration, denial, approval, fixed native-contract execution through the original service and recovery of the actual canonical tool result. Its host transport fixture uses automated decisions and real Linux pwd; it is not Android or human-approval evidence. The relocated package-image check runs outside the checkout, with the original session format and no Linux native binary shipped in the APK.

The adapter regression uses the actual original service class and real host processes. It checks exact bindings, unsupported requests before IPC, pre-abort, two one-shot consumers, bounded independent readers, failed-command status, cancellation acknowledgment, disposal awaiting a held transport, and refusal to claim quiescence for malformed outcomes without a cleanup acknowledgment. The held transport is explicitly a fixture with no process/result; native child ownership is covered separately by existing real JVM/native tests. The phone report from APK #4 remains historical evidence for primitives only.

Initial host integration failed when resolving the service from a package without a direct dependency, then failed when the tool accessed ctx.subprocess without an injection declaration. The final profile mounts the service separately, resolves from its declared dependency owner and declares the tool's service injection. These failures were repaired; validation was not weakened. Old generated profile images were preserved separately before rebuilding the current cache.

## APK #5 phone procedure

Install the single APK in the delivery archive as an update to the large Harness runtime proof app. Preserve data. Select the fourth original-tool approval test, keep the Activity visible, choose Deny for the first request and Approve for the second. Copy complete result and send it. The report must include originalSubprocessService=true and commandResult.subprocessProvider=android-fixed-pwd-v1, along with real output, one process launch, denied/changed/replayed requests and recovered original events.

```sh
python3 apps/android/scripts/validate_command_result.py result.json --build-record apps/android/evidence/runtime-subprocess-apk5-build.json --require-subprocess
```

No connected ADB device is assumed. Successful host tests and APK inspection do not establish Android execution of the new adapter. Overall Gate 3 stays IN PROGRESS; API 29/recent-device coverage, live terminal transport, PTY session lifecycle, original terminal backend, original frontend and model requests remain separate milestones.
