# DeepSeek Harness for Android — Codex Master Engineering & Implementation Prompt

**Development repository (existing fork):** https://github.com/MohammedTeir/deepseek-harness  
**Original upstream repository:** https://github.com/deepseek-ai/deepseek-harness  
**Project objective:** Port the existing DeepSeek Harness application into a standalone Android APK with its **actual original frontend**, a **locally executing Harness agent engine**, and Android-compatible execution infrastructure.  
**Target:** Android 10+ (API 29+), initially ARM64 (`arm64-v8a`).  
**Preferred architecture:** Kotlin Android shell + bundled original Harness Web UI in Android WebView + Android-compatible locally embedded Harness/Node.js runtime, subject to feasibility verification.

---

## 0. Role, operating instructions, and non-negotiable mission

Act as a principal Android platform engineer, Node.js/TypeScript runtime engineer, AI-agent infrastructure engineer, security architect, build/release engineer, and maintainer of a complex upstream-derived monorepo.

**Implement a genuine Android port of the existing DeepSeek Harness project. Do not rebuild a new application inspired by it.** Inspect code before planning changes, then implement incrementally with builds, tests, and recorded evidence. Prefer code reuse and compatibility adapters over replacing existing systems. Carry out available work directly in the checked-out fork; do not stop after producing documentation. Never claim that code, a build, an APK, or a device test works unless it actually does.

The project is independent from ORYN and must not reuse ORYN's source code, product naming, design, or requirements. The Android product should remain recognizable as DeepSeek Harness.

### Non-negotiable outcomes

- Reuse the **original Web UI source**, not a visual imitation and not a Jetpack Compose rewrite of its screens.
- Preserve the original Harness agent loop, model/provider abstractions, tool registry, sessions, plugin architecture, and workflows wherever genuinely compatible.
- Execute the agent **locally on the Android device**, not on a desktop, remote host, or required external Termux installation. Cloud LLM providers may still need network connectivity.
- Implement a real Android execution environment, not just a WebView displaying a UI.
- Provide an embedded terminal with actual command results; external Termux and root support are optional, independent providers.
- Use a trusted, backend-enforced authorization model for shell, filesystem, plugins, sensitive tools, and root commands.
- Produce Android APK artifacts, evidence-based test results, maintainable code, and documented limitations.
- Treat Android 10+ as the target, but report incompatibilities honestly rather than silently weakening the requirements.

---

## 1. Fork identity and Git workflow

**Work exclusively in my existing GitHub fork:** `MohammedTeir/deepseek-harness` (`https://github.com/MohammedTeir/deepseek-harness`). **Do not create another fork or repository.** The original `deepseek-ai/deepseek-harness` is upstream, not the write target.

Before any changes:

1. Verify the checked-out repo identity, working tree, branch, commits, and remotes (`git status`, `git remote -v`, `git branch -a`).
2. If `origin` is not my fork, stop destructive operations and correct the remote only when the checkout is verified to be the intended fork; otherwise report the mismatch.
3. Configure `upstream` as `https://github.com/deepseek-ai/deepseek-harness.git` when missing; do not overwrite a different remote without checking its purpose.
4. Record the exact fork HEAD and upstream baseline SHA; record the date/version, dependency lockfile and installed toolchain versions.
5. Preserve history, default branch, existing source files, CI, and unrelated work. Do not reset or overwrite uncommitted user changes.
6. Create or reuse `feature/android-port` as the main integration branch. Use reviewable feature branches/PRs against **my fork** as appropriate.
7. Do not push to upstream, force-push, auto-merge, publish a GitHub release, or expose signing credentials without my explicit authorization.
8. Preserve the upstream license and applicable third-party notices. Assess additional licenses for distributed binaries, Termux-related integrations, and native libraries.
9. Isolate Android-specific implementation so future upstream merges remain practical. Keep a patch inventory and regression checks.

Use GitHub Actions in my fork for build/test artifact workflows; do not replace unrelated upstream workflows unnecessarily. Do not publish a production release by default.

---

## 2. Inspect the actual repository before designing the port

Treat the repository source and manifests as authoritative; docs can be stale. Inspect at minimum, if present:

