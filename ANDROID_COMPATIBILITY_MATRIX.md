# Android compatibility matrix

## Summary

Classifications identify reuse or engineering work, not complete Android support. The user reports both v5 fixed Node API modes passing on Android 11/API 30, including an installed Node executable and actual child exit zero; no Harness profile or full-feature acceptance is claimed. See the [physical-phone results](apps/android/evidence/phone-v5-user-results.json) for evidence limits. The complete resolved graph, native dependency paths, platform metadata, installed payloads and remaining archive gaps are under [audit evidence](audit/android/EVIDENCE.md).

| Feature | Classification | Source evidence | Blocker / mitigation / acceptance evidence |
|---|---|---|---|
| Agent loop, tool/session event model | REUSE DIRECTLY | `packages/core/agent-loop`, `core/tools`, `core/session` | Preserve logic; real profile and tool round trip still unverified |
| Cordis profile/plugin composition | ADAPT | `apps/cli/src/profile-boot.ts`, `packages/boot/app-boot`, bundle YAML | V7 packages original sdk-minimal with the no-execution overlay; isolated Linux relocation passed, Android startup pending |
| Node >=24.9 | NOT YET VERIFIED | Root engines; Node 24 Android BUILDING guidance; v5 user phone results | Source build and fixed APIs pass in user-reported ARM64 execution, including installed child launch; broader Node APIs and authentic profile qualification remain incomplete |
| Original frontend source | REUSE DIRECTLY | `apps/web/src/main.ts`, `packages/client` | Linux Vite build passed; Android rendering/touch not tested |
| Frontend boot/dynamic modules | ADAPT | `packages/client/web`, `client/modules`, `host/frontend-static` | Preserve injections and plugin assets; static index alone is insufficient |
| Routes/assets/workers/fonts | ADAPT | Vite `base: './'`, explicit root/index static handler | Specify real routes and restricted fallback; reject missing assets/API paths; preview worker is not backend proof |
| HTTP/RPC/WebSocket streams | ADAPT | `client/connection`, `api/gateway/src/stream-protocol.ts` | `/api/remote.mux`; prove origin/cookies/token flow and restart streaming |
| Electron OS integrations | REIMPLEMENT ADAPTER | `apps/desktop/src/preload-app.ts` | File pick/save/share, clipboard, window/lifecycle; mark unavailable desktop features |
| JSONL sessions | ADAPT | `session/session-persistence-jsonl/src/lease.ts` | V6 selected-mode user result passes the original lock entry; V7 user reaches session-recovery after two initializations, but the session is not found; v8 awaits Android diagnostics |
| SQLite storage | NOT YET VERIFIED | `storage/storage-sqlite/src/schema.ts`; v5 user phone results | In-memory SELECT passed in both fixed modes; actual persistent storage, concurrency and crash recovery remain untested |
| Native POSIX flock | ADAPT | `native/system/packages/entry/src/flock.ts`, `flock.c`, prebuild matrices | Original C source rebuilt; v2 failed symbol resolution. V5 user results report lock acquisition/contention/release passing in both modes; v6 adds fixed-SONAME Android ARM64 selection; updated selector and session integration still require device tests |
| Plain subprocess execution | REIMPLEMENT ADAPTER | `subprocess/subprocess-local/src/spawn.ts` | V5 user reports installed Node and child stdout/exit zero with non-root same-UID identity. General command policy, signals/cancellation and Harness provider integration remain unverified |
| Persistent terminal | ADAPT | `terminal/terminal-bash/src/config.ts`, node-pty payload | Default `/bin/bash`; prompt-control logic is bash/pwsh-specific; Toybox sh is not a drop-in equivalent |
| PTY backend | NOT YET VERIFIED | NDK `pty.h`; node-pty `binding.gyp`/prebuilds | API 23 symbols exist; glibc prebuilds unusable; actual SELinux/fork/PTY/cancel behavior needed |
| Filesystem and SAF | REIMPLEMENT ADAPTER | `packages/fs`, `attachment`, `workspace` | App-private paths versus document URIs; grants/revocation and path policy |
| Credentials | REIMPLEMENT ADAPTER | `packages/credentials`, `client/connection` | Keystore-backed storage and scoped native access; preserve new provider-generated masked previews without exposing full keys |
| Model adapters/streaming | ADAPT | `packages/llm` | Preserve vendors; qualify TLS, DNS, proxies, streaming and cancellation on device |
| Tool guards/approval semantics | REUSE DIRECTLY | `core/tools` pipeline, `guard`, `interaction` | Existing in-process policy is not isolation against malicious plugins |
| Trusted Android execution policy | REIMPLEMENT ADAPTER | Broker architecture recommendation | Canonical approved requests, immutable args, denial/replay/expiry and native enforcement tests |
| Workflows/background jobs | ADAPT | `packages/workflow`, `jobs`, `schedule` | Android interruption and persisted recovery; no indefinite execution promise |
| Office skills / Python | BLOCKED for unqualified local execution | `packages/bundle/web-app/cordis.patch.yml` | Non-desktop composition expects user Python; no Android interpreter/toolchain verified |
| Plugin installation/extensions | ADAPT | `boot/plugin-manager`, `packages/extensions` | Reviewed APK-bundled set initially; native hooks/downloads not automatically supported |
| MCP Streamable HTTP | NOT YET VERIFIED | `mcp/mcp-client/src/transport.ts` | Network/auth/stream tests needed; does not require local server binary by itself |
| MCP stdio | ADAPT | Same transport file, SDK `StdioClientTransport` | SDK owns spawn outside Harness subprocess service; intercept/restrict separately |
| Linux Landlock sandbox | BLOCKED | `native/system`, `sandbox/sandbox-local` | No Android sandbox equivalence established; evaluate OS-enforced separation, not Linux assumptions |
| Desktop browser/computer automation | BLOCKED | `packages/browser-use`, `computer-use`, native driver packages | Desktop engines/X11/OS binaries unavailable as-is; explicit unsupported state |
| Optional Termux | NOT YET VERIFIED | Official RUN_COMMAND API | Optional inter-app provider only; permissions/result/cancel/version tests |
| Optional root | NOT YET VERIFIED | Master Gate 5 | Disabled until native authority and adversarial tests; never a core prerequisite |
| Foreground/background lifecycle | REIMPLEMENT ADAPTER | Android foreground-service/type/background limits | Select valid service type and bounded operation behavior; test process death/recovery |

