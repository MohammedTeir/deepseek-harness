# Android compatibility matrix

## Summary

Classifications identify reuse or engineering work, not complete Android support. The user reports both v5 fixed Node API modes passing on Android 11/API 30, including an installed Node executable and actual child exit zero; no Harness profile or full-feature acceptance is claimed. See the [physical-phone results](apps/android/evidence/phone-v5-user-results.json) for evidence limits. The complete resolved graph, native dependency paths, platform metadata, installed payloads and remaining archive gaps are under [audit evidence](audit/android/EVIDENCE.md).

| Feature | Classification | Source evidence | Blocker / mitigation / acceptance evidence |
|---|---|---|---|
| Agent loop, tool/session event model | REUSE DIRECTLY | `packages/core/agent-loop`, `core/tools`, `core/session` | Preserve logic; real profile and tool round trip still unverified |
| Cordis profile/plugin composition | ADAPT | `apps/cli/src/profile-boot.ts`, `packages/boot/app-boot`, bundle YAML | Choose explicit Android composition; audit native and privileged plugins |
| Node >=24.9 | NOT YET VERIFIED | Root engines; Node 24 Android BUILDING guidance; v5 user phone results | Source build and fixed APIs pass in user-reported ARM64 execution, including installed child launch; broader Node APIs and authentic profile qualification remain incomplete |
| Original frontend source | REUSE DIRECTLY | `apps/web/src/main.ts`, `packages/client` | Linux Vite build passed; Android rendering/touch not tested |
| Frontend boot/dynamic modules | ADAPT | `packages/client/web`, `client/modules`, `host/frontend-static` | Preserve injections and plugin assets; static index alone is insufficient |
| Routes/assets/workers/fonts | ADAPT | Vite `base: './'`, explicit root/index static handler | Specify real routes and restricted fallback; reject missing assets/API paths; preview worker is not backend proof |
| HTTP/RPC/WebSocket streams | ADAPT | `client/connection`, `api/gateway/src/stream-protocol.ts` | `/api/remote.mux`; prove origin/cookies/token flow and restart streaming |
| Electron OS integrations | REIMPLEMENT ADAPTER | `apps/desktop/src/preload-app.ts` | File pick/save/share, clipboard, window/lifecycle; mark unavailable desktop features |
| JSONL sessions | ADAPT | `session/session-persistence-jsonl/src/lease.ts` | Native flock loader rejects Android; preserve locking/fsync/recovery semantics |
| SQLite storage | NOT YET VERIFIED | `storage/storage-sqlite/src/schema.ts`; v5 user phone results | In-memory SELECT passed in both fixed modes; actual persistent storage, concurrency and crash recovery remain untested |
| Native POSIX flock | ADAPT | `native/system/packages/entry/src/flock.ts`, `flock.c`, prebuild matrices | Original C source rebuilt; v2 failed symbol resolution. V5 user results report lock acquisition/contention/release passing in both modes; production Android selection and session integration remain absent |
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
| Workspace node-addon-system: glibc/musl/macOS matrix; platform guard rejects Android | ADAPT | Bionic binding plus selection and lock contention tests; retain BSD notices |
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

The successful v4 user result still reports /system/bin/app_process64 as execPath and childNodeLaunch not-tested. Existing SDK/managed-runner launch uses that path, so it is a concrete integration blocker. V5 packages the original Node main as an Android PIE for installer-owned execution and tests real child launch; the user reports installed parent/child execution passing on Android 11/API 30. The [architecture decision](ANDROID_ARCHITECTURE.md) selects this for the next bounded profile experiment, with JNI retained as a reference. A genuine sdk-minimal profile/session restart recovery passed on Linux through the public SDK, without model requests. It establishes the reference sequence, not Android compatibility. Original native selection, POSIX ownership fallbacks and bash/PTY defaults still need Android adaptation before that profile is enabled on-device.
