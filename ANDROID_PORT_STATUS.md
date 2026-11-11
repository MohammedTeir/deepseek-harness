# Android port status

Milestone report, 2026-11-11. Overall: IN PROGRESS; standalone Android agent BLOCKED. Baseline commit [recorded baseline](apps/android/evidence/baseline.json); branch `feature/android-port`. Environment: Linux x64 managed cloud; Node24.22.1, pnpm11.25.0; local JDK17.0.21, Android SDK35, Gradle8.11.1. No Android runtime, device test, real model request or chat/tool round trip is claimed.

## Implemented

- Original frontend build and additive Kotlin/WebView asset carrier, API29 minimum/API35 target; ARM64 native ABI filter reserved for future runtime libraries.
- Origin admission, no JavaScript execution bridge, no Internet/storage/root permissions, release debugging disabled.
- Native-only, approved fixed pwd diagnostic with expiring single-use approval. Device execution is NOT YET VERIFIED; this is not the embedded terminal or Harness tool pipeline.
- Candidate runtime diagnostics, APK asset integrity checker, native authorization/origin unit tests, additive GitHub Actions workflow.
- Audit, risk register, compatibility matrix, architecture, security and build/runtime/provider/test guides.

## Executed evidence

| Command | Observed result |
| --- | --- |
| git status --short; git remote -v; git branch -a; git log -1 | Initial tree clean; intended fork; work branch; baseline recorded |
| git ls-remote origin HEAD; git ls-remote upstream HEAD | Both returned recorded baseline |
| pnpm run build:web | PASS; original frontend Vite output |
| pnpm run build:artifacts | Initial failure: missing Node-API development headers; retry with official local Node distribution PASS, 8 gates, 36.50s |
| pnpm run build:check | PASS, 2 aggregate checks, 18.49s |
| node apps/android/runtime/probe.mjs | Expected exit1 on Linux x64: Android ARM64 FAIL; Node version, fs, SQLite, worker PASS; not Android evidence |

Host APK/unit/lint results appear below. Documentation checks and resource-constrained retries are recorded separately. CI has not run remotely; no upload or release is claimed. Device/ADB access and Android runtime remain unverified. Complete acceptance criteria are in [test plan](ANDROID_TEST_PLAN.md).

## Blockers and next actions

1. Build and validate Bionic ARM64 Node >=24.9 plus Android native flock/PTY. Node24 documentation calls Android unsupported; current latest Node Mobile18 fails the engine requirement.
2. Add genuine dsh Android profile/provider composition and authenticated transport; full original screens require host boot injections/plugin bundles. Current assets reach original boot diagnostics only.
3. Test approved real agent command and session recovery on API29/recent Android ARM64, then external provider calls with protected test credentials.
4. Implement SAF, Keystore, terminal/lifecycle recovery and per-plugin compatibility. Termux/root are optional and NOT STARTED.
5. Complete license inventory before distribution and capture traceable CI/device evidence before calling any phase VERIFIED.

No existing frontend/core files, session data, lockfile, signing credentials or unrelated CI were modified. No upstream write, merge or production release has occurred.

## Packaging milestone

`testDebugUnitTest lintDebug assembleDebug` completed successfully using JDK17.0.21 and Gradle8.11.1. Two JVM tests passed with no skips or failures. APK inspection matched 94 original frontend files byte for byte, retained the Harness license and excluded preview/sourcemaps; apksigner verified v2 signing. Android lint had no errors; warnings about dependency freshness, ARM64-only scope and required WebView JavaScript are disclosed. The final resources/icon/backup-rule build also passed in 1m43s with 52 tasks (25 executed, 27 up to date). Final Android lint: 0 errors, 5 warnings (dependency freshness, ChromeOS ABI, required JavaScript, legacy backup metadata and original icon mask). Final APK SHA256: `13c727759f08a7078d0862da8c07c2a5a276f0bcee3c6ab0f20c37e23950aa46`. Tampered index.html was rejected by the payload checker. No install/launch/command execution is inferred from these checks.

The reference-checker regression file passed all 35 tests; baseline-field exceptions retain rejection for wrong paths/fields, abbreviated hashes, trailing content and prohibited organization URLs. Scoped bilingual pairing and repository-reference checks passed. Initial doc-quick reported 19 passing checks and two documentation failures, both repaired. Full documentation/lint jobs encountered confirmed cgroup OOM kills while running concurrently; final outcomes/retries are recorded separately.

## Repository validation

After the baseline-field test gained readonly tuple typing, the final reference suite passed 35/35 and `build:check` passed both aggregate checks in 28.17s. `doc-sync` completed 42/43 checks; its graph process was killed during concurrent resource pressure. An isolated `NODE_OPTIONS=--max-old-space-size=6144 pnpm run verify-doc-graphs` passed all seven graph documents, completing the failed check without disabling it. Full `pnpm run lint` was attempted twice; its type-aware tsgolint process was killed both times. The cgroup limit is 8 GiB and OOM counters increased; this remains an environment-blocked full check, not a pass. Focused source lint and aggregate TypeScript checks are the affected-code evidence. No local hook is bypassed.

The current Node24 source documentation retains android-configure but calls Android unsupported and untested in CI. Android runtime ABI, local Harness launch and all device acceptance paths remain BLOCKED. No physical-device or emulator result exists.