- Root `README.md`, `AGENTS.md`, `SAFETY.md`, `LICENSE`, `package.json`, package lockfile, workspace and TypeScript configs.
- `docs/architecture.md`, development and Web UI documentation, and the platform/build guides.
- `apps/web`, `apps/desktop`, `apps/desktop-host`, `apps/cli`.
- `packages/core`, `packages/client`, `packages/host`, `packages/llm`, `packages/terminal`, `packages/shell`, `packages/subprocess`, `packages/sandbox`, `packages/guard`, `packages/interaction`, `packages/session`, `packages/storage`, `packages/credentials`, `packages/boot`, `packages/extensions`, `packages/mcp`, and relevant dependencies.
- `native/system` and any host native addons.
- All build scripts, service bindings, RPC/WebSocket/event-stream transports, tool policies, plugin lifecycles, integration tests, and dependency package native hooks.

Determine and document:

1. Original Web UI entrypoint and production build output; its routes, styles, assets, dependencies, authentication, RPC and streaming contract.
2. Desktop Electron boot sequence and which Electron API surfaces are actually required by the frontend.
3. Harness local runtime entrypoint and minimum agent-capable dependency graph, including how profiles/bundles and Cordis plugins are initialized.
4. Agent → tool authorization → execution → result → UI round trip, including persistent session events.
5. Required Node.js version and actual `node:*` API dependencies; transitive native addons, subprocess patterns, binaries, database dependencies, PTY and worker requirements.
6. Plugins and MCP transports with desktop assumptions; sandbox functionality and limitations.
7. Android API restrictions at min SDK, target SDK, and recent Android versions, including executable code, file access, process backgrounding, package visibility, intent execution, root providers, and dynamic code loading.
8. Paths to reuse unchanged versus paths requiring platform abstraction, rebuild, or targeted replacement.

Create an evidence-backed compatibility table for every major feature: **REUSE DIRECTLY / ADAPT / REIMPLEMENT ADAPTER / BLOCKED / NOT YET VERIFIED**, with file paths, dependency evidence, test evidence, and remediation.

**Do not treat successful HTML rendering as proof that the backend works.** Do not assume Linux ARM64 executables work on Android, or that an npm module works on Android because it is JavaScript.

---

## 3. Architecture decision: minimize changes while preserving functionality

Preferred architecture, subject to proof of feasibility:

```text
Android APK (arm64-v8a)
├─ Native Android application shell (Kotlin)
│  ├─ Activity, WebView host, OS permissions, lifecycle, notifications
│  ├─ Secure runtime supervisor and Android adapters
│  └─ User-facing diagnostics and provider status
├─ Original DeepSeek Harness Web UI (built from existing source)
│  ├─ Original design system, chat, sessions, settings, plugins, tools
│  └─ Minimal touch/responsive and OS-integration patches
├─ Local authenticated UI ↔ Harness transport
│  └─ Preserve existing RPC/streaming contracts where possible
├─ Embedded, Android-compatible Harness runtime
│  ├─ Existing agent loop, Cordis plugin system, model adapters
│  ├─ Tools, permissions, sessions, workflows, settings, persistence
│  └─ Compatible embedded Node.js runtime and native dependencies
└─ Android execution/OS providers
   ├─ App-scoped shell & native process adapter
   ├─ App-private / SAF filesystem adapter
   ├─ Optional external Termux provider
   └─ Optional explicit root provider
```

Prefer Kotlin + Android WebView over Tauri Mobile or Capacitor **unless a demonstrated proof of concept yields a clear advantage** in runtime integration, upstream UI reuse, security, or maintenance. None of these frameworks automatically ports Node.js or native addons. Avoid rewriting the Harness agent in Rust, Kotlin, or a new TypeScript engine unless a specific component is demonstrably unportable; document deviations.

Separate frontend, runtime, transport, permission service, native OS adapters, and execution providers. Avoid privileged JavaScript APIs not strictly necessary. Use typed, versioned interfaces and structured errors.

**Critical distinction:** A native Android host containing a WebView can still be a real standalone Android app if its original frontend and real local Harness engine are both bundled and integrated. The WebView must not merely access a remote website or remote agent server.

---

## 4. Original UI: reuse source, preserve look and features

Use the **actual frontend source** from `apps/web`, `packages/client`, and related existing packages. Do not visually recreate the UI, rewrite the chat/settings pages in Jetpack Compose, or replace branding/components. Keep original fonts, icons, color themes, visual hierarchy, route structure, existing UI behavior, streaming, session history, plugin management, settings and model selection wherever working.

Ship compiled frontend assets with the APK and use a supported local-origin approach such as AndroidX WebKit `WebViewAssetLoader` when compatible with the app's routing and transport requirements. Reuse existing frontend RPC and event contracts and introduce the smallest possible adapter.

