# Gate 1 review and runtime qualification decision

## Decision

Gate 1 is ACCEPTED for a bounded Phase 2 runtime proof, following the author's authorization to review and proceed when its criteria are met. Acceptance covers reviewed audit evidence and a testable strategy. It does not certify Android runtime execution, native addon compatibility, security isolation or Gate 2 completion.

| Gate 1 criterion | Review evidence | Disposition |
|---|---|---|
| Complete resolved graph, optional/platform/transitive entries | `audit/android/dependency-graph.json`, 8,836 resolved edges | Satisfied for the committed lockfile |
| Native code, hooks, binaries and ABI risks | Installed payloads, registry metadata, native-library graph and compatibility matrix | Reviewed; 329 uninstalled archives and linked targets remain explicitly unverified, excluded from any compatibility claim |
| Frontend/routing/transport source inspection | Original Vite build, static-server/injection and Remote WebSocket findings | Satisfied as source/host-build evidence only |
| Precise blocker list | Native lock platform gate, GNU/Linux PTY linkage, bash assumptions, process/credential trust and Android packaging limits | Satisfied; these remain Phase 2/3 qualification requirements |
| Compared runtime candidates and testable strategy | Shared-library and packaged-executable comparison in architecture/runtime guides | Satisfied for experimental selection; neither is device-proven |

## Selected first experiment

Compile pinned Node 24.22.1 for Android ARM64/API 29 with NDK r28c, then load the shared library through APK native-library loading in a dedicated service process. This choice is based on Android's supported native-library packaging mechanism, the Node source's shared-library build/entry interface, existing NDK toolchain availability and the absence of any need to execute extracted writable native files. These are reproducible source/packaging facts, not evidence that Node runs on Android. Preserve the original Harness/profile launch path; a fixed Node API probe cannot substitute for agent initialization.

The alternative is an Android/Bionic executable installed through a compliant immutable APK mechanism. Its executable/interpreter/loader permissions and lifecycle must be tested on the same devices before selecting it; merely renaming a binary to `.so` does not establish supported execution. No fallback to writable-directory exec or required Termux is permitted. Reconsider the shared-library choice if its build, worker, addon or lifecycle behavior fails qualification.

## Immediate experiment and remaining blockers

Reuse the archived source-build investigation rather than repeating downloads. Verify the pinned source checksum and traceable patches. The earlier host-generator `-O0` attempt failed V8 always-inline compilation; use host-only `-O1` while retaining Android release flags. This is a new build attempt, not a repaired result until it completes.

The prototype must distinguish library linkage, Node API execution and authentic Harness readiness. Qualify ESM, workers, TLS/DNS, SQLite, filesystem and native locking before claiming the profile works. The shipped minimal profile still needs deliberate replacements for bash and Android-rejecting lock selection. Reviewed bundled code and a fixed explicitly approved harmless operation are the initial scope; arbitrary plugin/package installation, root and Termux remain excluded.

No attached Android device was found by `adb devices`; `/dev/kvm` and installed emulator system images are absent. That initial absence is recorded as the review starting condition. Official emulator/image installation subsequently succeeded and software boot is being attempted; a usable guest and ARM translation support are not yet verified. Hardware/emulator execution remains BLOCKED until actual readiness, while cross-compilation and APK packaging remain independently achievable. No device/API/ABI execution result, session recovery or tool output is fabricated.

## Evidence-policy repair

The repository-reference checker now separately validates the two canonical audit JSON records. Every declared revision must be a full lowercase 40-character known commit, all required revision fields must exist, and canonical JSON forbids duplicate keys or trailing text. Only exact top-level revision lines are admitted. Hash references in other files, undeclared/nested fields, and forbidden organization URLs remain rejected. Forty-six regression tests and the real repository scan passed. Original baseline evidence was not changed.
