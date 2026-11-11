# Android implementation milestones

Reference. Status ownership: Android port maintainer; no acceptance exceptions are assumed. Evidence and current results live in [status](ANDROID_PORT_STATUS.md).

| Phase | Objective / files | Acceptance / next runnable action | Status |
| --- | --- | --- | --- |
| 0 | Verify fork, baseline and branch | Origin/upstream HEAD comparison and clean initial tree recorded in audit | VERIFIED |
| 1 | Source and compatibility audit | Critical paths mapped; complete dependency/plugin closure still requires runtime build | IN PROGRESS |
| 2 | Original assets in Kotlin host, apps/android/app | Build APK, inspect payload; install and navigate real screens after boot integration | IN PROGRESS |
| 3 | Embedded Node/Harness, apps/android/runtime | Obtain pinned >=24.9 Bionic runtime; execute probe on ARM64, then boot dsh profile | BLOCKED |
| 4 | Existing protocol + OS adapters | Backend approvals, real tool result in original chat, restart persistence, SAF, Keystore, PTY | BLOCKED |
| 5 | Optional Termux/root | Implement explicit providers only after independent core works; suitable test devices | NOT STARTED |
| 6 | Hardening/performance | API29/recent Android, denial, malicious navigation/plugin, OS death and measured resources | NOT STARTED |
| 7 | Distribution | Traceable CI APKs and license closure; release remains separately authorized | IN PROGRESS |

Runtime investigation is independent of host packaging: do not downgrade Node requirements, substitute Linux binaries, disable native session locks or reimplement the loop to turn a blocked milestone green.