Make **only necessary** mobile changes: viewport breakpoints, narrow-screen navigation, touch targets, keyboard/IME resizing, copy/paste, safe areas/system bars, Android back button, portrait/landscape, accessibility, file picker, native share/export, terminal input, dialogs, and gesture handling. Keep mobile-specific changes isolated and ensure they do not regress desktop/browser UI.

WebView security requirements: prohibit arbitrary untrusted navigation to privileged origins; disable unneeded file/content access and unsafe debugging in release builds; constrain JavaScript bridges, use origin checks and explicit authorization, handle mixed content carefully, and do not expose API keys or privileged tool execution to arbitrary pages. If local loopback RPC is used, bind only to loopback, authenticate requests, defend against cross-origin/cross-app access, and use per-session tokens with controlled lifecycle. Evaluate WebView origin and WebSocket behavior explicitly.

UI proof: an installable prototype must display the **real upstream frontend**, preserve its design and navigate actual screens. Demonstrate what works and what requires the backend before claiming UI parity.

---

## 5. Local embedded Harness runtime (highest technical risk)

Run the real Harness engine **on-device**, without requiring a remote computer, another Android app, or Termux for core functionality. A cloud AI API is allowed for model inference; network availability should not be confused with backend hosting.

Audit the checked-out revision's Node.js engine requirement (the previously observed root manifest required Node >=24.9.0; verify current state). Identify a legal, reliable Android-compatible ARM64 Node runtime integration and validate required `node:*` APIs, native addons and dynamic libraries, PTY/processes, storage, worker threads, DNS/TLS, SQLite/databases, filesystem and package loading. Ordinary desktop Node releases or GNU/Linux ARM64 binaries are **not assumed** to work on Android's Bionic libc and sandbox.

Android executable restrictions matter: follow supported native-library/APK packaging and actual platform rules for target SDK; **do not rely on extracting executables into writable app-private storage and `exec`-ing them**, and do not bypass integrity or code-loading restrictions. Investigate NDK cross-compilation and compliant packaging, and record verifiable device test results.

Implement runtime lifecycle via a well-scoped Android supervisor/service with startup/ready/health/error/shutdown events, thread/process isolation as appropriate, log collection with secret redaction, cancellation, cleanup, crash restart policies, config migration, and session recovery. Respect Android foreground-service types, notifications and background execution restrictions; never promise indefinite background execution.

Preserve Harness profiles/bundles, plugin registration, agent loop, model adapters, tools, event streaming, session persistence and configuration wherever possible. Avoid a hardcoded replacement loop. Build a narrow vertical slice before investing in full porting.

**Mandatory end-to-end runtime proof:** Android device/emulator launches embedded runtime → authenticates local frontend → initializes Harness agent → makes a real supported LLM request with user-supplied test credentials (when available) → requests tool approval → executes an innocuous `pwd`-equivalent command using the Android provider → returns real stdout and exit code to the **original chat UI** → persists session across app restart. If credentials are unavailable, validate local runtime/tool execution and mark external model integration unverified.

Do not equate a mock response with agent execution; label test doubles clearly.

---

## 6. Embedded terminal, local tools and package constraints

Implement a working terminal backend using compatible Android-supported mechanisms, not just a visual terminal. Reuse the Harness terminal frontend and tool contracts as much as possible.

Support, where feasible: shell execution, cwd, environment, stdin/stdout/stderr, streamed output, exit code, timeouts, cancellation, process termination and cleanup, PTY sessions, interactive input, command history, executable detection, resource limits, and failure diagnostics. Determine which shell and utilities exist on each supported device; avoid assuming GNU tools or `/bin/bash` exist.

Define a minimal verified embedded toolchain first. Consider compatible app-bundled, properly licensed native utilities (e.g., shell, curl, git, Python, OpenSSH) **only after** auditing ABI, packaging legality, native linking, resource impact, Android versions, licensing and execution permissions. No unreviewed arbitrary package installation or external scripts. For unsupported tools, clearly state the gap and offer an optional authorized execution provider rather than faking support.

Provide explicit separation between **embedded runtime**, **Termux external provider**, and **root provider**. Tool availability and filesystem visibility must be provider-specific.

---

## 7. Execution providers and Android platform adapter contracts

Implement explicit capability-aware interfaces compatible with existing Harness abstractions. For example, conceptually:

```ts
interface ExecutionProvider {
  id: string;
  getCapabilities(): Promise<ExecutionCapabilities>;
  isAvailable(): Promise<boolean>;
  execute(request: AuthorizedExecutionRequest): Promise<ExecutionResult>;
  cancel(executionId: string): Promise<void>;
}
```

