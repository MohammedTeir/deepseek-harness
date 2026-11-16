# Fixed terminal allocation broker and approval relay

Reference scope: the private native allocation protocol and its original-service approval adapter. Status: IMPLEMENTED with host adapter tests and Android compilation. Android socket instrumentation and native human approval remain unverified. The [APK #7 qualification](TERMINAL_ANDROID_PROOF.md) now connects a private bound service, native UI and fixed Android backend. Its APK is built and inspected; physical execution is pending.

## Native protocol

[TerminalAllocationBroker.kt](../app/src/main/java/io/github/mohammedteir/deepseekharness/TerminalAllocationBroker.kt) derives the application UID, app-private workspace ownership and installer-owned fixed fixture path from Android Context and stat. It rejects set-ID executables. Each instance creates a private random abstract AF_UNIX endpoint and per-run secret, checks SO_PEERCRED UID/PID, compares the secret and admits only describe, prepare, consume and cancel. It does not provide approve or arbitrary command execution actions.

The two native-issued qualification call IDs bound the grant inventory. Full requests bind the root session/Agent owner, real registry terminal ID, backend, executable/arguments, workspace and initial geometry. Caller UID fields, unknown/duplicate fields, invalid types, oversized frames and changed configuration fail closed. Only pty-number IDs match the current original registry convention. The broker cannot independently attest that Node created a genuine Agent; the reviewed runtime must validate the actual owner reference before forwarding it. Same-UID malicious-plugin isolation is not claimed.

Prepare constructs the [native one-shot grant](TERMINAL_ALLOCATION_AUTHORIZATION.md) and sends an immutable derived snapshot to a native callback. Only the native decide method resolves the human outcome; it binds both call and terminal IDs. Consume returns a receipt once and never launches a process. Known response-write failure revokes the associated grant. An observed transport failure is not proof of whether a remote peer received a frame.

Cancel records a tombstone even before prepare arrives, so a late request cannot create a new prompt/grant after owner cancellation. Pending decisions are withdrawn and late native decisions cannot revive a closed grant. Call and terminal reservations cannot be reused. The broker has two workers, at most four admitted sockets, frame/read/decision deadlines and a bounded audit with an explicit omitted-entry counter. Consumption totals remain independent of audit truncation. Owner close revokes grants, cancels decisions, closes sockets and awaits worker termination; cleanup failures remain observable, including to concurrent close callers. Cleanup belongs on the resource owner's background thread.

## Original approval adapter

[terminal-authorization.mjs](../runtime/terminal-authorization.mjs) snapshots the native configuration and binds one original tool execution to one actual registry spawn spec. It checks the genuine current Agent reference and owner, then asks the original ApprovalService inside the open tool context. The reason records the exact allocation fields; it is data and cannot approve anything. The controller relay checks that request and forwards prepare to the native provider. Only a valid provider outcome returns to the original service.

Allowed-once must be followed by native consume and an unchanged receipt, including native UID. A private one-use take operation binds the receipt to the identical spawn-spec object immediately before process creation. Missing approval, changed receipts, used authority, cancellation and unavailable answerers prevent allocation. Revocation aborts pending approval, discards late answers and awaits an acknowledged native cancel. Original guards are preserved; no tool pipeline guard is replaced or disabled.

The adapter accepts its transport from reviewed composition. An injected transport is not an authentication boundary. The current host qualification deliberately uses a transport double, while the actual Android broker remains unexecuted. A production/native bootstrap must supply the private authenticated transport and cannot accept agent-selected endpoints or credentials.

## Evidence levels and tests

[The host integration report](../evidence/terminal-authority-host-reference.json) uses a real original sdk-minimal profile, Agent, tool pipeline, ApprovalService and TerminalSessionService. It denies the first allocation before any process, grants the second, drives real original node-pty input/resize/output/exit, rejects a second take and recovers identical original approval/command events after acknowledged runtime shutdown. Native preparation/consumption are explicit test doubles; these results are not Android broker, native grant or human-consent evidence. No model response or tool output is fabricated.

Component tests cover mutated approval fields, unknown/changed native receipts, unavailable approval, pre-abort and revocation during pending approval with a late answer. The earlier genuine registry ownership/rollback tests remain enabled. [Android instrumentation](../app/src/androidTest/java/io/github/mohammedteir/deepseekharness/TerminalAllocationBrokerTest.kt) covers actual sockets, malformed/unauthenticated/unsupported requests, native decision binding, denial, concurrent one-shot consumption, mutation/replay rejection and cancellation before/during prepare. It uses automated native decisions and therefore cannot substitute for human UI testing. Compilation alone is not execution; record these device tests BLOCKED until run.

```sh
python3 -m unittest discover -s apps/android/tests -p 'test_terminal*.py' -v
./apps/android/gradlew -p apps/android :app:compileDebugKotlin :app:compileDebugJavaWithJavac :app:compileDebugAndroidTestKotlin :app:lintDebug --console=plain
```

## Remaining physical gate

The [APK #7 proof](TERMINAL_ANDROID_PROOF.md) implements the private bound service, native human surface, authenticated Node transport and fixed Android backend. Authorization and PTY startup have separate deadlines. The original host-only factories remain Linux-only; the Android composition uses separate qualification factories and native receipts. Host automated decision fixtures are excluded from the interpreted image.

Android fileKey support, actual human consent, socket behavior, same-UID lifecycle cancellation and native receipt-to-PTY creation remain unverified until the new device test passes. Existing phone node-pty evidence does not verify this path. Gate 3 remains IN PROGRESS. No general shell, arbitrary process-tree cleanup, foreground group support, original terminal UI, Root or Termux integration is claimed.