## Transitive native and binary families

[Every locked platform condition and inspected binary](audit/android/package-inspection.json) and [paths from product/build roots](audit/android/native-dependency-paths.json) accompany this review. Registry-only entries are marked uninspected; the table groups related packages without dropping their graph nodes.

| Family / actual evidence | Android assessment | Required treatment |
|---|---|---|
| node-pty 1.2.0-beta.15: Linux ARM64 `pty.node` needs `libutil.so.1`, `libstdc++.so.6`, `libgcc_s.so.1`, `libpthread.so.0`, `libc.so.6`, `ld-linux-aarch64.so.1` | BLOCKED as shipped | Qualify source rebuild/loader and persistent shell semantics; do not copy GNU/Linux prebuild |
| Workspace node-addon-system: glibc/musl/macOS npm matrix; experimental carrier loader accepts Android ARM64 | ADAPT | Bionic binding plus selection and lock contention tests; retain BSD notices |
| Koffi 3.1.1: C/C++ source and cnoke install hook | ADAPT / conditional | JSONL Windows write-through path uses it lazily; do not force-load on Android; other consumers need individual audit |
| sharp 0.35.5 and @img platform/libvips packages | NOT YET VERIFIED | Image/provider reachability and native backend must be qualified; no assumed Android libvips |
| @earendil-works/pi-tui: ARM64 Linux X11 addon requires `libxcb.so.1` | BLOCKED for desktop TUI native features | Separate optional backend/transitive UI helpers from model API support |
| bare-fs/path/url: bundled Android `.bare` ELF exists; bare-fs Android ARM64 links `libm.so`, `libdl.so`, `libc.so` | NOT YET VERIFIED | Bionic payload presence does not make Bare-runtime addons Node N-API compatible |
| @openai/codex, Claude agent SDK, @botiverse/oar, @vscode/ripgrep | BLOCKED where desktop-only binaries are selected | Preserve model adapter distinction; optional external coding-agent CLIs/binaries are separate capabilities |
| @trycua/cua-driver, @ubjs/node, sherpa-onnx and desktop automation/speech payloads | NOT YET VERIFIED / desktop variants BLOCKED | Review exact plugin reachability; Linux ARM64 metadata is not Bionic evidence |
| LibreOffice kit 0.2.3 platform engines and WASM, photon-node, pdfjs WASM, quickjs-wasi, Shiki WASM | NOT YET VERIFIED | LibreOffice WASM no longer has Linux-only installation metadata; host APIs, memory, fonts and assets still need Android tests; not a substitute Harness engine |
| esbuild, Rollup, lightningcss Android variants | NOT YET VERIFIED on device; host build tools reusable | Prebuild original UI off-device; do not ship compiler dependencies merely because Android variants exist |
| oxlint/tsgolint/tsgo, lefthook, jscpd, Electron/build helpers, app-builder, 7-Zip, fsevents | Host/build or platform-specific | Keep outside runtime APK unless a traced runtime dependency requires them; retain optional edges in audit |
| pnpm and node-addon-require-builtin/custom-loader | ADAPT | Packaging/runtime plugin-management paths differ from host build; current addon platform matrices omit Android |

