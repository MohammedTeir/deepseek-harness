# Android port audit

Reference; inspected 2026-11-11 in Linux x64 cloud workspace. Baseline: [recorded baseline](apps/android/evidence/baseline.json) (fork and upstream HEAD returned by `git ls-remote`). Product version: 0.2.2-rc.1. Origin remains https://github.com/MohammedTeir/deepseek-harness.git; upstream is https://github.com/deepseek-ai/deepseek-harness.git. Initial branch `work`, clean tree; integration branch `feature/android-port`.

## Source map

| Concern | Evidence and implications |
| --- | --- |
| Frontend | `apps/web/src/main.ts`, `apps/web/index.html`, `apps/web/vite.config.ts`: React/Cordis shell built to `apps/web/dist`; relative assets, ES2022 target. Original assets copied without rewriting screens. |
| Client boot | `packages/client/web/src/boot.ts`: requires `__ModuleLoader__`, `__DSH_BOOT__` and dynamically supplied plugin bundles; plain HTML cannot mount the complete application. |
| Desktop boot | `apps/desktop-host/src/index.ts`: `runProfile`, reserved desktop profile, loopback listener and IPC startup/shutdown. `apps/desktop/src/preload-app.ts`: directory picker, platform, boot, locale and product bridges. Electron is not bundled on Android. |
| Supported launch | `apps/cli/src/bin.ts`, `apps/cli/src/profile-boot.ts`, `packages/boot/app-boot`: launch real agent using a named dsh profile; no new agent loop. |
| Composition | `packages/bundle/base/cordis.patch.yml` supplies shared agent, LLM, subprocess, sandbox, credentials, JSON storage, permissions; `packages/bundle/web-app` supplies Web application. Must replace desktop providers before enabling an Android profile. |
| Remote protocol | `packages/client/connection/src`: RPC, client socket, connection generations, browser auth, `/connect`, host/origin admission. `packages/host/webserver/src/injections.ts` owns structured index injection. |
| Agent/tool result | `packages/core/agent-loop`, `packages/core/tools`: LLM stream, `tools/pre-execute`, `tools/execute`, post-execution, persisted `tool/result`; UI projects session events. Native diagnostic currently bypasses none of these because it is not wired to the agent. |
| Node | Root `package.json`: Node >=24.9.0, pnpm 11.28.5. Existing environment pnpm 11.25.0; validation records that difference. |
| Native code | `packages/subprocess/subprocess-local/package.json`: node-pty 1.2.0-beta.15. `native/system/packages/entry/src/flock.ts` rejects non-linux/darwin; Linux selection only glibc/musl. `native/system/docs/support-matrix.md`: no Android package. |
| Persistence | `packages/session/session-persistence-jsonl/src/lease.ts` requires native flock for POSIX ownership. `packages/storage/storage-sqlite/src/schema.ts` uses node:sqlite; base currently selects JSON storage. No persistence formats changed. |
| Policy | `SAFETY.md`: experimental, unaudited; approvals do not establish a secure sandbox. |

## Baseline and dependency evidence

`pnpm-lock.yaml` SHA256: `b6f0946199db2661e45ac0ceead23e6ceedf148604b48ea9b05a6287a4094bcd`. Node 24.22.1, Java OpenJDK 21.0.13. Initial artifact build failed because the preinstalled Node lacked Node-API development headers; a project-local official Node 24.22.1 distribution resolved that prerequisite. Full artifact build and aggregate build checks passed; see [status](ANDROID_PORT_STATUS.md).

The Node.js Mobile latest-release API returned v18.20.4 with an Android archive. That release does not satisfy the repository engine requirement. No Android Node binary was accepted, shipped or represented as compatible. Full transitive Android binary compatibility, native ABI linking and plugin loading remain unverified.

## Risk register

| Risk | Severity | Remediation and acceptance evidence |
| --- | --- | --- |
| Compatible Node 24 Android embedding unavailable | Critical | Build an NDK/Bionic ARM64 shared runtime from pinned source, record patches/licenses, run on API 29 and recent Android. |
| Native flock/PTY missing | Critical | Android platform selection and NDK builds, lock contention and PTY device tests before persistence/tools are enabled. |
| Backend boot data missing | High | Preserve authenticated original protocol and bundle graph; do not manufacture a fake boot manifest. |
| Same-UID plugins can bypass JavaScript policy | High | Do not claim plugin isolation; restrict activation and move trusted authorization outside plugin execution before enabling arbitrary tools. |
| OS kills/background limits | High | Explicit interrupted-task recovery; no indefinite background execution promise. |
| Distribution license closure incomplete | High | Inventory frontend dependencies and every additional native binary before release. |

Patch inventory: all implementation is added under `apps/android/`, with an additive Android CI workflow and these reports. No existing frontend, agent loop, session type or upstream CI file is modified. `scripts/verify-repository-references.ts` has a tested exception only for full forkHead/upstreamHead fields in the Android baseline evidence JSON, retaining the exact SHAs requested by the port audit; other fields, paths and prohibited URLs remain checked.
