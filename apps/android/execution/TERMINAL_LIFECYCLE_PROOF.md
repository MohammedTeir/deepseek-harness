# Original terminal lifecycle qualification: APK #8

Reference scope: fixed benign PTY wait timeout and cancellation through the original Harness terminal registry, tool pipeline, approval service and persisted session records. Host execution is verified; the bounded Android 11/API 30 run is VERIFIED at user-reported physical-device evidence level in the [phone review](../evidence/phone-apk8-lifecycle-result-review.json). The previous input/resize phone evidence remains in the [APK #7 review](../evidence/phone-apk7-terminal-result-review.json).

## Execution and authorization

The native broker describes the lifecycle qualification. The original tool still requests exactly the installer-owned libharness_pty_fixture.so with --tty-child, an app-private workspace, fixed session/call/owner/terminal identities and 80 x 24 geometry. The first prompt must be denied and the second approved once. Native one-shot consumption, mutation rejection and receipt validation remain enforced. No extra process, alternate executable, shell or fixture role is authorized.

After readiness, an empty, non-submitted send waits for one second. Its result must say timeout while the terminal remains running; this is a wait deadline, not a process termination deadline. The fixture receives no input. A second empty send is cancelled through the original TerminalSendOperation.cancel method, which writes Ctrl-C to the PTY. Exactly one cancellation is accepted. The actual child must exit with signal SIGINT and null exitCode, become unobservable and drain before registry cleanup succeeds. A settled operation cannot be cancelled again. Original approval and tool results must recover after acknowledged runtime shutdown and restart.

The backend sendWaitMs option bounds a send wait to at most ten seconds; its default is five seconds. The fixed lifecycle composition uses one second. Timeout does not revoke ownership or authorize further processes. The original terminal owner remains responsible for closing the existing terminal. This qualification does not establish general foreground-group signalling or arbitrary process-tree cleanup.

## Phone procedure

Install APK #8, version 0.1.14-terminal-lifecycle-proof, as an update to Harness runtime proof without uninstalling or clearing data. Run RUN ORIGINAL TERMINAL + NATIVE APPROVAL. Deny the first prompt and approve the second once; keep the Activity visible. Copy the complete result after it settles. The report must identify qualification lifecycle, a running timeout result, one process start, SIGINT exit, child cleanup and recovered original records. A BLOCKED result is a failure to investigate, not permission to bypass a check.

## Evidence limits

Linux qualification uses an explicitly labelled automated native-broker transport double with the genuine profile, original registry and real node-pty. It is not human approval or Android evidence. Android instrumentation compilation does not establish device execution. App restart, OS process termination, power loss, API 29/recent-device coverage, general shell support and malicious same-UID plugin isolation remain separate. Gate 3 remains IN PROGRESS until its remaining acceptance evidence is reviewed.

## Build records

The [validation record](../evidence/terminal-lifecycle-validation.json), [APK inspection](../evidence/terminal-lifecycle-apk8-build.json) and [delivery record](../evidence/terminal-lifecycle-apk8-delivery.json) identify the compiled sources, tests, signatures, APK digest and remaining phone checkpoint. The [host result](../evidence/terminal-lifecycle-host.json) and [relocated result](../evidence/terminal-lifecycle-relocated-host.json) explicitly retain their automated transport-double evidence level.
