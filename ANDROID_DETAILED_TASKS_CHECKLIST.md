# DeepSeek Harness Android — Detailed Tasks, Acceptance Checklist & Handoff Board

> **Companion:** [ANDROID_COMPLETE_ROADMAP.md](ANDROID_COMPLETE_ROADMAP.md)  
> **Authoritative scope:** [DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md](DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md), particularly sections **15, 15A and 17**.  
> **Snapshot:** 2026-11-13; dev HEAD \`4496650e83bf16ce85eae9fd4e589270116ec742\`; \`master\` is the repository's real default branch.  
> **Meaning of checkboxes:** \`[x]\` means **documented evidence exists for exactly the stated, sometimes limited, claim**; \`[ ]\` means not accepted, incomplete, blocked, or future work. A checkbox is **not** authorization to broaden scope. See [ANDROID_PORT_STATUS.md](ANDROID_PORT_STATUS.md) and the gate reviews.

## Usage: strict update protocol

1. At session start verify **Git HEAD, branch, working tree, master/master-prompt revision, latest evidence, and phone/APK results**. Never rely on an old snapshot or a prior chat transcript alone.
2. Search real implementation + tests before marking anything \`[x]\`. A passed host test or compiled APK **does not** close a phone-test checkbox.
3. Maintain task IDs so Codex can report progress unambiguously; link commits, artifacts, precise command/exit, report JSON and environment when closing tasks.
4. Update \`ANDROID_PORT_STATUS.md\` and the relevant Gate review *before* marking gate acceptance. Do not edit historical test reports or auto-clear known failures.
5. If blocked for device, credentials, SDK or upstream behavior, preserve \`[ ]\`, annotate **BLOCKED: cause**, and continue independent work.
6. All product functionality must still comply with authoritative master prompt. Tests below add detail but do not substitute for its explicit acceptance.
7. This checklist was committed to documentation in \`master\` by user request; **do not merge feature code, open a PR or publish a release** without separate user authorization.
8. Keep all test artifacts free of secrets, access tokens, private data and unredacted user files.

## Status dashboard (baseline)

| Phase/Gate | Snapshot | Immediate blocker |
| --- | --- | --- |
| Phase 0 | VERIFIED | None, keep baseline fresh |
| Phase 1 / Gate 1 | ACCEPTED | Audit recheck for any newly enabled packages |
| Phase 2 / Gate 2 | BOUNDED ACCEPTED | Model-provider round trip remains untested without credentials |
| Phase 3 / Gate 3 | IN PROGRESS | **APK #7 physical original-terminal/native-approval test** |
| Phase 3A / Gate 4 | NOT VERIFIED | Original WebView + secure transport + streaming |
| Phase 4 | INTEGRATION NOT COMPLETE | SAF/Keystore/lifecycle/models/plugins/MCP/workflows |
| Phase 5 / Gate 5 root-related work | NOT COMPLETE | Optional Termux/root providers and adversarial authorization |
| Phase 6 | NOT COMPLETE | Security, performance, device/API and lifecycle matrix |
| Phase 7 / Gate 6 | NOT COMPLETE | Reproducible release artifact and final acceptance |

---

# P0 — Current critical path: APK #7 and Phase 3

### P0.1 Verify test artifact and tester environment

- [x] **P0-001** APK #7 original terminal proof implemented, built and recorded at \`4496650e\`: [guide](apps/android/execution/TERMINAL_ANDROID_PROOF.md).
- [x] **P0-002** Signed Android debug package, alignment, ARM64, minSdk 29, targetSdk 36 inspected: [build evidence](apps/android/evidence/runtime-terminal-apk7-build.json).
- [x] **P0-003** Host original registry/tool/PTY proof and Android build/lint tests reported passing: [validation](apps/android/evidence/terminal-apk7-validation.json). **Scope: host/build only.**
- [x] **P0-004** ZIP delivery and downloaded-byte hash match recorded: [delivery evidence](apps/android/evidence/runtime-terminal-apk7-delivery.json). **Does not establish phone execution.**
- [ ] **P0-005** Confirm APK #7 ZIP accessible or provide newly verified downloadable package if link expired.
- [ ] **P0-006** Verify SHA-256 of installed main APK equals \`c55fde2fca0ef5cc6732c267580b736acf22c808ab822cdc1653933a2ef73da0\`; record device model, API/ABI, installed version/signing identity.
- [ ] **P0-007** Install as UPDATE preserving existing app-private sessions; do not uninstall/clear data to work around signing/version issues.
- [ ] **P0-008** Run \`RUN ORIGINAL TERMINAL + NATIVE APPROVAL\`; record complete raw JSON, stderr/logs and physical tester actions.
- [ ] **P0-009** In first native approval screen inspect exact command/fixture, args, cwd, user ID, Agent/session/call/terminal ID and click **Deny**; assert no child process.
- [ ] **P0-010** In second distinct request inspect exact identity and click **Approve Once**; assert one authorized spawn.
- [ ] **P0-011** Verify original \`TerminalSessionService\` + registered original tool/approval pipeline, real terminal ID/Agent ownership and native allocation receipt.
- [ ] **P0-012** Verify actual PTY tty identity, owner UID/PID, input→output, correct stderr merged into PTY, resize 80×24→100×40, actual exit/reap.
- [ ] **P0-013** Verify two concurrent consumers, exactly one success and one USED rejection; replay/mutation/invalid resource identity fails *before* launch; native start count remains one.
- [ ] **P0-014** Verify original session/approval/command event history survives acknowledged shutdown and real Node runtime restart with matching records/hashes.
- [ ] **P0-015** Validate complete phone JSON using dedicated unmodified validator and exact build fingerprints; preserve raw result, PASS/FAIL, known warnings, log and device details.
- [ ] **P0-016** Check cancellation when Activity leaves/rotates: pending approval invalidated without silent acceptance. Distinguish UI cancellation from actual child process termination.
- [ ] **P0-017** Record physical result in \`apps/android/evidence/\`, update \`ANDROID_GATE3_REVIEW.md\` and \`ANDROID_PORT_STATUS.md\` with *bounded* claim; do not mark Gate 3 complete solely on a fixed fixture.
- [ ] **P0-018** Fix any APK #7 failure with minimal patches and rebuild/test new uniquely versioned artifact rather than changing evidence to green.

**Stop rule:** if APK #7 fails or device unavailable, leave P0 phone checks open and address separate work only. Preserve existing approved Gate 2 and APK #4–#6 reviews.

### P0.2 Close actual Gate 3 (separate from APK #7 passing)

- [x] **P0-019** Fixed Android process, system shell, PTY, stdout/stderr, stdin, nonzero exit, timeout and kill/reap on reported Android 11 phone (APK #4).
- [x] **P0-020** Original \`SubprocessRuntime\` fixed approved \`pwd\` integration on reported phone (APK #5).
- [x] **P0-021** Unmodified original \`node-pty\` ARM64 fixed input/resize/exit/signals phone qualification (APK #6).
- [x] **P0-022** Host original registry/Agent ownership, terminal handle/service adapter and approval composition validated; Android physical scope still pending.
- [ ] **P0-023** Bring real original terminal session creation/ownership/handle allocation and cleanup online in Android accepted scope (APK #7).
- [ ] **P0-024** Verify terminal live input/output/resize, exit, timeout, cancellation, all relevant original service contracts, disconnect/reconnect and cleanup on actual Android.
- [ ] **P0-025** Audit PTY lifecycle: process groups, Ctrl-C, TERM/KILL, child descendants, foreground information, unknown capability fail-closed.
- [ ] **P0-026** Verify Android \`/system/bin/sh\`, Toybox utilities, cwd/env/argv, supported commands and missing tools without incorrectly claiming GNU/Bash compatibility.
- [ ] **P0-027** Enforce executor and PTY session resource budgets: maximum children, output/backpressure, timeouts, memory and file descriptors.
- [ ] **P0-028** Define user-visible provider capability report and unsupported-tool messages (no hidden Termux/root fallback).
- [ ] **P0-029** Test Android API 29 and at least one recent supported API/ABI, with emulator versus physical results explicitly separated. Some broader matrix may remain Phase 6, but any target-version gap is documented.
- [ ] **P0-030** Test Android service/Activity termination during allocation, live PTY/child execution, repeated restart and orphan cleanup. Partial coverage must not be generalized.
- [ ] **P0-031** Review original TerminalBackend/subprocess interfaces against all demonstrated device behavior, patch genuine incompatibilities without replacing core engine.
- [ ] **P0-032** Update Gate 3 explicit criterion-by-criterion review and classify every remaining unsupported feature; **do not infer gate PASS from build success or diagnostic-only success**.

---

# P1 — Phase 0, Phase 1 and Gate 1 baseline preservation

## Phase 0 — Repo/fork

- [x] **P1-001** Correct fork/upstream and historical baseline inspected.
- [x] **P1-002** Source revision, branch, environment/toolchain and lock digest recorded.
- [x] **P1-003** Original upstream history and monorepo preserved.
- [ ] **P1-004** On each new milestone, recheck default branch, PRs, remote changes, dirty tree and user merge authorization.
- [ ] **P1-005** Maintain an authoritative changelog: baseline SHA, source patch list and retained user changes.

## Phase 1 / Gate 1 — Audit

- [x] **P1-006** Traversed pnpm lock graph and direct/transitive/platform dependencies at initial accepted baseline.
- [x] **P1-007** Android Bionic vs glibc, ELF/executable packaging and candidate Node architectures analyzed.
- [x] **P1-008** Native-addon and original frontend/transport risks documented.
- [x] **P1-009** Gate 1 strategy and bounded experiment reviewed/accepted.
- [ ] **P1-010** Re-audit new optional libraries/plugins/assets added after audit and all relevant upstream syncs.
- [ ] **P1-011** Keep full Android support matrix for native addons, toolchain packaging, WASM/worker APIs and unsupported dependencies.
- [ ] **P1-012** Audit ABI/page-size and Android SDK/target compatibility when enabling new binaries/features.

---

# P2 — Phase 2 / Gate 2 accepted foundation and remaining integration

## Embedded runtime and storage

- [x] **P2-001** Embedded Node.js v24.22.1 runs ARM64 on user-tested Android 11 without required Termux/root.
- [x] **P2-002** Original Harness SDK/profile boots with genuine readiness/identity evidence.
- [x] **P2-003** Session JSONL hardlink failure recorded; isolated \`renameat2(RENAME_NOREPLACE)\` physical PoC tested in scoped filesystem.
- [x] **P2-004** Shared original JSONL no-replace publication integration verified within APK #2 reported scope.
- [x] **P2-005** Authentic session state recovered across Node runtime restart and repeated invocations.
- [x] **P2-006** Genuine registered Harness tool + original approval + native user Deny/Approve + fixed \`pwd\` real output and exit verified in APK #3 reported scope.
- [x] **P2-007** Collision/mutation/replay/concurrency denial recorded for fixed native approved command.
- [x] **P2-008** Gate 2 accepted in [bounded local-engine review](ANDROID_GATE2_REVIEW.md).
- [ ] **P2-009** Exercise actual supported external model/provider with user-authorized test credential, real LLM response, errors, cancellation and streaming; **BLOCKED when no credential**.
- [ ] **P2-010** Show authentic tool result and user approval in original Chat UI once Phase 3A completes.
- [ ] **P2-011** Test power loss/active-write process termination and broader session migration/attachment publication semantics without extrapolating APK #2 no-replace success.
- [ ] **P2-012** Verify full app-lifecycle session recovery and clean restart beyond Node runtime restart.
- [ ] **P2-013** Test API 29/newer Android runtime/profile compatibility, not only Android 11.
- [ ] **P2-014** Preserve strict no-fake-server/no-remote-Harness/no-desktop guarantee and verify real user-facing agent turns later.

---

# P3 — Phase 3A / Gate 4 original Web UI and secure streaming

## Source and asset integration

- [ ] **P3-001** Inspect original \`apps/web\`, \`packages/client\`, app routing, asset bundling, Vite base paths, fonts, icons, themes, workers, data loading and RPC contracts.
- [ ] **P3-002** Freeze a reference screenshot/behavior baseline from upstream UI; identify Android-only responsive changes and desktop non-regression tests.
- [ ] **P3-003** Build authentic original UI assets from checked-out source in clean documented build.
- [ ] **P3-004** Bundle assets inside APK with verified file hashes, no required remote web host.
- [ ] **P3-005** Configure AndroidX \`WebViewAssetLoader\` virtual HTTPS origin (normally \`https://appassets.androidplatform.net\`), no unrestricted local file scheme.
- [ ] **P3-006** Correct SPA deep-link/history fallback; restrict to app routes only; no HTML fallback for missing assets/API.
- [ ] **P3-007** Verify JS bundles, CSS, fonts, icons, workers, source maps policy, caching and URI/percent encoding on supported WebView versions.
- [ ] **P3-008** Preserve upstream chat, model selection, session history, settings, plugin/tool screens, terminal UI and original visual identity.
- [ ] **P3-009** Add only necessary mobile viewport/touch/safe-area adjustments; keep desktop behavior regression tested.

## Authenticated local transport

- [ ] **P3-010** Audit original HTTP/RPC/WebSocket/SSE/IPC paths and define minimal authenticated Android bridge.
- [ ] **P3-011** Secure loopback binding/origin restrictions/per-session secrets, protocol handshake and app-to-app/cross-origin resistance.
- [ ] **P3-012** Test CORS/CSP, WebSocket Origin, cookies and storage, unauthorized navigation and mixed-content settings.
- [ ] **P3-013** Reject untrusted WebView JS bridge calls; no arbitrary page may trigger tools or retrieve keys.
- [ ] **P3-014** Map runtime readiness, startup failure, shutdown, reconnect and session-affinity to real frontend state.
- [ ] **P3-015** Implement real event streaming/backpressure/reconnect/error handling through original protocols; no mocked messages.
- [ ] **P3-016** Test suspended/resumed WebView and background limits without lost/duplicated tool events.

## End-to-end functional acceptance

- [ ] **P3-017** Display original UI on real Android device; navigate actual screens including sessions/history/settings.
- [ ] **P3-018** Start and recover actual Harness session via authenticated original UI.
- [ ] **P3-019** Request a tool through original UI/agent path, render exact native approval, Deny and Approve Once, show real stdout/exit and persisted result.
- [ ] **P3-020** With authorized credentials, complete real user→model→agent→tool→UI cycle; record provider/timeouts and correct stream.
- [ ] **P3-021** Mobile touch, soft keyboard/IME resizing, rotation, Android back, deep links, accessibility, clipboard and file pickers.
- [ ] **P3-022** Negative tests: forged origin/token/URL, missing assets, path traversal, invalid stream frame, dropped connection, unsafe navigation.
- [ ] **P3-023** Record Gate 4 review with APK, source SHA, devices/WebView versions, output and all limitations.

---

# P4 — Phase 4 Android adapters & full original Harness feature integration

## SAF/filesystem and app-private data

- [ ] **P4-001** Define storage model for app-private workspace, user-selected SAF URIs and file ownership.
- [ ] **P4-002** Implement Android document picker read/import, write/export, atomicity within available URI semantics, permissions and persistable grants.
- [ ] **P4-003** Test URI revocation, deleted/moved document, unplugged/cloud provider, large files, path traversal and failure recovery.
- [ ] **P4-004** Audit all original session materialization, migration, attachment and backup/restore publication paths on Android.
- [ ] **P4-005** Preserve data across app upgrades, failures and controlled restarts without broad external-storage permission.
- [ ] **P4-006** Integrate share/export/backup/restore UX into original frontend, with sensitivity controls.

## Credentials, models and provider APIs

- [ ] **P4-007** Implement Keystore-backed protection strategy for provider credentials (including backup/device migration semantics).
- [ ] **P4-008** Add secure key entry/rotation/clear, prevent logging/WebView JS leakage, screen/clipboard accidental exposure where feasible.
- [ ] **P4-009** Integrate original multiple-provider model selection, config persistence and capability flags.
- [ ] **P4-010** Verify real authorized LLM request, streaming, cancellation, tool calling and error/timeout/rate-limit handling.
- [ ] **P4-011** Implement connectivity/usage diagnostics and honest offline/failure states.
- [ ] **P4-012** Test invalid/revoked credentials, network loss and switching providers without exposing old keys.

## Android lifecycle and system capabilities

- [ ] **P4-013** Android runtime supervisor: process startup, readiness, health, shutdown, service restart and bound cancellation.
- [ ] **P4-014** Respect Android foreground-service declarations/types/notifications, background limitations and Doze/battery behavior.
- [ ] **P4-015** Test Activity/WebView recreation, rotation, resume, low-memory death, user force-stop and permission revocation.
- [ ] **P4-016** Reconnect frontend safely; reconcile session events and PTY/process handles without duplicate execution.
- [ ] **P4-017** App diagnostics/log export with secret redaction and explicit feature failure reasons.
- [ ] **P4-018** Android notification/intents/package visibility/share and permission minimization review.

## Original Harness features

- [ ] **P4-019** Preserve original agent loop/profile lifecycle and original tool registry under Android-specific capability-aware adapters.
- [ ] **P4-020** Restore compatible settings, sessions, history, conversation state and source-backed event streaming.
- [ ] **P4-021** Preserve compatible workflows and original plugin lifecycle; classify each important plugin SUPPORTED/ADAPTED/LIMITED/UNSUPPORTED.
- [ ] **P4-022** Validate MCP HTTP/streamable remote servers independently of local stdio MCP subprocess server support.
- [ ] **P4-023** Verify file, search, external, browser/computer or other platform-specific tools individually; truthful failures on Android-incompatible ones.
- [ ] **P4-024** Attach terminal UI to original terminal backend; real interactive I/O/history/copy-paste/resize and errors.
- [ ] **P4-025** User-facing capability reporting, supported tool/provider selection and visible unsupported alternatives.
- [ ] **P4-026** Handle source updates, session migration, configuration changes, compatibility and regressions against upstream.
- [ ] **P4-027** Define precise feature-completion matrix with links to actual device evidence.

---

# P5 — Phase 5 optional providers / Gate 5 privilege architecture

## External Termux — optional, independent

- [ ] **P5-001** Review official Termux/Termux:Tasker and RUN_COMMAND APIs and Android install-source/version compatibility.
- [ ] **P5-002** Implement conservative installation/capability detection and user-driven opt-in setup.
- [ ] **P5-003** Request only documented permissions, including \`com.termux.permission.RUN_COMMAND\` where needed, and validate \`allow-external-apps\`, exported service/package visibility and supported return channels.
- [ ] **P5-004** Implement trusted request dispatch and real execution result mapping for actually supported API cases.
- [ ] **P5-005** Verify stdout/stderr/exit, timeout/cancel and streaming only to the degree supported by real Termux protocol.
- [ ] **P5-006** Handle Termux missing, denied, unsupported version, disconnect, no output channel, security/permission failure, app update.
- [ ] **P5-007** Never assume direct access to Termux private files, binaries or execution scope from Harness UID.
- [ ] **P5-008** Show selectable optional provider in original Harness settings; embedded core works when absent.

## Root — separate explicit provider

- [ ] **P5-009** Define threat model and trusted root-helper isolation boundary independent of Node/agent arguments; confirm only real supported root manager availability.
- [ ] **P5-010** Conservatively detect ROOT UNAVAILABLE/NOT AUTHORIZED/AUTHORIZED/DENIED/REVOKED/ERROR, with no auto-escalation.
- [ ] **P5-011** Define structured canonical root request: session, tool, call, operation, argv, resources, UID, scope, expiry and unique request ID.
- [ ] **P5-012** Native approval displays exact operation and risk; deny by default; no persistent unrestricted agent-accessible root shell.
- [ ] **P5-013** Enforce one-shot/scope bounds, replay/mutation/argument replacement denial, cancellation, policy checks before any \`su\`.
- [ ] **P5-014** Explicit denylist/policy for destructive, persistent, system-critical operations irrespective of generic consent.
- [ ] **P5-015** Review indirect effects of shell strings/redirection/scripts/env; prefer structured argv and trusted helper with narrow operations.
- [ ] **P5-016** Test on suitable explicitly authorized rooted device only; no rooting attacks, bypassing or exploitation.
- [ ] **P5-017** Test privilege revocation, failure, root-manager rejection and no silent embedded/Termux→root provider switch.
- [ ] **P5-018** Ensure core app and all standard settings/tools continue to work non-root on unrooted devices.
- [ ] **P5-019** Decide explicit release feature scope if Root/Termux integration is to be deferred; record owner approval rather than silently dropping master requirements.

---

# P6 — Phase 6 hardening, adversarial tests & compatibility

## Gate 5 full security acceptance

- [ ] **P6-001** Read/uphold upstream \`SAFETY.md\`; formalize agent/plugin/native service threat model and privileges.
- [ ] **P6-002** Adversarial prompt-injection suite: malicious repo text, web pages, retrieved documents, terminal outputs and MCP responses.
- [ ] **P6-003** Tool/plugin policy fuzzing: mutated JSON, mismatched request ID/argv/cwd/UID/tool identity, duplicate fields, expiry, replay, substitution.
- [ ] **P6-004** Root denial suite (when root provider present): denied, revoked, self-approval attempt, direct agent \`su\`, malicious plugin bypass and unauthorized fallback.
- [ ] **P6-005** Same-UID hostile plugin feasibility and limitations evaluated; separate-UID process/security boundary tested wherever supported. Do not advertise sandboxing without proof.
- [ ] **P6-006** WebView transport attacks: malicious navigation, origin spoof, forged token, CSRF/cross-app, bridge injection, WebSocket handshake, path traversal and credential exfiltration.
- [ ] **P6-007** Verify secret masking in logs, stack traces, events, backups, exported files, notifications and debugging surfaces.
- [ ] **P6-008** Package/addon supply chain and native executable integrity review; plugin enablement least privilege.
- [ ] **P6-009** Security findings prioritized/severity-rated; fix critical issues or explicitly block release.
- [ ] **P6-010** Independent Gate 5 review, documented positive/negative authorization results and residual limitations.

## Lifecycle, recovery and fail-safe behavior

- [ ] **P6-011** Android activity destruction and service/process death during model requests, command execution, PTY session, file writes and approval pending.
- [ ] **P6-012** App force-stop/reopen versus Node-only restart separately measured; no silent retry of destructive actions.
- [ ] **P6-013** Session crash consistency: truncate/corrupt tail, rename collision, full storage, fsync failure, interrupted migration and partially written attachments.
- [ ] **P6-014** Power-loss durability tested or explicitly qualified as not directly demonstrated by controlled kill tests.
- [ ] **P6-015** Native child and descendant cleanup on cancellation, timeout, supervisor death, process groups and blocked I/O.
- [ ] **P6-016** Network loss/reconnect, slow provider streaming, cancellation races, duplicate events and reconnect state.
- [ ] **P6-017** SAF permission revocation, lost credential, Keystore invalidation, terminal-provider loss, plugin crash and disk-full diagnostics.
- [ ] **P6-018** Accessibility, keyboard/IME, screen rotate, sleep/wake, Doze, foreground notification and background limits.

## Device/API matrix and performance

- [ ] **P6-019** Android 10/API 29 real supported ARM64 device or emulator, with actual runtime/addon/frontend acceptance.
- [ ] **P6-020** Android 11/API 30 selected device regression suite after complete integration (not only proof APK).
- [ ] **P6-021** At least one recent Android/API version with modern process/permissions/WebView behavior.
- [ ] **P6-022** Emulator/physical results separately labeled; test 16 KB page-size environment where applicable.
- [ ] **P6-023** Verify targetSdk/app-store-policy and foreground-service compliance on target release.
- [ ] **P6-024** Measure cold/warm startup, Node load, WebView rendering, command/PTY launch, stream latency, app memory, CPU, battery, storage and release size on named configurations.
- [ ] **P6-025** Resource stress: concurrent sessions/agents/PTYs, large output/files, slow device, memory pressure and cancellation.
- [ ] **P6-026** Upstream desktop/browser regression smoke tests for isolated Android-only changes.
- [ ] **P6-027** Test CI negative path and ensure no skipped/filtered assertions or failed test reframed as success.
- [ ] **P6-028** Maintain device/API/ABI/NDK/build SHA matrix with PASS/FAIL/BLOCKED and exact unsupported reasons.

---

# P7 — Phase 7 distribution, Gate 6 release readiness and future upkeep

## Reproducible build and release artifacts

- [ ] **P7-001** Clean-checkout documented build from pinned commit, Node/pnpm/JDK/SDK/NDK, native binaries and original frontend assets.
- [ ] **P7-002** Produce traceable debug and release APK packages with SHA-256, provenance, versionCode/versionName, signing scheme, ABI and SDK configuration.
- [ ] **P7-003** Verify native ABI ELF dependencies, no writable-dir executable violations, 16 KB/page alignment where relevant and correct native license inclusion.
- [ ] **P7-004** Secure release signing/key custody and debug/release configuration differences, secrets and WebView debugging restrictions.
- [ ] **P7-005** CI artifact generation, test/report attachments, supply-chain/license notices, release-notes source linkage and binary reproducibility assessment.
- [ ] **P7-006** Validate upgrade from prior debug/test state separately from clean install; session migration/recovery, notification and permission changes.
- [ ] **P7-007** Validate actual original UI + local engine + model flow (when credentials) + real tool/terminal + approvals + sessions + storage + supported providers on tested devices.
- [ ] **P7-008** Final security, functional, lifecycle, crash, storage, performance, emulator and physical-device acceptance review; Gate 6.
- [ ] **P7-009** Write user guide, supported Android list, installation, API key/storage setup, optional Termux/root setup, troubleshooting and limitations.
- [ ] **P7-010** Create explicit release/no-go decision with evidence; **user authorization required before GitHub Release, Play Store publication or development-branch merge**.
- [ ] **P7-011** Monitor post-release regressions and Android/Node/upstream compatibility only after an explicitly approved release.

## Master Prompt Definition of Done — independent final gate

Each checkbox below is copied in **meaning** from master section 17, not a claim that the full item is already complete.

- [x] **DOD-01** Development uses existing fork and retains upstream history (initial verified baseline).
- [ ] **DOD-02** Supported target APK installs/runs as an integrated final app, not only diagnostic APKs.
- [ ] **DOD-03** Actual original Harness Web frontend is bundled and retains real screens/visual identity.
- [ ] **DOD-04** Touch, keyboard/IME, Android navigation and accessibility work in original frontend.
- [x] **DOD-05A** Real original Harness engine has run locally without required Termux/server on reported Android 11 phone (bounded Gate 2).
- [ ] **DOD-05B** Same engine and end-to-end flow pass within final integrated app/device support matrix.
- [ ] **DOD-06** Valid authorized real model request succeeds (credential conditional).
- [x] **DOD-07A** Fixed native approval/denial and anti-replay proof on Android 11 in bounded Gate 2 scope.
- [ ] **DOD-07B** Full trusted tool/plugin/root authorization in integrated app, including negative security tests.
- [ ] **DOD-08** Real harmless tool stdout/exit shown in **original Harness UI**.
- [x] **DOD-09A** Real session recovered after original Node runtime restart and repeated invocation (bounded APK #2/#3).
- [ ] **DOD-09B** Session recovered reliably after full app restart/process lifecycle in final app.
- [ ] **DOD-10** SAF/storage and Android Keystore credential handling implemented and verified.
- [ ] **DOD-11** Working embedded interactive terminal with supported commands, cancellation and observable output in final UI.
- [ ] **DOD-12** Compatible tools/plugins/MCP integrations demonstrably functional, others truthfully marked.
- [ ] **DOD-13** Optional external Termux provider implemented/tested where supported or explicitly owner-approved release-scope deferral.
- [x] **DOD-14A** Core non-root runtime proven for selected tests.
- [ ] **DOD-14B** Optional root provider, separately authorized and appropriately tested on suitable device if retained in required scope.
- [ ] **DOD-15** Android-constrained lifecycle and crash recovery verified.
- [ ] **DOD-16** WebView, local transport, tool and native security negative/regression tests pass.
- [ ] **DOD-17** CI creates traceable APK artifacts, source/licenses/build docs checked.
- [x] **DOD-18A** Selected bounded phone reports are preserved and identified as user-reported evidence.
- [ ] **DOD-18B** Final integrated device/API test matrix and all residual limits documented.

**Important:** split partial items deliberately. The final release requires the *full original Definition of Done*, not just checked subproofs.

---

# FUTURE — Post-baseline feature backlog (not automatic acceptance blockers unless master requires them)

Prioritize only after verifying impact, security and user approval.

### FUT-01 — Bundled utilities and tools management
- [ ] **FUT-001** Feasibility study: Android Bionic-compatible packaged Git, curl, Python, OpenSSH, editors and other utilities; native addons/licensing/executable path/size constraints.
- [ ] **FUT-002** Minimal trusted installable tool catalog with signed/hashed provenance and version compatibility.
- [ ] **FUT-003** Tools manager with discover/install/update/uninstall/verify/logs/capability diagnostics, *only* under approved trusted package pipeline.
- [ ] **FUT-004** Storage quotas, failure rollback, offline packages and cleanup with no arbitrary unsafe script execution.

### FUT-02 — Better terminal and workflow UX
- [ ] **FUT-005** Multiple terminal sessions, scrollback/search, robust Unicode/RTL/IME, copy/paste and working directory history in original UI.
- [ ] **FUT-006** Provider-aware tool and shell capabilities, unsupported-option labeling, authorized explicit provider switch.
- [ ] **FUT-007** Resumable session/terminal logs and recoverability diagnostics within Android OS constraints.
- [ ] **FUT-008** Resource/performance settings and user-visible stop/cancel summaries.

### FUT-03 — Ecosystem, models, security and quality
- [ ] **FUT-009** Expanded compatible MCP provider library and platform-safe Android workflows.
- [ ] **FUT-010** Additional LLM model/provider connectivity, structured usage/latency reporting and safe credential switching.
- [ ] **FUT-011** Stronger untrusted-plugin sandbox boundary if feasible; evidence-based isolation instead of relying on same-UID IPC secrets.
- [ ] **FUT-012** Device farm CI, automatic Android version/ABI/addon regression coverage, controlled update migration.
- [ ] **FUT-013** Localizable original UI, accessibility, tablet/foldable layouts and system theme improvements.
- [ ] **FUT-014** Backups, diagnostics/export and startup/performance tuning, privacy-by-default.
- [ ] **FUT-015** Ongoing upstream compatibility checks and annotated adapter patch series.

---

# Required evidence matrix for each closed milestone

| Field | Required record |
| --- | --- |
| Task IDs | The exact checkbox IDs closed, and those still BLOCKED |
| Source | Repository, branch and full commit SHA |
| Artifact | APK filename/version, digest, signed certificate and delivered package verification |
| Environment | Host vs emulator vs physical; device/API/ABI/kernel/WebView, Node/JDK/SDK/NDK versions |
| Command/test | Exact reproducible command/input/test sequence, output/exit and validator name |
| Security | Real user approval/denial, caller identity, rejected mutation/replay, privileges and remaining risks |
| Runtime | Actual original SDK/profile/tool/PTY integration, no mocks in Android image |
| Durability | Session and event hashes, shutdown, runtime/app restart, crash semantics and unverified assumptions |
| Result | PASS / FAIL / BLOCKED and narrow accepted scope; no overwritten failure history |
| Follow-up | Concrete next task ID, dependency, owner decision, and deliverable |

## Codex restart/handoff template

Copy this template into the next session or completion summary:

> Continue \`MohammedTeir/deepseek-harness\`. Read \`DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md\`, \`ANDROID_COMPLETE_ROADMAP.md\`, \`ANDROID_DETAILED_TASKS_CHECKLIST.md\`, \`ANDROID_PORT_STATUS.md\` and current gate reviews. Verify actual latest HEAD/branch/working tree and do not trust dated snapshot values. Report accepted phases/gates with precise device/test scope. Identify first open P0 task and execute it. Keep original Harness engine/UI architecture and strict native authorization. Never equate host tests or APK builds with device execution. Update evidence, checklist and status accurately; do not merge development branch, create PR or publish release without explicit approval.

## References

- [Master Prompt — authoritative](DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md)
- [Complete roadmap and future plans](ANDROID_COMPLETE_ROADMAP.md)
- [Current implementation state](ANDROID_PORT_STATUS.md)
- [Implementation plan](ANDROID_IMPLEMENTATION_PLAN.md)
- [Gate 2 accepted bounded proof](ANDROID_GATE2_REVIEW.md)
- [Gate 3 selected-device review](ANDROID_GATE3_REVIEW.md)
- [APK #7 phone qualification guide](apps/android/execution/TERMINAL_ANDROID_PROOF.md)
- [Android test plan](ANDROID_TEST_PLAN.md)
- [Security model](ANDROID_SECURITY_MODEL.md)
- [Termux optional provider documentation](ANDROID_TERMUX_INTEGRATION.md)
- [Root optional provider documentation](ANDROID_ROOT_INTEGRATION.md)
