# Native terminal allocation grant

Reference scope: a qualification-only Java policy component for one fixed PTY allocation. Status: IMPLEMENTED with host JVM tests and Android compilation/lint. The [private broker and original approval adapter](TERMINAL_BROKER_INTEGRATION.md) are implemented and compiled/tested at their stated evidence levels. The [APK #7 qualification](TERMINAL_ANDROID_PROOF.md) implements native UI/runtime wiring with physical execution still pending. The [original terminal registry host qualification](TERMINAL_REGISTRY_QUALIFICATION.md) remains a separate evidence level.

## Binding and consumption

[TerminalAllocationGrant.java](../app/src/main/java/io/github/mohammedteir/deepseekharness/TerminalAllocationGrant.java) reuses the existing CommandGrant state machine. Its immutable request adds the actual registry terminal ID, Agent owner ID, backend and initial dimensions to the session/tool-call/executable/arguments/workspace/UID binding. The only native command configuration is an installer-owned libharness_pty_fixture.so with --tty-child, 80 columns and 24 rows. It grants allocation only; later input, resizing, lifetime and cleanup still require the owning terminal backend.

The eventual native broker must authenticate peer identity and the per-run secret, derive paths and UID from native-owned state, and validate the session, call and registry ownership before constructing this component. Passing an ID or UID to this Java constructor does not authenticate it. No agent-facing approval method, wire listener, service or process launcher is added here. Only a native human-decision handler may call decide. An approved request can be consumed once; an allocation failure after consumption requires fresh approval. Expiry uses the existing monotonic clock and bounded lifetime. Close revokes a pending grant but cannot terminate a process allocated elsewhere.

Terminal metadata mismatches return REQUEST_CHANGED before inspecting command-grant state. Exact requests preserve the original pending, denied, expired, used and closed outcomes. The command snapshot and its arguments are immutable. Root/negative native identity, noncanonical paths and an unavailable/writable fixed executable are rejected at construction.

## Resource checks and limits

The grant captures workspace and executable file identities through BasicFileAttributes.fileKey. Before approval and consumption it rechecks canonical paths, file identity/type, executable size/modification time and executable access. A changed or inaccessible resource revokes the grant and throws IOException; restoring it does not restore approval. A filesystem with unavailable identity fails explicitly. Android fileKey behavior has not been executed on a device for this component.

These checks detect the tested directory replacement, symlink and executable changes. They do not hold directory descriptors across process creation, prevent a same-UID attacker changing resources between checking and use, verify workspace ownership from Android stat, or isolate malicious plugins. The future broker must perform native UID/owner checks and derive the fixture from applicationInfo.nativeLibraryDir. A matching basename and read-only mode alone do not establish installer ownership or permit executable extraction into writable data. The reviewed bundled-code qualification must keep that boundary explicit. This is not filesystem confinement. No process execution, native IPC authentication or human consent can be inferred from these policy tests.

## Validation

[The JVM fixture](../tests/TerminalAllocationGrantFixture.java) exercises the actual Java implementation: pending/denied/one-shot approval, every identity and geometry mutation, null candidate, revocation, expiry, immutable snapshots, malformed identities/dimensions, resource changes followed by attempted reuse, and 32 synchronized consumers with one winner and 31 USED outcomes. This is thread contention for one native-host object, not independent-process or Android execution evidence. Fixture data is never executed.

```sh
python3 -m unittest discover -s apps/android/tests -p 'test_terminal_allocation_grant.py' -v
cd apps/android
./gradlew :app:compileDebugKotlin :app:compileDebugJavaWithJavac :app:lintDebug --console=plain
```

The test uses a unique non-root Linux temporary directory and host JDK. Android compile/lint does not establish on-device file identity support. The [APK #7 proof](TERMINAL_ANDROID_PROOF.md) now ships the component through its private native broker. Device execution remains pending.

## Physical integration checkpoint

The [APK #7 composition](TERMINAL_ANDROID_PROOF.md) binds the actual registry allocation through the original ApprovalService, native UI and authenticated broker before the fixed PTY is created. Original guards and runtime/session formats remain unchanged. Collect its phone output before accepting Android resource identity, consent, cancellation and execution. Gate 3 remains IN PROGRESS; general shell, process groups, untrusted-plugin isolation and original Web UI remain separate work.