## Platform restrictions

Android 10-targeted apps cannot execute files from writable app home using execve; use only a demonstrated supported APK binary loading/execution arrangement. Interpreted JS data and executable native payloads require separate treatment. No executable extraction workaround is recommended. Modern 16 KB devices require correct ELF and APK alignment, plus runtime testing rather than just an ARM64 file header.

Scoped storage/SAF gives URI grants, not arbitrary POSIX paths. Android 11+ package visibility affects optional Termux/root-manager discovery. Recent Android foreground-service types, permissions, start restrictions and timeouts constrain agent jobs; an app process may be killed. No broad storage permission or unlimited background service is assumed. Version-specific official sources and retrieval outcomes are in [platform references](audit/android/platform-references.json).

The new `packages/util/ripgrep` resolves packaged binaries only and uses the subprocess service. `packages/experimental/terminal-panel` adds a consumer of existing terminal services, not Android execution. Structured approval and PTY-unavailable errors in rc.2 improve failure reporting; native ABI and executable restrictions remain blockers.

## Android process identity

Node deliberately omits POSIX credential methods on Android. The user reports v3 failing at getuid after the lock stage. V4 records unavailable Node uid separately from native Android identity. Production ownership checks, including spill-local cleanup's geteuid fallback, need explicit Android adaptation; they are not verified by this probe.

## Runtime launch and profile evidence

