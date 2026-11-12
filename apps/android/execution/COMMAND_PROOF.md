# Fixed command qualification reference

Scope: native host components for the pending original Harness approved-command proof. This is not a command-capable Android product or a completed Gate 2 demonstration.

## Implemented components

CommandGrant owns one immutable request: session ID, call ID, executable, arguments, canonical workspace and UID. A native decision can approve or reject a pending request once. Consumption compares every field under synchronization and marks the grant used before spawning. Changed requests do not expand consent or consume the original matching grant. Rejected, expired, used and closed grants fail closed; a failed spawn still requires new consent. A monotonic two-minute maximum lifetime and owner close bound authorization. The request must be constructed from trusted native configuration; this class does not validate filesystem ownership or prove caller identity.

FixedPwdExecution's Android factory fixes /system/bin/pwd with no arguments, checks an ordinary supplied UID and rejects an executable writable by the application. It canonicalizes an existing workspace, clears inherited environment, closes stdin, waits at most five seconds and retains bounded real stdout/stderr and exit status. OwnedProcess handles cancellation and cleanup. A package-private constructor allows a separately identified host executable only for qualification. No shell string, root escalation, Termux fallback or caller-selected Android executable is exposed.

## Executed verification

The [host/build record](../evidence/command-grant-host-validation.json) records eight fixture modes, including real host pwd execution, failed launch consumption and 32 concurrent grant consumers with exactly one winner. These are JVM policy and Linux subprocess results, not Android execution evidence. Existing process-owner tests additionally cover live-child termination, interrupted cleanup and cancellation before launch. Android Java compilation and lint pass; the nonfatal read-only Android analytics settings warning remains recorded.

## Integration requirements

Neither class is called by the app, an IPC listener or an original Harness tool yet. The native approval surface, trusted Android UID/workspace derivation, cancellation wiring, IPC peer validation and original tool integration remain NOT STARTED. Never expose decide on agent-accessible IPC or deserialize a grant from plugin arguments. Native UI must render the native-derived exact command and identity; a generic agent-supplied approval reason is insufficient.

The original SDK approval/request response carries only an approval outcome. Preserve that protocol. The composed approval service requires an open original agent turn; a qualification pre-step can invoke a registered original tool and stop before model inference without introducing a fake model or replacing the engine. That integration is proposed, not executed. Approval denial, mutation/replay rejection and real output must be demonstrated together in the resulting physical-phone APK before approvedCommandExecuted can become true.

These helpers are not confinement against arbitrary code already executing under the same application UID. Only reviewed bundled qualification code is in scope; arbitrary plugins and general subprocess access need their own security review. Activity restart, process termination during execution and model-generated tool calls remain separate acceptance cases. The delivered persistence APK and its physical reports are unchanged.
