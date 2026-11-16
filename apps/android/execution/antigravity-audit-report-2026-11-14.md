> **Archive note:** This report was supplied on 2026-11-14 and describes the earlier repository snapshot recorded below. Its P3A-001/P3A-002 status predates the host-observation work documented in the current [feature-branch checklist](../../../ANDROID_DETAILED_TASKS_CHECKLIST.md) and [feature-branch roadmap](../../../ANDROID_COMPLETE_ROADMAP.md). Its claim that no Kotlin source files exist is contradicted by [`OriginalWebActivity.kt` on `feature/android-port`](https://github.com/MohammedTeir/deepseek-harness/blob/feature/android-port/apps/android/app/src/main/java/io/github/mohammedteir/deepseekharness/OriginalWebActivity.kt). The supplied report body is retained with Git revision identifiers omitted to satisfy repository reference rules. Treat it as supplemental historical input, not current project authority.

---

# DeepSeek Harness Android Port — Comprehensive Audit Report

> **Date:** 2026-11-14T14:28 +02:00
> **Auditor:** MYTHOS-BB / Senior Android Systems Engineer
> **Repository:** `MohammedTeir/deepseek-harness`
> **Active Branch:** `feature/android-port`

---

## 1. Repository State

| Property | Value |
|---|---|
| **Current branch** | `feature/android-port` |
| **HEAD commit** | `revision omitted by repository reference policy` |
| **Working tree** | **Clean** (no uncommitted changes) |
| **Local branches** | `feature/android-port` (active), `master` |
| **Remote** | `origin` → `https://github.com/MohammedTeir/deepseek-harness.git` |
| **Feature → master divergence** | **22 commits ahead, 4 commits behind** |
| **Master HEAD** | `revision omitted by repository reference policy` |

> [!IMPORTANT]
> The actual repository state **exactly matches** the documented November 14, 2026 snapshot. No discrepancy.

The 4 commits on master not in feature are **documentation-only** (roadmap, checklist, task updates). The 22 feature-branch commits span from APK #3's subprocess routing through APK #8 lifecycle, original web asset packaging, and web-profile host bootstrap evidence.

---

## 2. Project Understanding

### Original DeepSeek Harness Architecture

The original Harness is an all-plugin Cordis agent framework with:
- **Agent Loop**: Cordis-based plugin composition with `SessionEventMap`, typed events, waterfall listeners
- **SDK**: Public `@deepseek-ai/dsh-*` packages with JSON-RPC SDK interface
- **Profile System**: Named profiles (`headless`, `web`, `sdk-minimal`) loaded from `cordis.yml` with overlay patches
- **Tool Registry**: Plugin-contributed tools with approval, execution, and event persistence
- **Session Management**: Durable JSONL sessions with atomic hardlink-based generation publication
- **Web Frontend**: Vite-built SPA at `apps/web/` served by the web profile with authenticated boot graph, client module batches, launch-token→cookie exchange, and SSE/WebSocket streaming
- **Command Execution**: Subprocess, terminal (node-pty), shell sandboxes, and process management packages
- **Native Addons**: Platform-specific `.node` binaries (flock, system utilities)

### Intended Android Architecture

The port aims for a standalone APK running:
1. **Embedded Node.js 24.22.1** (ARM64/Bionic) as a service process
2. **Original Harness engine** under the authentic profile/Cordis composition
3. **Android WebView** loading the original web frontend from `WebViewAssetLoader` HTTPS origin
4. **Authenticated local transport** between WebView and embedded Node backend
5. **Native Android approval broker** for tool authorization with one-shot grants
6. **Kotlin supervisor** managing Node lifecycle, process death recovery, and Android integration

---

## 3. Verified Progress

### Phase 0 — Baseline: ✅ VERIFIED
- Fork/upstream/branch/environment recorded; reproducible graph/index collection

### Phase 1 / Gate 1 — Audit: ✅ ACCEPTED
- 1,755 package identities, 8,836 dependency edges, 161 ELF payloads, 329 registry manifests inspected
- Host build, lint, tests, documentation all passing

### Phase 2 / Gate 2 — Bounded Local Engine: ✅ ACCEPTED (bounded scope)
**Evidence supports:**
- Embedded Node.js v24.22.1 running on ARM64 Android 11/API 30 (Redmi Note 8 Pro, user-reported)
- Original SDK/profile startup with genuine readiness evidence
- Atomic `renameat2(RENAME_NOREPLACE)` replacing hardlinks for Android persistence
- Session create, acknowledged shutdown, restart recovery, prior-invocation persistence
- Genuine registered Harness tool + native Deny/Approve + fixed `pwd` with stdout/exit
- Collision/mutation/replay/concurrent denial for one-shot approvals
- **APK versions 1–8** progressively qualifying capabilities

**NOT covered by Gate 2:**
- Model/provider round trip (no credentials available)
- Power loss / active-write termination
- Full app-lifecycle (process death) recovery
- API 29 / newer Android versions

### Phase 3 / Gate 3 — Process/Shell/PTY: 🔄 IN PROGRESS
**Verified (APK #4–#8, user-reported physical device):**
- Separate stdout/stderr, stdin, nonzero exits, launch errors
- SIGTERM cancellation, timeout/SIGKILL/reaping, cooperative descendant cleanup
- Fixed system-shell execution, PTY input/resize (node-pty)
- Original SubprocessRuntime service integration (APK #5)
- Original terminal registry + native approval (APK #7)
- Bounded wait timeout and SIGINT cancellation through terminal service (APK #8)
- Session recovery across runtime restart for terminal records

**NOT verified:**
- API 29 and recent Android targets
- Activity/OS process death cleanup
- General shell support (only fixed `pwd` and bounded fixtures)
- Orphan-descendant, resource/backpressure limits
- Malicious plugin isolation

### Phase 3A / Gate 4 — Original Web UI: 🔄 IN PROGRESS (early stage)
**Implemented:**
- Original Vite frontend assets built and packaged in APK under `assets/web/`
- `OriginalWebActivity` with `WebViewAssetLoader` serving `https://appassets.androidplatform.net`
- Static asset inspection (CSP, traversal rejection, no JS bridge)
- Linux-host web profile bootstrap: boot graph, client batches, launch-token→cookie exchange
- Linux-host bounded composition: 6 providers disabled, 74 client entries, origin denial (401/403)
- Isolated process-tree trace: successful absolute `openat` reads counted

**NOT verified (critical gaps):**
- No Android Web Runtime Image constructed
- No Android WebView-to-backend integration
- No original chat UI screens on Android
- No streaming model responses
- No Android device web profile startup
- No authenticated WebSocket transport
- No SPA routing
- `ui-open-in-app` client entry still active despite disabled provider
- Dependency trace covers only absolute `openat` reads — blind to relative paths, metadata, dlopen, imports

---

## 4. Incomplete Work

### Immediate (Gate 4 / Phase 3A):
| Task ID | Description | Status |
|---|---|---|
| **P3A-001** | Complete dependency observation (extend tracing beyond absolute openat) | NOT STARTED |
| **P3A-002** | State trace blind spots documentation | NOT STARTED |
| **P3A-003** | Separate runtime from test dependencies | NOT STARTED |
| **P3A-004** | Audit native artifacts (ABI/Bionic/linkage) | NOT STARTED |
| **P3A-005** | Narrow image policy (allowlist/denylist) | NOT STARTED |
| **P3A-006** | Build reproducible Web Runtime Image | NOT STARTED |
| **P3A-007** | Android runtime boot (physical device) | NOT STARTED |
| **P3A-008** | Capability-safe client graph (`ui-open-in-app` fix) | NOT STARTED |
| **P3A-009** | Authenticated HTTP transport | NOT STARTED |
| **P3A-010** | Authenticated WebSocket transport | NOT STARTED |
| **P3A-011** | Original UI integration | NOT STARTED |
| **P3A-012** | End-to-end Android acceptance | NOT STARTED |
| **P3A-013** | Gate 4 review | NOT STARTED |

### Remaining Gate 3 items:
| Task ID | Description | Status |
|---|---|---|
| P0-023–P0-032 | API 29/recent device, lifecycle, capability contract | BLOCKED |

### Later phases (4–7):
All NOT STARTED — SAF/filesystem, credentials/Keystore, lifecycle supervisor, plugins/MCP, Termux/root, security hardening, release packaging.

---

## 5. Documentation vs. Implementation Discrepancies

| Area | Documentation Says | Actual Code/Evidence Says | Result |
|---|---|---|---|
| **Git state** | HEAD `revision omitted by repository reference policy`, 22 ahead / 4 behind | Exactly matches | ✅ Consistent |
| **Gate 2** | ACCEPTED (bounded local-engine) | Backed by APK #1–#3 phone results + host tests | ✅ Consistent |
| **Gate 3** | IN PROGRESS, APK #7/#8 phone evidence | Evidence JSON files present, consolidated review exists | ✅ Consistent |
| **Gate 4 dependency trace** | "counts only successful absolute `openat` reads" | `audit_web_host_trace.py` L74: filters `O_RDONLY`, L80: requires `ROOT` prefix, L96: `relativePathsAndOtherSyscallsIncluded: False` | ✅ Consistent — limitation accurately documented |
| **Web Runtime Image** | Not yet a valid image; `sdk-minimal` ≠ web production image | No image construction code exists; `prepare_runtime_assets.py` packs only the bounded sdk-minimal closure | ✅ Consistent |
| **`ui-open-in-app` mismatch** | "client graph still exposed an active entry" | `web-bounded-profile.host.spec.mjs` L37-38: explicitly asserts `FiberState.ACTIVE` | ✅ Consistent — known issue |
| **6 disabled provider rows** | Subprocess, bash-sandbox, pwsh-sandbox, open-in-app, directory-picker, MCP manager | `web-host-bounded.patch.yml` disables exactly these 6 | ✅ Consistent |
| **Dashboard baseline vs. current** | Checklist says Gate 3 blocker is "APK #7 physical test" | APK #7 and #8 results are now accepted; blocker shifted to API 29/device coverage + Gate 4 work | ⚠️ Stale baseline — superseded by dated refresh section |
| **Native Kotlin source** | AndroidManifest declares 7 services + 2 activities | No Kotlin source files found in `app/src/main/java/` or `app/src/main/kotlin/` at depth 3 | ⚠️ Source may be deeper or generated — needs verification |

> [!NOTE]
> The discrepancy table is tight. The project documentation is unusually rigorous — every limitation is explicitly stated. The only stale item is the dashboard baseline in the checklist, which is correctly superseded by its dated refresh section.

---

## 6. Gate Status

| Gate | Status | Evidence Level |
|---|---|---|
| **Gate 1** — Architecture/Dependency Feasibility | ✅ ACCEPTED | Full audit with 1,755 packages, ELF inspection, host build/test |
| **Gate 2** — Embedded Runtime/Local Engine | ✅ ACCEPTED (bounded) | APK #1–#3 phone results, host tests, session recovery, approval denial |
| **Gate 3** — Native Subprocess/Shell/PTY | 🔄 IN PROGRESS | APK #4–#8 phone results on API 30; API 29 and lifecycle gaps remain |
| **Gate 4** — Original Web UI/Secure Transport | 🔄 IN PROGRESS (early) | Static assets packaged; Linux-host bootstrap only; no Android integration |
| **Gate 5** — Security/Authorization | ❌ NOT STARTED | Depends on Gate 4 completion |
| **Gate 6** — Release Readiness | ❌ NOT STARTED | Depends on all prior gates |

---

## 7. Phase Status

| Phase | Status | Notes |
|---|---|---|
| **Phase 0** | ✅ VERIFIED | Baseline preservation maintained |
| **Phase 1** | ✅ VERIFIED | Gate 1 accepted |
| **Phase 2** | ✅ ACCEPTED (bounded) | Gate 2 accepted within local-engine scope |
| **Phase 3** | 🔄 IN PROGRESS | Gate 3 has bounded phone evidence; gaps in device coverage |
| **Phase 3A** | 🔄 IN PROGRESS | **Next active work area** — P3A-001 is the continuation point |
| **Phase 4** | ❌ NOT STARTED | Platform adapters / full integration |
| **Phase 5** | ❌ NOT STARTED | Termux/Root providers |
| **Phase 6** | ❌ NOT STARTED | Security hardening / performance |
| **Phase 7** | ❌ NOT STARTED | Distribution / release |

---

## 8. Risks and Blockers

### Critical Technical Risks

1. **Dependency closure is unknown.** The current trace captures only absolute `openat` reads with `O_RDONLY`. Relative paths, `stat`, `access`, `faccessat`, directory enumeration, symlink resolution, dynamic imports, `dlopen`, child process executables, and configuration loading are all unobserved. A complete Web Runtime Image cannot be built without this coverage.

2. **Linux native addons are not Android-compatible.** The isolated trace identifies at least one `.node` addon from the Linux host build. These GNU/GLIBC-linked ELF binaries cannot be packaged for Android. Each native addon either needs an Android ARM64/Bionic cross-build or its provider must be disabled.

3. **`sdk-minimal` image ≠ web production image.** The existing `prepare_runtime_assets.py` packs the bounded `sdk-minimal` profile closure. The web profile requires additional runtime assets, frontend build output, configuration, and different provider composition. A new image construction pipeline is needed.

4. **WebView-to-backend authentication is undesigned.** The original web profile uses a loopback origin with launch-token→cookie exchange. The Android `WebViewAssetLoader` uses `https://appassets.androidplatform.net`, which is a different origin from the Node backend's loopback listener. Cookie scope, CORS, WebSocket upgrade authentication, and cross-origin policy all need a new transport design.

5. **No Android device for Gate 4 verification.** All prior phone evidence was user-reported manual testing, not developer-controlled ADB instrumentation. Gate 4 requires WebView integration testing that is harder to verify manually.

### Moderate Risks

6. **Disabled provider / active client entry mismatch.** The `ui-open-in-app` client entry is `ACTIVE` while its backend provider is disabled. This could surface misleading controls in the Android UI.

7. **API 29 and recent Android untested.** All phone evidence is from a single Redmi Note 8 Pro (Android 11/API 30). The target is API 29+, and newer Android versions may have different SELinux policies, storage behavior, or WebView versions.

8. **No model/provider credentials tested.** No real LLM API call has been made. Streaming, error handling, rate limits, and credential storage are entirely unverified.

### Process Risks

9. **User-reported evidence only.** No developer-controlled ADB instrumentation has succeeded. Phone results depend on user cooperation and are not independently reproducible.

---

## 9. Next Task: P3A-001 — Complete Dependency Observation

### Why P3A-001 is the correct next step

P3A-001 is the first task in the Gate 4 / Phase 3A critical path. It directly addresses the foundational gap: **we cannot build an Android Web Runtime Image without knowing which files the web profile actually needs at runtime.** Every subsequent P3A task depends on this:
- P3A-002 (blind spots) extends P3A-001's analysis
- P3A-003 (separation) requires P3A-001's data to distinguish runtime from test files
- P3A-004 (native audit) needs P3A-001's native dependency list
- P3A-005/006 (image policy/construction) are impossible without the dependency closure

### Existing observation state

The current `audit_web_host_trace.py`:
- Parses `strace` per-process trace files (`openat` only)
- Filters to `O_RDONLY` with absolute paths under the checkout root
- Identifies `.node` native addons
- Selects the web-profile process tree by PID ancestry (`clone3/vfork/fork`)
- Produces a JSON summary with explicit `relativePathsAndOtherSyscallsIncluded: False`

The [isolated trace](apps/android/evidence/original-web-profile-isolated-host-trace.json) and [bounded composition trace](apps/android/evidence/original-web-bounded-host-trace.json) exist with these limitations.

### What P3A-001 must add

Extend the trace auditor and capture to observe:
1. **Relative and absolute `open`/`openat`/`openat2`** (success + failure)
2. **Metadata: `stat`, `fstatat`, `access`, `faccessat`, `lstat`**
3. **Directory enumeration: `getdents`, `getdents64`**
4. **Symlink resolution: `readlink`, `readlinkat`, `realpath`**
5. **Dynamic imports: ESM `import()` and CJS `require()` resolution paths**
6. **`dlopen` and native addon loading**
7. **Child process executables and arguments**
8. **File descriptor inheritance**
9. **Configuration and environment-dependent loading**

---

## 10. Proposed P3A-001 Implementation Plan

### Files likely to change

| File | Change |
|---|---|
| `apps/android/scripts/audit_web_host_trace.py` | Extend parsers for additional syscalls |
| `apps/android/tests/test_audit_web_host_trace.py` | New test cases for extended parsing |
| `apps/android/tests/web-bootstrap.host.spec.mjs` or new spec | Extended strace capture flags |
| `apps/android/tests/web-bounded-profile.host.spec.mjs` | Updated trace invocation |
| `apps/android/evidence/` | New trace result files |
| `apps/android/execution/ORIGINAL_WEB_ASSETS.md` | Updated dependency documentation |

### Implementation approach

1. **Extend strace capture** in the Vitest web-profile test to include: `-e trace=open,openat,openat2,stat,fstat,lstat,fstatat,newfstatat,access,faccessat,getdents,getdents64,readlink,readlinkat,dlopen,execve,clone,clone3,vfork,fork` with both success and failure logging.

2. **Extend the trace auditor** to parse each new syscall class separately, producing categorized dependency lists:
   - Files opened for reading (existing, extended to relative paths)
   - Files whose metadata was checked
   - Directories enumerated
   - Symlinks resolved
   - Native libraries loaded via `dlopen`
   - Child executables spawned
   - Failed accesses (important for identifying expected-missing files)

3. **Add static analysis complement** — parse the built JavaScript bundles for `import`/`require` statements, `process.dlopen`, `child_process.spawn`, and configuration file references that may not appear in a single trace run.

4. **Record blind spots explicitly** — document which syscall classes are still unobservable (e.g., `io_uring`, indirect `mmap`-based loading) and which trace conditions may not exercise all code paths.

### Tests

- Unit tests for each new syscall parser in `test_audit_web_host_trace.py`
- Regression tests ensuring existing trace output format compatibility
- Validation that the extended trace produces a strict superset of the current results
- Negative tests for parser edge cases (truncated lines, resumed syscalls, error returns)

### Acceptance criteria

- [ ] Trace auditor parses all listed syscall classes from strace output
- [ ] Both success and failure cases are categorized separately
- [ ] Relative paths are resolved against the process's working directory where observable
- [ ] Native addon dependencies are identified with their full `DT_NEEDED` chains
- [ ] Child process executables are recorded
- [ ] A JSON report documents observed and unobserved syscall classes explicitly
- [ ] Existing evidence files are not modified; new evidence files are produced
- [ ] Host tests pass
- [ ] Documentation updated to reflect extended observation scope

### Expected output artifacts

- Extended `audit_web_host_trace.py` with `schemaVersion: 2`
- New evidence JSON(s) with extended trace results
- Updated blind-spot documentation in `ORIGINAL_WEB_ASSETS.md`

---

## 11. Approval Required

> [!IMPORTANT]
> **No source code will be modified until explicit user approval is received.**
>
> The above audit is complete. P3A-001 is identified as the correct next task. The proposed implementation plan is ready for review.
>
> **Awaiting your approval to proceed with P3A-001 implementation.**
