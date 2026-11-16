# Gate 3 evidence review

Reference scope: subprocess, shell and PTY capability conditions in the [master specification](../../../DEEPSEEK_HARNESS_ANDROID_MASTER_PROMPT.md#gate-3--android-subprocess-shell-and-pty-capability). Decision: IN PROGRESS. Bounded capability qualification passes on the user-reported Redmi Note 8 Pro, Android 11/API 30, ARM64. This is not a general Android compatibility or general shell-provider acceptance.

## Acceptance coverage

| Required capability | Evidence | Decision and limits |
|---|---|---|
| Real subprocess output, stderr, nonzero exit, streaming and backpressure | [APK #4 review](../evidence/phone-process-apk4-review.json) | VERIFIED on reported API 30 phone; fixed native fixtures |
| Fixed Android shell execution and executable discovery | [APK #4 report](../evidence/phone-process-apk4-run1.json) | VERIFIED for reported paths; Git, curl, Python and SSH were unavailable at tested system paths, not universally absent |
| Original node-pty input, resize, exit, Ctrl-C, TERM and KILL | [APK #6 review](../evidence/phone-node-pty-apk6-review.json) | VERIFIED on reported phone; no custom PTY multiplexer required |
| Original registry/tool/approval integration and persisted recovery | [APK #7 review](../evidence/phone-apk7-terminal-result-review.json) | VERIFIED for one fixed, native-approved benign child |
| Original-terminal wait timeout, cancellation and child cleanup | [APK #8 review](../evidence/phone-apk8-lifecycle-result-review.json) | VERIFIED for timeout retaining the child, followed by SIGINT cancellation; not a process-kill deadline |
| Installer-owned executable/addon packaging | [APK #8 inspection](../evidence/terminal-lifecycle-apk8-build.json) | Build inspection passes; matching hashes reported on API 30 phone |
| Target API-level coverage | Existing phone evidence is API 30 | BLOCKED: no API 29 or recent-Android execution evidence available |
| Termux fallback | Fixed embedded qualification uses no Termux | No silent fallback; optional provider remains a later phase |

VERIFIED here means reviewed user-reported physical-device results, not developer-controlled ADB instrumentation or device attestation. Historical failure records and raw gate3Passed false values remain unchanged. Selected-field APK #7/#8 reviews are explicitly labelled and do not pretend to be complete raw captures.

## Remaining engineering checkpoint

Before broad Gate 3 acceptance, run the existing fixed process, original node-pty, original approved-tool and original-terminal lifecycle diagnostics on Android 10/API 29 ARM64 and a recent Android ARM64 environment. Record actual API/ABI/kernel, APK and library hashes, syscall/process outcomes and complete results. Use native human approval for the original-tool and terminal cases; do not automate physical acceptance decisions. A device/emulator run is attributed as such, with the existing physical-phone evidence preserved separately.

The current signed APK #8 contains these diagnostics. Follow the [lifecycle procedure](TERMINAL_LIFECYCLE_PROOF.md#phone-procedure) for its terminal case. Installation failure, unsupported APIs or cleanup failure must become recorded blockers rather than waived checks. Keep original frontend implementation behind the acceptance decision; independent source inspection is safe, but this review does not authorize bypassing unresolved gates.

General shell-provider implementation, arbitrary foreground job control, arbitrary descendant trees, app/OS process-death cleanup, power-loss durability and malicious same-UID plugin isolation remain unverified or future work. Original frontend/streaming acceptance belongs to Gate 4; optional Termux/root belongs to later providers. These limitations do not invalidate the fixed API 30 results or establish broader functionality.

## Cloud emulator preflight

The [architecture preflight](../evidence/arm64-emulator-preflight.json) records an x86_64 host, absent /dev/kvm and an installed QEMU2 emulator rejecting ARM64 guest selection before Android boot. This explicitly synthetic AVD metadata probe uses the existing x86_64 image path; it is not Android execution evidence. Official API 29 and API 35 ARM64 images exist in the downloaded Google catalog, but were not downloaded because the installed emulator rejects the required architecture. The next runnable acceptance environment needs an ARM64-capable Android emulator host or suitable ARM64 devices; an x86_64 APK would test different binaries and cannot substitute for the required ARM64 evidence.
