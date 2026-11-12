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

The [APK #1 physical review](apps/android/evidence/atomic-poc-physical-review.json) passes the narrow native checkpoint on the reported Android 11 ARM64 phone. The shared original JSONL materialization/generation adapter and APK #2 are implemented for device qualification. Execute the [APK #2 tutorial](apps/android/runtime/ATOMIC_PERSISTENCE_ADAPTER.md#physical-device-tutorial), validate matching artifacts, genuine runtime restart/recovery and second-invocation persistence, and then test separately reported app restart and process termination. Do not claim Gate 2 or begin the trusted harmless-command proof before original Android persistence passes. Cross-directory publication, retained-source aliases, API 29/recent-device coverage and later root/Termux/PTY/original-UI milestones retain their requirements.