The successful v4 user result still reports /system/bin/app_process64 as execPath and childNodeLaunch not-tested. Existing SDK/managed-runner launch uses that path, so it is a concrete integration blocker. V5 packages the original Node main as an Android PIE for installer-owned execution and tests real child launch; the user reports installed parent/child execution passing on Android 11/API 30. The [architecture decision](ANDROID_ARCHITECTURE.md) selects this for the next bounded profile experiment, with JNI retained as a reference. A genuine sdk-minimal profile/session restart recovery passed on Linux through the public SDK, without model requests. It establishes the reference sequence, not Android compatibility. The updated lock selector and no-execution overlay have host evidence only; see [runtime integration](ANDROID_RUNTIME_GUIDE.md#original-lock-selector-and-bounded-profile). Android packaging and profile/session execution are not verified. POSIX ownership-sensitive spill cleanup stays excluded, and bash/PTY features stay disabled in that bounded overlay.

## Original profile native-loader constraint

node-addon-require-builtin 0.1.9 and node-addon-native-custom-loader 0.1.9 are required during authentic Cordis/profile resolution. Classification: ADAPT / Android runtime NOT YET VERIFIED. The former's pinned original N-API source cross-compiles for Bionic and is packaged through a private fixed-SONAME Android carrier. The unchanged runtime probe must still qualify private Node symbols, context lookup and instruction-pattern validation on the actual shared Node build. V7 bundles a bounded observed startup/session image, not a complete plugin/model dependency distribution; see the [runtime guide](ANDROID_RUNTIME_GUIDE.md#v7-bounded-original-profile-image). Host and user-phone evidence remain separate.

V7's user transcript reaches original SDK session recovery after local initialization, so basic private-loader/profile startup has partial physical evidence on the reported phone. Persistent sessions remain BLOCKED: the new session is not found after restart. V8 adds acknowledged shutdown and actual storage/lookup diagnostics; its Linux permission-failure experiment is not an Android cause determination. No compatibility classification implies durable Android session recovery yet.

APK #1's same-directory native primitive is VERIFIED on the [reported Android 11 ARM64 phone](apps/android/evidence/atomic-poc-physical-review.json). The shared [APK #2 JSONL adapter](apps/android/runtime/ATOMIC_PERSISTENCE_ADAPTER.md) is IMPLEMENTED and host-tested, with Android native-addon execution and genuine session recovery NOT YET VERIFIED. API 29, newer releases, cross-directory fs-local/attachment publication and retained-source aliases remain unqualified; neither phase acceptance nor universal compatibility is implied.

## Gate 3 OS capability collection

| Capability | Classification | Evidence | Remaining acceptance |
| --- | --- | --- | --- |
| Native fork/exec pipes, separate streams, exits and bounded signals | NOT YET VERIFIED on Android | Actual Linux native suite; API 29 ARM64 APK #4 compilation | Phone execution and original subprocess adapter |
| PTY input, controlling TTY and resize | NOT YET VERIFIED on Android | Actual Linux openpty fixture; fixed Android diagnostic packaged | Phone permissions and behavior, original terminal integration |
| Android system shell and Toybox tools | NOT YET VERIFIED | Fixed /system/bin discovery and shell script in APK #4 | Actual phone results; no GNU/Bash assumptions |

The [process qualification guide](apps/android/execution/process-proof/PROCESS_CAPABILITY_PROOF.md) separates host evidence, synthetic parser tests and required physical-device evidence. This milestone does not enable the original Bash terminal backend or broaden agent command permissions.

## APK #4 physical capability update

The earlier Gate 3 NOT YET VERIFIED rows describe the build checkpoint. The [received Android 11/API 30 ARM64 report](ANDROID_GATE3_REVIEW.md) now verifies the fixed native process, shell script and PTY cases on that phone. General shell provider and original terminal backend remain ADAPT / NOT YET VERIFIED; API 29 and recent-device behavior remain NOT YET VERIFIED. Discovery is limited to twelve exact system paths.

## Original subprocess adapter

Original SubprocessRuntime fixed pwd integration is ADAPT / IMPLEMENTED with host tests; Android adapter execution remains NOT YET VERIFIED pending APK #5. Native process/PTY primitives retain their separate Android 11 acceptance. Raw streams, general commands, spills, custom environment, signal classification and the original interactive terminal backend remain unsupported by this bounded adapter. See [scope and evidence](apps/android/execution/SUBPROCESS_ADAPTER.md).

## APK #5 physical adapter update

Fixed pwd through the original SubprocessRuntime service is now VERIFIED on the reported Android 11/API 30 ARM64 device, based on [matching artifact and session evidence](ANDROID_GATE3_REVIEW.md). Earlier host-only rows retain the build checkpoint. General subprocess commands, streaming raw pipes, nonzero/signal classification, interactive PTY transport and original terminal backend remain unsupported or NOT YET VERIFIED as documented in the adapter guide.

## Original node-pty build result

Original node-pty 1.2.0-beta.15 C++ is ADAPT / cross-compiled for Android ARM64 API 29 without native source changes. Its Linux/Android branch uses forkpty; spawn-helper is Apple-only here. Original JavaScript plus the installed-addon loader pass real host tests. Android loading and behavior remain NOT YET VERIFIED pending APK #6. Stock GNU/Linux prebuilds remain BLOCKED; the [source qualification](apps/android/execution/NODE_PTY_QUALIFICATION.md) does not enable the original terminal backend.

## Original node-pty physical result

Original node-pty source/addon and its original JavaScript are VERIFIED for the five fixed Android 11 ARM64 cases in [the phone review](ANDROID_GATE3_REVIEW.md). The original SubprocessTerminalHandle adapter is IMPLEMENTED / host VERIFIED only, with Android activation blocked on authorization/ownership integration. General shell jobs, foreground inspection, descendants and other Android versions remain NOT YET VERIFIED.

## Terminal registry evidence level

The [fixed terminal registry qualification](apps/android/execution/TERMINAL_REGISTRY_QUALIFICATION.md) exercises the original profile, genuine Agent ownership, tool/approval pipeline, registry rollback and persisted history with real host PTY processes. Status: IMPLEMENTED with host verification; Android integration NOT STARTED. Automated host decisions are not native human approval. Android guards remain active and no APK changes are included. Gate 3 remains IN PROGRESS; next implement native-authorized allocation before a new physical-device checkpoint.
