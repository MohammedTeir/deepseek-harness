# Gate 3 selected-device process capability review

## Decision

Status: VERIFIED for the fixed capability suite on Redmi Note 8 Pro, Android 11/API 30, ARM64. The [complete submitted report](apps/android/evidence/phone-process-apk4-run1.json) passes the unchanged APK #4 result validator with matching APK and native executable fingerprints. This accepts the demonstrated primitives on this device; overall Gate 3 remains IN PROGRESS for target-version coverage and unresolved qualification limits. It does not establish a general shell provider, original terminal integration or complete Android compatibility.

This is user-reported physical execution, not developer-controlled ADB instrumentation or device attestation. JSON formatting and slash escaping are normalized; submitted values and gate3Passed=false remain unchanged. The controller intentionally does not decide gate acceptance. [The review evidence](apps/android/evidence/phone-process-apk4-review.json) records the separate decision and executed checks.

## Criteria and evidence

| Criterion | Actual submitted result | Review |
| --- | --- | --- |
| Installed ordinary-UID execution | UID 10751; native PID 10107; supervisor 10069; installed executable reported nonwritable; matching packaged digest | VERIFIED for submitted run |
| Observable stdout, stderr and exit | Two separately observed stream chunks, stdin acknowledgment before exit 7; complete 16384-byte streams with exit 9 | VERIFIED |
| Launch failure | Missing executable reports errno 2 and exit 127 | VERIFIED |
| Explicit cancellation | TERM signal 15, timedOut=false, actual child reap reported | VERIFIED for native fixture |
| Deadline escalation | Ready worker ignores TERM; timeout yields KILL signal 9 and actual reap | VERIFIED for native fixture |
| Cooperative descendant cleanup | Grandchild 10130 reaped by worker 10129; group completion exit 0 | VERIFIED within cooperative group scope |
| Android shell | Fixed /system/bin/sh script returns real SH-OUT, canonical cwd, SH-ERR and exit 7 | VERIFIED for fixed script |
| PTY | Actual controlling TTY; input echoed and consumed; resize to 40 rows/100 columns; merged stderr; exit 0/reaped | VERIFIED for fixed native child |
| Tool availability | Eight exact system paths executable; four exact paths return ENOENT | VERIFIED as path discovery only |

The observed executable paths are sh, pwd, printf, cat, sleep, echo, stty and toybox under /system/bin. Existence/executable checks do not execute each individual utility, certify its full flags or identify GNU compatibility. Git, curl, python3 and ssh were absent at those same paths, not necessarily everywhere on the device. No Termux or Root fallback was used.

## Limits and next milestone

API 29 and a recent Android version remain NOT YET VERIFIED. The PTY child is a fixed native fixture, not an interactive shell. This run tests explicit native cancellation, not leaving the Activity, Android service death, arbitrary process trees, detached children, PTY job control, Ctrl-C or indefinite background operation. Parent-death setup is reported; actual parent-death behavior was not exercised. No AVC denial was captured, so the test does not prove a universal SELinux allowance or explain the earlier hardlink denial.

The original Harness engine and Gate 2 tool proof remain unchanged. This suite is not another registered Harness tool and does not provide agent-accessible arbitrary shell execution. Same-UID code remains outside a malicious-plugin isolation claim. No model request or original Web UI result is part of this report.

Next: inspect how the original Subprocess/TerminalBackend contracts can consume these verified capabilities without assuming Bash or desktop process managers. Select and test a narrow adapter using existing authorization ownership before enabling any general tool. Continue independent original-UI/secure-transport work only within its separate Gate 4 criteria. Keep target-version coverage, unsupported tools and lifecycle tests explicit; no merge or release follows from this review.

## APK #5 original subprocess adapter acceptance

Status: VERIFIED for the bounded AndroidFixedPwdSubprocess service path on the same reported Android 11/API 30 ARM64 phone. The [complete normalized report](apps/android/evidence/phone-subprocess-apk5-run1.json) passes the unchanged command validator with --require-subprocess against the delivered APK #5 fingerprints. The [review record](apps/android/evidence/phone-subprocess-apk5-review.json) accepts actual original registry/pipeline plus originalSubprocessService=true and android-fixed-pwd-v1 in the canonical successful tool result. Native denial occurs before one approved process launch; two consumers have one winner, changed inputs reject and replay returns USED. UID 10751, supervisor 1747, controller 1792 and execution peer 1812 remain distinct and correlated. Actual stdout is the native workspace, stderr is empty and exitCode is 0. All six original approval/command records recover identically after runtime restart; five JSONL hashes are retained, including earlier sessions.

This is user-reported execution, not ADB instrumentation. Submitted gate2Passed=false and modelRequestExecuted=false remain unchanged. The known linker warning and duplicate SDK close/shutdown note are retained; the pinned controller requires explicit acknowledged shutdown and recovered history before success. This run does not test interrupted/failed adapter outcomes, Activity/service death, live terminal I/O or broader shell commands. Overall Gate 3 stays IN PROGRESS for its existing version/lifecycle limits. Next engineering milestone: evaluate an Android build and compliant helper packaging for the existing node-pty implementation, then choose the smallest authenticated live PTY adaptation with real input/output/resize and awaited termination. A narrow native bridge is an alternative only after that comparison; do not build a custom multiplexer by default.