Adapt to existing types rather than introducing duplicate engines. Each provider must report true capabilities and reasoned unavailable/error states. Never silently fall back from unprivileged to root execution. Keep privilege policy independent from frontend display.

Android adapters should cover process execution, app-private filesystem, SAF document URI grants, configuration, environment, network, Keystore-backed credential protection, notifications, package visibility, system-intent integrations, lifecycle and diagnostics. Minimize requested permissions; do not assume shared-storage access.

---

## 8. Optional external Termux integration

Implement integration **only as an optional provider**. The embedded runtime remains fully functional for verified core use without Termux installed. Detect compatible Termux installation/version/related components and supported communication mechanisms. Review official Termux and Termux:Tasker or RUN_COMMAND documentation and Android intent restrictions where applicable; use supported, permission-respecting inter-app APIs. Never assume access to Termux's private storage or cross-app executable paths.

Implement authorized request dispatch, results/streaming where supported, capability checks, timeout/cancel semantics where technically available, error mapping, disconnect/recovery, and clear setup diagnostics. If a given Termux API cannot provide necessary output or interactive sessions, document that limitation explicitly.

Show provider availability and selection in the **original Harness settings UI**, styled with the original design system. Never present Termux as a prerequisite for the embedded agent.

---

## 9. Optional root execution

Root must not be required. Detect available root authorization mechanisms conservatively (e.g., supported installed root managers) and distinguish UNAVAILABLE, NOT AUTHORIZED, AUTHORIZED, DENIED, REVOKED, ERROR. Never root the device, bypass Android controls, or attempt privilege exploits.

Before each privileged operation, enforce backend authorization showing exact commands, arguments, effective identity, affected resources when knowable, risks, and scope. Treat shell strings as potentially having indirect effects: do not promise perfect side-effect prediction. Require separate deliberate root consent; fail closed; bound sessions/scopes; allow revocation; log outcomes with redaction. Never let an LLM or plugin approve its own root privileges, and never silently escalate from embedded/Termux to root.

Restrict destructive/persistent system operations through explicit security policy independent of UI dialogs. Preserve normal non-root agent functionality.

---

## 10. Harness services: models, sessions, tools, plugins, MCP, workflows

Preserve the current Harness model/provider adapter framework and do not hardcode only one model vendor. Support provider selection, user-supplied API keys, streaming, tool calling, cancellation, connectivity checks, retry/rate-limit handling and usage display where supported. Avoid fabricated provider support. Use Android Keystore-backed protection where appropriate; do not expose keys to WebView debugging, logs, session exports, arbitrary plugins or untrusted web content.

Preserve event-based sessions/history, settings, conversation state, tool registry, approval pipeline, workflow engine, extensions and the plugin lifecycle. Reuse their existing protocols. Where specific desktop/native plugins cannot run on Android, mark each as supported/adapted/limited/unsupported and surface clear diagnostics. Do not crash the whole app when loading an incompatible plugin.

Assess MCP HTTP/streamable transport support separately from local stdio subprocess-based servers; the latter have platform and binary dependencies. Preserve actual supported features, not merely menu entries.

Browser/computer use, filesystem sandboxing and desktop automation may be incompatible with Android. Audit each separately and implement a truthful Android adaptation or declare a blocker. Do not claim universal feature parity without evidence.

---

## 11. Security architecture and untrusted input handling

Read and honor upstream `SAFETY.md`; assume developer-preview Harness is **not security-audited**. Android porting does not change that status by itself.

Treat LLM text, web pages, retrieved documents, repository files, plugins, MCP responses, terminal output and downloaded artifacts as untrusted. Tool execution requires a trusted enforcement layer that cannot be bypassed via UI scripting, prompt injection, JSON argument manipulation or plugin metadata. Enforce capability-scoped permissions, per-command review where needed, network/file boundaries, root separation, cancellation and audit events.

Review all local transports for origin checks, authentication, CSRF-like risks, WebSocket handshakes, app-to-app access and token handling. Use least privilege. Avoid broad storage permission and exported Android components unless needed and correctly protected. Test denial paths, unauthorized requests, credential leaks and malicious plugin attempts. Do not call something a secure sandbox without proving its boundaries; document residual risks.

---

## 12. Android UX and lifecycle requirements

