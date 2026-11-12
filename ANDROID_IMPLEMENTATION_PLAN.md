# Android implementation roadmap

## Summary

The author has authorized Gate 1 review and a bounded Phase 2 proof when its acceptance criteria are satisfied. The [Gate 1 decision](ANDROID_GATE1_REVIEW.md) accepts the investigation strategy; the [v5 phone results](apps/android/evidence/phone-v5-user-results.json) now report fixed Node API and installed-child execution passing on Android 11/API 30. Authentic profile/session/tool execution remains unverified. The master prompt's gates take precedence over earlier prototype work, which is not imported into this branch.

| Milestone | Status | Acceptance / next action |
|---|---|---|
| Phase 0: fork/baseline | VERIFIED | Correct fork and upstream, clean starting tree, exact revisions and lock digest recorded, requested branch created |
| Phase 1: locked dependency graph | VERIFIED | All resolved nodes and 8,836 edges enumerated; zero unresolved targets; all package manifests accounted for locally or by integrity-matched registry metadata |
| Phase 1: source/native/platform audit | IMPLEMENTED | Source-backed report, package payload inventory and risk matrix available; noninstalled payloads and device semantics explicitly unverified |
| Gate 1 review | VERIFIED | Reviewed criteria and bounded experimental decision recorded; no runtime selected as proven |
| Phase 2 / Gate 2 | IN PROGRESS | ARM64 runtime builds and user-reported fixed phone probes pass; authentic Android profile/session/tool proof remains blocked |
| Gate 3 | NOT STARTED | Device commands, streams, signals, timeout/cancel and PTY proof |
| Gate 4 | NOT STARTED | Original UI boot, origin authentication, deep links, genuine streaming/session result |
| Gate 5 | NOT STARTED | Separate root policy, canonical request binding, deny/replay/mutation/adversarial tests |
| Gate 6 | NOT STARTED | Device matrix, recovery, licenses and traceable artifacts; no release authorization |

## Review decisions

Approve or revise the minimum trusted plugin set, first device/API targets, supported command set, runtime qualification budget and acceptable candidate fallback. Resolve which dependencies belong in the first Android profile rather than shipping the CLI's full install closure unchanged. Decide how credentials remain outside untrusted execution; a same-UID service does not solve this.

## Exact next engineering milestone

Use the packaged executable selected in the [architecture recommendation](ANDROID_ARCHITECTURE.md) for the next authentic profile experiment. The selected v6 executable-mode lock entry now has user-reported device evidence. Run the packaged v7 original-profile diagnostic on Android ARM64 and qualify its newly built internal-loader addon and persistent session recovery. Keep unqualified ownership cleanup and shell/PTY services excluded during that startup/session experiment. After the profile creates and reopens a persistent session, implement and verify a trusted provider for one explicitly approved harmless tool with real output. The existing fixed API proof on Android 11 does not replace API 29 and recent-device runtime qualification, lifecycle testing or developer-controlled instrumentation. Capture failure telemetry and denied-operation evidence. No model success claim without authorized credentials. Do not spend this milestone redesigning the UI or implementing optional root/Termux.
