# DeepSeek Harness Android — Complete Phases, Gates & Long-Term Product Roadmap

> **Status:** Living project handoff / completion reference  
> **Baseline:** 2026-11-13; development branch \`feature/android-port\` at \`4496650e83bf16ce85eae9fd4e589270116ec742\`; default branch \`master\`  
> **Authority:** [DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md](DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md) is authoritative. This document expands and tracks it; it **does not** modify, override, silently waive, or replace its requirements.  
> **Related execution tracker:** [ANDROID_DETAILED_TASKS_CHECKLIST.md](ANDROID_DETAILED_TASKS_CHECKLIST.md)  
> **Working evidence:** [ANDROID_PORT_STATUS.md](ANDROID_PORT_STATUS.md), [ANDROID_IMPLEMENTATION_PLAN.md](ANDROID_IMPLEMENTATION_PLAN.md), [ANDROID_GATE1_REVIEW.md](ANDROID_GATE1_REVIEW.md), [ANDROID_GATE2_REVIEW.md](ANDROID_GATE2_REVIEW.md), [ANDROID_GATE3_REVIEW.md](ANDROID_GATE3_REVIEW.md).

## 1. Purpose and non-negotiable product definition

The product must be a **standalone Android 10+ (API 29+) ARM64 APK** that ports the **real DeepSeek Harness**, not a new product inspired by it. Required end state:

- **Original upstream Web frontend**, built from original sources, shown locally inside Android WebView. Preserve recognizable design, routes, chats, settings, tools, history, streaming, and compatible features; implement mobile adaptations rather than rewriting the UI.
- **Authentic on-device Harness agent**, profiles, agent loop, models/provider abstraction, tool registry, approval services, sessions, events, plugins/MCP/workflows where feasible. No fake engine, desktop dependency, required external server, required Termux, or replacing real agent behavior with mocks.
- **Real local execution and interactive terminal** using Android-supported process/PTY infrastructure; honest per-device command/capability reporting; real streams, exit, cancel, timeouts, and cleanup. A fixture that executes one fixed command is proof of only that scope.
- **Trusted native authorization**: no agent/plugin self-approval, exact-request binding, deny/mutation/replay protections; additional constraints for privileged/root actions; no silent privilege escalation or arbitrary shell/root fallback.
- **Reliable platform integration**: session persistence/recovery, scoped storage/SAF, Android Keystore credentials, lifecycle/background constraints, notifications/permissions, file pickers, logs, error diagnostics and resource limits.
- **Explicit optional providers**: external Termux and Root are *optional separate integration tracks*, not substitutes for the embedded runtime. Original spec still places their implementation in Phase 5 and root enforcement in Gate 5; do not discard them merely because an earlier Gate passed.
- **Tested, traceable distribution**: real device/emulator evidence, Android 10 and newer coverage, security and reliability acceptance, source-linked reproducible artifacts, license review and release approval.

The master prompt's section 17 **Definition of Done** remains the final end-to-end completion contract. A passing diagnostic APK, a successful Gradle build, or a single-phone acceptance test does not equal product completion.

## 2. Essential distinction: Phases versus Gates versus APKs

**Phases** are the ordered engineering workstreams **Phase 0, 1, 2, 3, 3A, 4, 5, 6, 7** (nine labels). **Gates** are six *blocking technical acceptance checkpoints* in master section 15A. **APK #1…#7** are incrementally packaged *test artifacts*, not phase numbers. Gate 4 maps most directly to Phase 3A; Gate 5 spans root/approval/security work in Phase 5/6; Gate 6 relates to Phase 6/7 and product release readiness. The gate sequence may constrain claims even where independent phase work happens in parallel.

Status vocabulary: **VERIFIED** only when supported by executed evidence; **IMPLEMENTED** is code present but not fully proven; **IN PROGRESS**, **BLOCKED**, **NOT STARTED**. Mark *scope* next to every VERIFIED claim: device, API, ABI, path, exact operation, test type, and evidence source.

### Snapshot table (2026-11-13, before APK #7 phone report)

| Workstream | Evidence-based status | What is **not** implied |
| --- | --- | --- |
| Phase 0 / fork and baseline | VERIFIED | Nothing about Android runtime |
| Phase 1 / source/dependency audit | Gate 1 ACCEPTED; review and audit produced | Every platform-specific package works on-device |
| Phase 2 / embedded runtime and Harness | Gate 2 ACCEPTED **for bounded local-engine proof** on user-tested Android 11 ARM64 | Real model inference, original chat UI, hostile-plugin isolation, full lifecycle |
| Phase 3 / local process, PTY, original terminal | **IN PROGRESS**; prior fixed process/PTY and original node-pty phone proofs accepted; APK #7 built, not phone-verified | General shell, full interactive terminal integration or API-wide support |
| Phase 3A / original frontend and secure transport | NOT VERIFIED as integrated Android UI | Web UI inside a diagnostic APK or authentic streaming |
| Phase 4 / platform adapters and feature restoration | NOT COMPLETE | SAF/Keystore, complete sessions/models/plugins/MCP/workflows |
| Phase 5 / optional Termux and Root | NOT IMPLEMENTED as full providers | Root/Termux already included because a process can spawn |
| Phase 6 / hardening and device matrix | NOT COMPLETE | Production-grade security or compatibility |
| Phase 7 / distribution | NOT COMPLETE | Publishable release readiness |
| Gate 1 | ACCEPTED | Runtime automatically proven |
| Gate 2 | ACCEPTED within bounded scope | Model provider request verified |
| Gate 3 | IN PROGRESS | APK #7 success automatically closes Gate 3 |
| Gate 4 | NOT VERIFIED | WebViewAssetLoader alone establishes secure RPC |
| Gate 5 | NOT VERIFIED | A native approval dialog proves complete root security |
| Gate 6 | NOT VERIFIED | Debug APK equals release readiness |

**Git note:** PR #3 was merged into \`master\` on 2026-11-13 as commit \`9ba372e84aeb9e5754c0a5f8d2c9ca22ac4c27a5\`. The development branch subsequently gained 9 commits and remained ahead of master at the baseline. Future development merges/PRs/releases require explicit authorization. Adding planning documents to master is not authorization to merge feature code.

## 3. What has actually been achieved — historical evidence

### 3.1 Phase 0 and Gate 1
- Verified correct fork and upstream identity, source baseline, branch and lockfile.
- Audited broad pnpm dependency graph, native modules and binaries, frontend/backend routes and Android ABI/runtime constraints.
- Chosen feasible bounded packaging/Node experiments; Gate 1 review accepted the investigation and experimental strategy.
- **Limit:** manifest/dependency mapping is not on-device execution for every feature.

### 3.2 Phase 2 / Gate 2 — accepted bounded local-engine capability
- Embedded **Node.js 24.22.1, Android ARM64**, actual runtime API probes and genuine Harness SDK/profile initialization on the reported **Redmi Note 8 Pro, Android 11 / API 30**.
- Fixed Android hardlink publication failure in session storage using tested **\`renameat2(RENAME_NOREPLACE)\`** for the scoped original JSONL publication paths. APK #1 atomic-publication phone evidence, APK #2 profile/session persistence and restart evidence, and native no-replace adapter integration recorded.
- Original Harness session creation and persisted JSONL recovery across Node runtime restart and repeated invocations; controlled manual force-stop/reopen reported, not equal to demonstrated process death mid-write/power loss.
- **APK #3** original registered tool + ApprovalService + human native Deny/Approve + fixed \`/system/bin/pwd\`, one native process, real output/exit, denial/mutation/replay/concurrency protection and recovered original approval/command records.
- Gate 2 **accepted for these local-engine conditions** in [ANDROID_GATE2_REVIEW.md](ANDROID_GATE2_REVIEW.md).
- **Not proven:** provider/model round trip without authorized test credentials, model-generated tool calls, genuine original chat UI display, comprehensive malware-resistant same-UID isolation, complete app restart and OS-kill reliability.

### 3.3 Phase 3 / Gate 3 — substantial but partial
- **APK #4:** fixed OS process/shell/PTY capability suite verified in user-reported physical Android 11 result: stdout/stderr, stdin, nonzero exit, missing executable, TERM/KILL, timeout/reap, cooperative descendant cleanup, fixed \`/system/bin/sh\`, PTY input/resize, and exact Toybox tool presence.
- **APK #5:** fixed approved \`pwd\` routed through original \`SubprocessRuntime\` service on phone with original approval/session persistence (limited, not generic subprocess API proof).
- **APK #6:** original **node-pty** source qualified as Android native addon on phone; input/resize, nonzero exit, Ctrl-C/TERM and timeout/KILL tested with a fixed fixture. A host-only prototype for original terminal handle follows; not general shell support.
- Original terminal registry, Agent ownership, native terminal allocation authorization, private broker, exact approval relay and host integration have since been implemented and checked in bounded scope.
- **APK #7** at \`4496650e\`: original registry/tool/ApprovalService + native human approval + fixed Android PTY path packaged, signed debug build/lint/tests/inspection reported passing; **physical APK #7 execution still BLOCKED at baseline**.
- **Limit:** all physical reports are user-reported and scoped; no claim of independent ADB attestation. Android 10/API 29, newer versions, OS death, arbitrary descendants, foreground/job-control correctness and general terminal/shell remain open.

### 3.4 Artifacts and test limitations
- APK #7 build record: \`apps/android/evidence/runtime-terminal-apk7-build.json\`; delivery: \`apps/android/evidence/runtime-terminal-apk7-delivery.json\`.
- APK #7 main APK SHA-256 recorded: \`c55fde2fca0ef5cc6732c267580b736acf22c808ab822cdc1653933a2ef73da0\`. Version \`0.1.13-original-terminal-proof\`, min SDK 29, target SDK 36, ARM64 debug package. The record states 48 host tests and 20 script tests pass; Android debug and androidTest APK assembly and lint pass. **These are not Android APK #7 execution results.**
- Related protocol: [apps/android/execution/TERMINAL_ANDROID_PROOF.md](apps/android/execution/TERMINAL_ANDROID_PROOF.md). The external upload in the delivery record is time-limited; rebuild/re-upload if expired and verify SHA-256 before installation.
- For all proofs, distinguish code/host test, cross-compilation, emulator, user-reported physical test, direct ADB instrumentation and security attestation. Preserve raw failures.

## 4. Detailed execution phases and definitions of done

### Phase 0 — Fork verification and baseline (VERIFIED)
**Outcome:** correct repository, provenance and reproducibility baseline. Inspect remotes and Git refs; preserve upstream history; pin toolchains/source/dependency graph; document security advisories and risk ownership. **Done:** audit artifacts and reproducible baseline accepted. **Ongoing:** refresh baseline on upstream changes; don't silently replace previously accepted baseline.

### Phase 1 — Architecture/dependency feasibility (Gate 1 ACCEPTED)
**Outcome:** explicit compatibility matrix and reasoned runtime choice. Audit C/C++/Rust addons, Node APIs, Bionic/glibc boundaries, Android executable/W^X packaging, page-size assumptions, Web frontend routes/RPC and plugin closures. Decide minimum compatible profile and mark unsupported plugins. **Done for initial Gate:** inspected matrix, selected feasible bounded strategy, accepted Gate 1 review. **Ongoing:** repeat audits for newly enabled feature packages and Android versions.

### Phase 2 — Real embedded Harness proof (Gate 2 bounded ACCEPTED)
**Outcome:** honest local engine proof. Embedded Node, original SDK/profile, reliable JSONL, session restart, original registered tool/approval, fixed approved harmless process. **Demonstrated in accepted device scope.** **Remaining cross-phase:** real LLM/model round trip when credentials available; general tool paths only after respective phase gates; persistent UI interaction happens in Phase 3A/4. Never reinterpret this bounded success as final product integration.

### Phase 3 — Local processes, PTY and embedded terminal (Gate 3 IN PROGRESS)
**Objective:** turn selected-device process/PTY proofs into honest, original Harness terminal integration and a capability-aware embedded toolchain.

**Required work:**
1. **Immediate: APK #7 physical test.** Preserve existing app data; install verified update; run \`RUN ORIGINAL TERMINAL + NATIVE APPROVAL\`; Deny first prompt, Approve Once second; capture full JSON, hashes, device info, actual PTY I/O/resize/exit, native process/UID, approval denials, replay/mutation resistance and persisted/recovered original events. Failures are useful evidence, not to be edited away.
2. Validate original \`TerminalSessionService\`, terminal registration/Agent ownership, allocation rollback and cleanup, actual PTY factory, buffered/streamed output and input, terminal resize and lifecycle behaviors under real phone.
3. Define truly supported subprocess/shell contract: argv/cwd/env, input/outputs, live streaming, stderr merge for PTY, nonzero exits, timeout, signals, cancellation, child and descendant reaping, job-control/foreground limitations and resource budgets.
4. Test real Android shell/Toybox availability per device and actual tool functionality, distinguishing existence from command feature support. No assumption of Bash/GNU/Python/Git/npm/OpenSSH. Audit any bundled utility before shipping.
5. Harden fixed proof into bounded safe production adapter only after correct authorization, lifecycle and terminal semantics are established; preserve original Harness registry and service contracts.
6. Device matrix: Android 10 API 29 and at least one recent ARM64 version, different kernels/filesystems, relevant 16 KB page-size environment; separate emulator from physical tests.
7. Record expected unsupported features visibly and do not silently fall back to Termux/root.
8. Identify clear narrow Gate 3 acceptance vs broader optional shell product scope. Do not mark Gate 3 PASS just because APK #7 compiles or a fixed fixture succeeds.

**Acceptance:** documented supported process/PTY operation on identifiable Android devices with correct observable streams/exit/cancellation and capability gaps; original terminal path demonstrated in actual Android runtime, with every remaining device/lifecycle limitation explicitly tracked.

### Phase 3A — Original frontend, secure origin & end-to-end streaming (Gate 4)
**Objective:** run the **original upstream UI** in the APK and connect it securely to authentic on-device Harness.

**Engineering deliverables:**
1. Inspect original \`apps/web\`, \`packages/client\`, routers, resources, Vite/static asset paths, WebWorkers, application routes, network/RPC/SSE/WebSocket paths.
2. Compile original UI; package assets in APK without external hosting; keep upstream visual identity, screens, icons, fonts, themes and responsive elements.
3. Use AndroidX \`WebViewAssetLoader\` where suitable; default virtual HTTPS origin is **\`https://appassets.androidplatform.net\`**. Configure restricted SPA fallback only for actual app routes; never return HTML for nonexistent assets or API calls.
4. Design and test local authenticated frontend↔runtime transport (RPC, WebSocket/SSE as required). Secure origin, session-bound tokens, request authentication, CORS/CSP, CSRF/cross-app/cross-origin defenses and local endpoint lifecycle. Avoid public unauthenticated listeners or broad JS bridges.
5. Verify login/session readiness and agent state, live streamed messages, real agent turns, tool approval, actual local command output and session history using original UI; real model inference only when authorized credentials are available.
6. Mobile readiness: Android back/deep links, IME/keyboard resizing, rotation, touch gestures, terminal keyboard/copy-paste, safe areas, accessibility, system bars, file pickers and errors/offline conditions.
7. Test WebView navigation to untrusted content, WebSocket origin spoofing, path traversal, malformed asset routes, reconnect/resume and stream backpressure.

**Acceptance / Gate 4:** original Web frontend runs and navigates on Android; authenticated transport and real session/agent/tool streamed state verified on-device, not screenshots/mocks.

### Phase 4 — Android platform adapters and full Harness feature integration
**Objective:** connect original backend/frontend to Android system services and restore compatible features.

**Deliverables:**
1. SAF document read/write/import/export, URI permission persist/revocation, secure app-private storage, filesystem adapter, correct file picker and share/export integration.
2. Credentials: Android Keystore-backed secret protection, storage/encryption lifecycle, secure API-key input, zero sensitive logging/export/WebView exposure, provider health checks and rotation/clearing.
3. Runtime/service lifecycle: startup/health/shutdown, foreground-service and notifications compliance, app background restrictions, OS kill/restart/reconnect, interrupted operations, lock/persistence cleanup and battery-aware behavior.
4. Preserve original model/provider selection, real authorized network API requests, streaming, retries/rate-limits/usage accounting, tool calling; not one hardcoded LLM vendor. No test credentials committed.
5. Sessions, settings, themes, history, import/export, workflows and original plugin lifecycle; Android compatibility matrix for each plugin and platform-dependent feature.
6. MCP: distinguish remote HTTP/streamable MCP from local stdio subprocess servers; verify actual compatible launch/network/permissions and disclose unsupported ones.
7. Terminal integration exposed through original UI with accurate capabilities and error diagnostics; do not bypass prior native approval policies.
8. Android intents, package visibility, notifications, connectivity, permissions, file sharing and appropriate platform APIs.
9. Any desktop/browser automation features must be explicitly classified SUPPORTED / ADAPTED / LIMITED / UNSUPPORTED, never silently replaced.
10. Maintain backward compatibility with upstream source, isolate adaptations, and test upgrades/migrations.

**Acceptance:** end-to-end functional integrated Android app for a defined, transparent supported feature set with real credential, storage, lifecycle, session, terminal and model flows.

### Phase 5 — Optional Termux and Root execution providers
**Objective:** expand capabilities while keeping a fully functional verified non-root, no-Termux base.

**Termux provider:**
- Detect installed/version/source/permissions and explicitly opt in; review supported official RUN_COMMAND/RunCommandService and Termux:Tasker interfaces, \`com.termux.permission.RUN_COMMAND\`, \`allow-external-apps\`, package visibility and return channels.
- Verify actual command execution/results/streaming if supported; respect Android app sandbox boundaries and never assume access to Termux private directories.
- Handle availability, consent, cancellation, disconnects, errors and version differences. Clearly label features unavailable due to API limitations. Never fake PTY streaming.
- Provider selector, setup/permissions diagnostics and capabilities integrated into original Harness UI.

**Root provider (ties directly to Gate 5):**
- Detect available root manager conservatively; user opt-in and separate explicit request-specific privileged approval, default-deny restricted operations.
- Trusted native authorization independent of agent-controlled arguments; canonical identity/scope/target/argv, immutable request and anti-replay, explicit escalation intent, cancellation and revocation, audit without secrets.
- Avoid a persistent unmediated root shell or direct agent/plugin \`su\`; no rooting/exploit/bypass, no silent embedded→root fallback.
- Test only on suitable authorized rooted test devices; handle unavailable/denied/revoked states correctly.

**Acceptance:** explicit capability-aware providers work where available and fail safely where unsupported; core app remains usable without either provider. Note: optional from a user-installation standpoint ≠ automatically removable from roadmap. Any deliberate deferral must be explicitly approved and reflected in release scope.

### Phase 6 — Hardening, adversarial tests, performance, reliability and compatibility (Gate 5/6 work)
**Objective:** prove the supported feature set is safe/reliable enough for a planned release.

**Security:**
- Agent/plugin/prompt-injection attack tests with malicious repo files, tools, web text and MCP results; command and root request mutation/replay, same-UID threat-model limitations, separate-UID attacks, transport-origin and token tests, protected credentials, untrusted HTML and WebView navigation, path traversal, plugin supply chain and dangerous permission cases.
- Deny destructive/system-critical operations under explicit policy; native enforcement must be more than a dialog.
- Track security audit findings, severity/mitigation/residual risk. Gate 5 can only be called accepted based on the *required* trusted root/prompt-injection evidence or explicitly documented support constraints under approved acceptance policy.

**Compatibility/reliability:**
- Android 10/API29 plus recent Android API; ARM64 emulator and physical device; 16 KB page-size compatibility if relevant.
- App/process service death, force-stop, active-write crash, restart, power-loss reasoning, storage exhaustion, sessions/migration repair, endpoint reconnect, background/foreground constraints, low memory.
- Terminal signal/descendant cleanup, PTY stop/resume/reconnect, provider denial, model request failures, file URI revocation, key loss and rotation.
- Record device-specific toolchain, Android WebView engine, ABI, OS, kernel, build SHA, battery/performance measurements, startup/memory, latency, CPU and streaming behavior.
- Regression suite, CI, negative cases, log privacy, policy boundaries and clear unsupported-feature diagnostics.

**Acceptance:** necessary security/functional/regression/device matrix evidence; no unresolved *critical* failure hidden by disabling checks. Gate 6 requires verified on-device scope, not universal unsupported claims.

### Phase 7 — Distribution, reproducible builds and release
**Objective:** traceable installable APK ready for approved distribution.

**Deliverables:**
1. Reproducible pinned source/build toolchain (Node, pnpm, JDK, SDK/NDK, dependencies); clean-checkout builds with recorded source and artifact fingerprints.
2. Signed release build strategy, signing/key custody, versioning, upgrade/data migration, APK/ABI/SDK compliance; debug/release parity checks.
3. CI pipeline generating inspectable artifacts: license notices, SBOM/dependency provenance where practicable, native ELF alignment/linking, package and signature checks.
4. Final QA: original frontend, local real Harness agent, valid authorized LLM round trip, explicit tool/root approvals, terminal, sessions across app restart, storage, negatives and device matrix.
5. User documentation: setup, keys, provider capabilities, Termux/root optional setup, permissions, backups, troubleshooting and known limitations.
6. Privacy/security and distribution policy review; release notes; final explicit go/no-go decision.
7. **Never publish GitHub Release, store listing, or merge development branch merely because docs/builds pass; require explicit owner approval.**

**Acceptance:** the approved feature-set meets master Definition of Done, Gate 6 review recorded, release artifact proven against tested devices and reproducible source.

## 5. Cross-cutting integration contracts to preserve

### Authenticity and evidence
- Use original engine, original Web UI and actual SDK/protocols. Existing "qualification" hooks may prove a bounded path but are not proof of model-generated agent work.
- Models and remote providers are optional external *inference services*, not a remote Harness backend. An offline local engine may need a network connection to an LLM.
- Test doubles must be labeled HOST-ONLY. A real host child command, emulator boot or APK build is **not** physical phone proof.
- Mark expected test-controlled false flags separately from actual accepted results. Never silently change validators/test assertions to make evidence green.

### Execution and provider boundaries
- Embedded unprivileged, external Termux, and root providers expose different command/FS/permission capabilities; no silent provider switching.
- Preserve original registered tools and schema validation; native grant is request-scoped and one-shot. Node/plugins under the same Android UID may remain untrusted; separate-UID isolation requires dedicated design and validation.
- Expose blocked/unavailable features, not empty success strings. Allow graceful fallback only when explicit, authorized and semantically correct.

### Storage and durability
- On Android no-replace publication, distinguish \`renameat2(RENAME_NOREPLACE)\` atomic namespace operation from power-loss durability; file and directory \`fsync\` ordering matters.
- Preserve JSONL history and temp cleanup across crash/restart. No unsafe check-then-\`rename()\` fallback and no false "all migrations/attachments audited" claim without call-site evidence.

### Lifecycle and Android policy
- Do not execute extracted binaries from app-writable storage if Android packaging/W^X prohibits it; use reviewed installed APK-native mechanisms.
- Respect foreground service/background limits, target SDK restrictions, SELinux, SAF and scoped storage. No permanent background-running guarantee.
- Keep logs privacy-safe with actionable exit/error telemetry.

## 6. Prioritized sequence from current checkpoint

**P0 — Immediate, blocking next step**
1. Obtain user-run **APK #7** complete physical result (or developer-controlled Android test), preserve raw data.
2. Verify installed APK/native fingerprints and source; inspect Deny→Approve Once, exact terminal allocation, one child, correct PTY input/output/resize, cleanup, negative requests and original recovered events.
3. Fix any phone-specific failure, rebuild/retake evidence as needed; update Gate 3 review with honest accepted scope.

**P1 — Finish meaningful Gate 3 terminal functionality**
4. Close remaining original terminal integration and safe process ownership/authorization gaps; define working embedded shell/tool limits.
5. Prioritize verified Android 10 and recent-device runs, and lifecycle/cancellation outcomes (some device-matrix work can continue in Phase 6).

**P2 — Deliver first genuinely usable application (Phase 3A)**
6. Build and embed original UI with secure HTTPS asset origin/SPA routing.
7. Wire authenticated streaming RPC and show *real* sessions, approvals, terminal and tool output in original chat/terminal panels.
8. Demonstrate real model turn with user credentials if available; otherwise mark clearly blocked.

**P3 — Full Android platform feature support (Phase 4)**
9. Implement SAF, Keystore, lifecycle and service adapters, real provider integration, sessions/settings/models, plug-in/MCP/workflow compatibility matrix and mobile UX.

**P4 — Optional provider tracks (Phase 5)**
10. Implement and qualify Termux and separately authorized Root if retained in product release scope; produce device-specific unsupported states and safeguards.

**P5 — Assurance and shipping (Phase 6/7)**
11. Security and prompt-injection adversarial assessment, device coverage, resilience/performance and recovery matrix.
12. Reproducible signed build, CI artifacts, licenses, final traceable tests and explicit authorized release decision.

## 7. What *not* to call complete yet

- Real LLM/provider execution or model-initiated tool calls.
- The original UI running in a WebView, session streaming and mobile UI functionality.
- Full general shell/Bash/GNU/Termux/root toolchain support, interactive terminal across all APIs.
- Storage Access Framework, Android Keystore secret handling, full plugin/MCP/workflow compatibility.
- Full lifecycle recovery (especially process death during writes), power-loss durability, hostile plugin isolation.
- Android 10 + newer Android compatibility matrix, release-grade security, production APK and distribution.

These do **not** invalidate accepted bounded proofs; they prevent scope inflation.

## 8. Future/backlog ideas after the required baseline

The following are **product enhancements**, not replacements for required master acceptance:
- Optional app-bundled verified utilities (Git, curl, Python, OpenSSH etc.) only after Bionic/ABI, licensing, executable loading, dependency, storage and device-support audits; opt-in and size/performance budget.
- Tools Manager with verified discovery/install/update/uninstall and capability-specific error messaging; *not* arbitrary external installer permissions by default.
- Provider-aware tool suggestions, accurate availability badges, support diagnostics and fallback recommendations in original settings UI.
- Dedicated security/process isolation for untrusted plugins, per-plugin permissions, signed supply-chain review and policy test suites.
- More robust terminal UX (sessions, scrollback, Unicode/RTL/IME, copy/paste, reconnect, multiple terminals, job-control capability disclosures).
- Offline guidance, local logs export, crash diagnostics with redaction, backup/restore and guided compatibility reports.
- CI device farm and per-Android-version regression matrix; profile size/startup/memory/battery instrumentation.
- Accessibility, internationalization, tablet layouts and polished responsive UI *within the original design system*.
- Long-term upgrade strategy from upstream Harness versions, compatibility re-audit and migration testing.

**Prioritize feasibility and owner approval; do not invent promised features, performance metrics or delivery dates.**

## 9. Handoff protocol for future Codex/agent sessions

At every new session:
1. Read this roadmap, [ANDROID_DETAILED_TASKS_CHECKLIST.md](ANDROID_DETAILED_TASKS_CHECKLIST.md), the authoritative master prompt and the current \`ANDROID_PORT_STATUS.md\`.
2. Verify repo, actual default branch and working branch, current HEAD, uncommitted changes, latest PR/merge and build evidence; **never assume baseline HEAD remains current**.
3. Inspect real source, tests, recorded evidence and APK fingerprints; documentation may lag implementation.
4. Update checkbox statuses **only** after matching executed tests/recorded acceptance; add links, commit, device/API and exact limits.
5. Carry out the highest unblocked dependency-safe work. Do not skip physical-device checkpoints. If a test requires user phone, produce installable artifact and precise instructions; BLOCKED until a real result is received.
6. Preserve already accepted milestones and historical failures, avoid repetitive audit, avoid sweeping refactor.
7. Commit isolated changes to the authorized development branch; do not open PR, merge development changes to master or publish release without specific permission.
8. Publish a concise status handoff: current phase/gate, newly verified items, APK artifacts and checksums, blockers, next executable step, and unanswered product decisions.

## 10. Source-of-truth references

- [Master engineering prompt](DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md) — sections 0–17, especially section 15 (Phases), 15A (Gates), 17 (Definition of Done).
- [Current Android progress](ANDROID_PORT_STATUS.md).
- [Current implementation plan](ANDROID_IMPLEMENTATION_PLAN.md).
- [Gate 1 review](ANDROID_GATE1_REVIEW.md), [Gate 2 review](ANDROID_GATE2_REVIEW.md), [Gate 3 review](ANDROID_GATE3_REVIEW.md).
- [Terminal APK #7 instructions](apps/android/execution/TERMINAL_ANDROID_PROOF.md).
- [Terminal APK #7 build record](apps/android/evidence/runtime-terminal-apk7-build.json) and [delivery record](apps/android/evidence/runtime-terminal-apk7-delivery.json).
- [Security model](ANDROID_SECURITY_MODEL.md), [compatibility matrix](ANDROID_COMPATIBILITY_MATRIX.md), [Android build guide](ANDROID_BUILD_GUIDE.md), [test plan](ANDROID_TEST_PLAN.md), [Termux guidance](ANDROID_TERMUX_INTEGRATION.md), [Root guidance](ANDROID_ROOT_INTEGRATION.md).

**Revalidation rule:** This is a dated baseline document, not a live status oracle. Newer commits and accepted evidence may change the status; update this document and the checklist together without erasing the history.
