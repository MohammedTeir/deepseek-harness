# Fixed terminal registry qualification

Reference scope: host-only integration of the original TerminalSessionService with a bounded real PTY backend. This does not enable Android terminal execution.

## Implementation and authority

[terminal-backend.ts](../runtime/node-pty-proof/terminal-backend.ts) implements the original TerminalBackend contract using the [qualified handle](PTY_HANDLE_QUALIFICATION.md). It accepts only the fixed fixture interaction, bounds scrollback and startup, and preserves actual exit and cleanup failures. Allocation cancellation applies until publication; the independent owner lifetime controls the published session. Unknown foreground process groups remain unavailable rather than being inferred from the child PID.

[The profile plugin](../tests/terminal-registry-plugin.mjs) registers the backend and a qualification tool through original extension points. Genuine Agent instances own terminals. The original tool executor and approval service record denial and permission, and the original terminal registry enforces ownership, name reservations and rollback. The controller uses automated SDK decisions and a host fixture authority scope, not native human authorization. Same-process reviewed fixture code is not a security boundary against malicious plugins.

The original host factories still reject Android. The [APK #7 proof](TERMINAL_ANDROID_PROOF.md) adds separate fixed Android factories under native authorization; its physical verification is pending. This earlier host report remains host evidence only.

## Executed evidence

[Host reference output](../evidence/terminal-registry-host-reference.json) records actual original SDK/profile startup, two genuine Agents, real node-pty fixture execution, original approval and command events, acknowledged shutdown and identical history after a fresh runtime resumes the session. No external model request is made. The canonical tool batch is retained in original command/done events; no model tool-call events are invented.

The integration test covers denied execution with zero allocations, missing host authority, foreign and forged owners, duplicate names, unsupported input, concurrent sends, unavailable foreground signaling, real input/resize/output and exit, early startup exit, cancellation before allocation with a late authority answer, cancellation after allocation, rollback at publication, name reuse and genuine owner disposal. Allocated fixture PIDs must no longer be observable after cleanup. Raw ASCII fixture scrollback is not a terminal emulator or a persistent Bash prompt implementation.

Run from the repository with its installed Node and C++ toolchain:

```sh
python3 -m unittest discover -s apps/android/tests -p 'test_terminal_registry_profile.py' -v
pnpm exec tsc --ignoreConfig --noEmit --strict --target ES2024 --module NodeNext --moduleResolution NodeNext --skipLibCheck --allowImportingTsExtensions --types node apps/android/runtime/node-pty-proof/terminal-backend.ts
```

The Python test builds a real native fixture in a unique temporary directory and launches the original profile controller. Its bounded timeout terminates its own process group. Host results do not replace physical-device evidence.

## Remaining checkpoint

Gate 3 remains IN PROGRESS. Next connect native-owned exact-request allocation authority to original terminal ownership and authenticated IPC, retaining rollback, cancellation and one-shot consumption. Only then build a new Android qualification APK and request phone verification. General shell commands, Bash semantics, stopped jobs, foreground identity, arbitrary descendants, OS-death cleanup, API 29 and recent-device coverage remain separate requirements. Root and Termux remain optional future providers.
