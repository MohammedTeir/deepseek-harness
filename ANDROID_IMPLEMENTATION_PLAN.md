# Android implementation roadmap

## Summary

Only Phase 0 and Phase 1 are authorized in this branch. Phase 2 must wait for review of these findings. The master prompt's gates take precedence over earlier prototype work, which is not imported into this branch.

| Milestone | Status | Acceptance / next action |
|---|---|---|
| Phase 0: fork/baseline | VERIFIED | Correct fork and upstream, clean starting tree, exact revisions and lock digest recorded, requested branch created |
| Phase 1: locked dependency graph | VERIFIED | All resolved nodes and 8,836 edges enumerated; zero unresolved targets; all package manifests accounted for locally or by integrity-matched registry metadata |
| Phase 1: source/native/platform audit | IMPLEMENTED | Source-backed report, package payload inventory and risk matrix available; noninstalled payloads and device semantics explicitly unverified |
| Gate 1 review | IN PROGRESS | Author reviews scope, unresolved artifacts, trust model and runtime qualification plan; no runtime selected as proven |
| Phase 2 / Gate 2 | NOT STARTED | After review only: compare Android Node packaging candidates and boot real Harness profile/session/tool |
| Gate 3 | NOT STARTED | Device commands, streams, signals, timeout/cancel and PTY proof |
| Gate 4 | NOT STARTED | Original UI boot, origin authentication, deep links, genuine streaming/session result |
| Gate 5 | NOT STARTED | Separate root policy, canonical request binding, deny/replay/mutation/adversarial tests |
| Gate 6 | NOT STARTED | Device matrix, recovery, licenses and traceable artifacts; no release authorization |

## Review decisions

Approve or revise the minimum trusted plugin set, first device/API targets, supported command set, runtime qualification budget and acceptable candidate fallback. Resolve which dependencies belong in the first Android profile rather than shipping the CLI's full install closure unchanged. Decide how credentials remain outside untrusted execution; a same-UID service does not solve this.

## Exact next engineering milestone

After Phase 1 review, qualify a Node >=24.9 Android ARM64 runtime on API 29 and a recent Android device: load from compliant APK packaging; exercise ESM, workers, TLS/DNS, SQLite and actual lock contention; launch an authentic Harness profile, create/reopen a persistent session, and execute one explicitly approved harmless tool with real output. Capture failure telemetry and denied-operation evidence. No model success claim without authorized credentials. Do not spend this milestone redesigning the UI or implementing optional root/Termux.