Keep UI from upstream. Add only necessary OS integrations: native Android host, Splash/launch routing if necessary, runtime readiness/error overlay styled consistently, permission requests, file/document picker, Android back navigation, keyboard/IME behavior, touch, accessibility, notifications, theme/system bars, and safe rotation/state restoration.

Keep sessions intact through WebView/Activity recreation where possible. Respect Android background limits, foreground service restrictions, target-SDK policy and battery management. Explicitly report tasks interrupted by OS process termination and restore only what persisted safely. Never use hidden persistence bypasses.

---

## 13. Performance, reliability and observability

Optimize app startup, Node runtime loading, memory consumption, WebView memory, stream latency, PTY execution, battery, CPU, storage and plugin overhead. Prefer lazy services and limited concurrency where compatible. Collect measurements on identifiable emulator/device configurations and Android versions; never fabricate numbers.

Provide clear diagnostics for unsupported ABI, runtime failure, native linking error, missing capabilities, permissions denial, tool failure, model error, plugin incompatibility, Termux unavailable, root authorization failure, and insufficient storage. Logs must exclude credentials and sensitive file content by default.

---

## 14. Monorepo layout and build pipeline

Preserve existing monorepo structure. Prefer adding Android-specific components in `apps/android/` (adjust only after source audit):

```text
apps/android/
├── app/                 # Android Gradle/Kotlin host
├── bridge/              # authenticated UI ↔ runtime transport
├── runtime/             # Android-compatible Harness/Node launch
├── platform/            # OS adapters: storage, keystore, lifecycle
├── execution/           # embedded, Termux, root providers
├── native/              # NDK libraries and packaging support
└── tests/
```

Build original web assets using existing workspace build tools; bundle assets in APK. Build or acquire traceable Android-compatible runtime binaries according to license and reproducibility requirements. Integrate Kotlin, Android Gradle Plugin, SDK/NDK, signing configuration without committing secrets. Generate debug APK and release APK when build requirements are met; release signing may remain separately configured. Do not claim store eligibility or broad device compatibility without checks.

Create GitHub Actions workflows in my fork for lint/typecheck, frontend build, Android/runtime build, unit/integration tests, APK packaging and upload as run artifacts. Fail CI on meaningful failures. Never bypass checks or mark a workflow green based on mocked outputs. Do not publish releases without permission.

---

## 15. Execution roadmap and gated milestones

Proceed through the phases, implementing rather than only writing plans. Each phase must include tests, evidence, status and remaining blockers.

### Phase 0 — Fork verification and baseline
- Verify checkout/remotes/default branch/working tree, create or reuse `feature/android-port`.
- Record SHA, toolchain, dependency graph, upstream baseline and security notices.

### Phase 1 — Repository audit and Android feasibility
- Map frontend/backend/transport and native dependencies.
- Classify every major feature; identify critical blockers and accepted architecture.
- Produce compatibility matrix, security model and implementation plan.

### Phase 2 — Original UI on Android
- Build actual existing frontend, bundle it in Android WebView, preserve design.
- Validate navigation and touch/keyboard behavior; keep original frontend code.
- Build and inspect a debug APK; do not claim the backend works yet.

### Phase 3 — Local embedded runtime proof
- Bring up compatible Android ARM64 Node.js/Harness runtime.
- Test runtime process, session storage and ready/fail signals.
- Complete actual agent/tool-result vertical slice with approval and stdout in UI.
- Mark blockers accurately; don't replace Harness with fake backend.

### Phase 4 — Platform adapters and full integration
- Connect original UI to local session/agent/model/streaming interfaces.
- Add filesystem/SAF, credential store, terminal/PTY, subprocess and lifecycle adapters.
- Restore compatible settings, sessions, tools, workflows and plugins.

### Phase 5 — Optional execution providers
- Implement Termux provider with documented supported interfaces.
- Implement separately authorized root provider.
- Add capability-aware provider selection inside existing Harness UI.

### Phase 6 — Hardening and compatibility
- Functional, negative-path, security, lifecycle, performance and regression tests.
- Test Android 10 and a recent Android version, ARM64 emulator and actual physical device when available.
- Record unsupported or partially supported features.

### Phase 7 — Distribution
- Build reproducible debug APK; build release APK as configured.
- Validate install, launch, original UI, real local agent/tool execution, session recovery and security policies.
- Upload CI artifacts, update documentation; **do not publish a GitHub release without explicit authorization**.

If a phase is blocked due to unavailable equipment, SDK binaries, runtime compilation, network or credentials, document it and continue on independent work. Do not assert end-to-end completion before the vertical slice passes.

---

## 16. Required documentation and progress reporting

Create and maintain in the fork:

- `ANDROID_PORT_AUDIT.md`
- `ANDROID_ARCHITECTURE.md`
- `ANDROID_COMPATIBILITY_MATRIX.md`
- `ANDROID_IMPLEMENTATION_PLAN.md`
- `ANDROID_SECURITY_MODEL.md`
- `ANDROID_RUNTIME_GUIDE.md`
- `ANDROID_TERMUX_INTEGRATION.md`
- `ANDROID_ROOT_INTEGRATION.md`
- `ANDROID_BUILD_GUIDE.md`
- `ANDROID_TEST_PLAN.md`
- `ANDROID_PORT_STATUS.md`

For every milestone track objective, tasks, file paths, acceptance tests, test command/output summary, blockers, owner/decision if relevant, and next action. Status vocabulary: **NOT STARTED, IN PROGRESS, BLOCKED, IMPLEMENTED, VERIFIED**. Only VERIFIED after actually executing tests with evidence. Include commit SHA and environment in reports. Keep original frontend deviations and upstream patches listed explicitly.

---

## 17. Acceptance tests / definition of done

A complete Android port is **not achieved** until all applicable required tests pass; report any exceptions or unsupported features instead of calling the app complete.

- [ ] Development occurs in existing fork; upstream remote/history intact.
- [ ] App builds an Android APK from documented steps and installs on supported device/emulator.
- [ ] **Actual existing DeepSeek Harness frontend** ships in APK; original visual identity/screens are retained.
- [ ] UI works on touch screens, IME, and Android navigation.
- [ ] Real Harness agent runtime starts **locally** without another installed app/computer/server.
- [ ] A real model request succeeds when valid user-supplied credentials are available.
- [ ] Trusted permission gate requires explicit approval and rejects unauthorized tool/root actions.
- [ ] A real harmless `pwd`-equivalent command executes locally, and its stdout/exit status appear in original Harness UI.
- [ ] Sessions persist and recover after app restart.
- [ ] Android storage/SAF integration and Keystore-based credential protection are implemented and tested.
- [ ] Embedded terminal runs real supported commands, with cancellation, failure handling and output.
- [ ] Compatible Harness plugins/tools/MCP features function as demonstrated; unsupported ones are marked.
- [ ] External Termux is truly optional and its integration is tested where available.
- [ ] Non-root core operation works; optional root provider requires separate authorization and is tested only on suitable devices.
- [ ] Runtime lifecycle and crash recovery follow Android constraints.
- [ ] WebView/transport/tool security tests, negative cases and relevant regression tests pass.
- [ ] CI builds traceable APK artifacts; licenses and build instructions are accurate.
- [ ] Physical-device tests are claimed only when actually run; residual limitations documented.

---

## 18. FIRST EXECUTION: DO THIS NOW

1. Inspect my currently checked-out fork `MohammedTeir/deepseek-harness`; verify remotes, status and commit baseline. Do **not** create a new repo.
2. Configure `deepseek-ai/deepseek-harness` as `upstream` if missing, preserving `origin`.
3. Create/reuse `feature/android-port` without overwriting existing changes.
4. Read real source/docs, map the original frontend, local runtime, plugins, tool execution, RPC and platform dependencies.
5. Create the initial audit, Android compatibility matrix, risk register and implementation milestones.
6. Set up the smallest Android project necessary to run the **original** frontend locally in WebView; build/test it.
7. Investigate and prototype a **real embedded Harness runtime** on Android ARM64, honoring executable packaging and ABI restrictions.
8. Connect UI and runtime using the original protocol where possible; demonstrate harmless approved local command and real output in UI.
9. Incrementally implement verified compatible features, Android adapters, optional Termux/root, CI and tests.
10. Commit reviewable work and create a PR targeting **my fork** when appropriate. Do not auto-merge/publish releases.
11. At each milestone, report what actually ran, exact commands and results, what remains unsupported, and next runnable tasks.

**Do not stop after drafting a plan when implementation is possible. Do not fabricate build results, remove features silently, reproduce the UI in another framework, or call a WebView-only mock a complete port.**

### Final directive

**Deliver a maintainable, standalone Android adaptation of the actual DeepSeek Harness fork (`MohammedTeir/deepseek-harness`) using the original frontend source and authentic Harness agent architecture, with a verified local Android-compatible runtime, real terminal execution, carefully controlled optional Termux and root providers, secure platform integrations, and reproducible APK builds.**