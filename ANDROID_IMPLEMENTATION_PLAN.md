# Android implementation roadmap

## Summary

The author has authorized Gate 1 review and a bounded Phase 2 proof when its acceptance criteria are satisfied. The [Gate 1 decision](ANDROID_GATE1_REVIEW.md) accepts the investigation strategy; the [v5 phone results](apps/android/evidence/phone-v5-user-results.json) now report fixed Node API and installed-child execution passing on Android 11/API 30. The later APK #2 physical review accepts authentic profile/session recovery on one phone; the bounded original-tool/native-approval phone proof is now accepted by the Gate 2 review. The master prompt's gates take precedence over earlier prototype work, which is not imported into this branch.

| Milestone | Status | Acceptance / next action |
|---|---|---|
| Phase 0: fork/baseline | VERIFIED | Correct fork and upstream, clean starting tree, exact revisions and lock digest recorded, requested branch created |
| Phase 1: locked dependency graph | VERIFIED | All resolved nodes and 8,836 edges enumerated; zero unresolved targets; all package manifests accounted for locally or by integrity-matched registry metadata |
| Phase 1: source/native/platform audit | IMPLEMENTED | Source-backed report, package payload inventory and risk matrix available; noninstalled payloads and device semantics explicitly unverified |
| Gate 1 review | VERIFIED | Reviewed criteria and bounded experimental decision recorded; no runtime selected as proven |
| Phase 2 / Gate 2 | VERIFIED (bounded local engine) | ARM64 runtime builds and user-reported fixed phone probes pass; Android profile/session and fixed original-tool/native-approval phone evidence accepted; external model remains unverified without credentials |
| Gate 3 | NOT STARTED | Device commands, streams, signals, timeout/cancel and PTY proof |
| Gate 4 | NOT STARTED | Original UI boot, origin authentication, deep links, genuine streaming/session result |
| Gate 5 | NOT STARTED | Separate root policy, canonical request binding, deny/replay/mutation/adversarial tests |
| Gate 6 | NOT STARTED | Device matrix, recovery, licenses and traceable artifacts; no release authorization |

## Review decisions

Approve or revise the minimum trusted plugin set, first device/API targets, supported command set, runtime qualification budget and acceptable candidate fallback. Resolve which dependencies belong in the first Android profile rather than shipping the CLI's full install closure unchanged. Decide how credentials remain outside untrusted execution; a same-UID service does not solve this.

## Exact next engineering milestone

The [APK #2 physical review](apps/android/evidence/runtime-apk2-physical-review.json) accepts original Android session persistence across Node runtime restart and repeated invocations on the reported Android 11 ARM64 phone; the manual force-stop/reopen scenario is separately attributed. Implement the trusted harmless-command proof through the existing Harness tool registry/approval services and a native one-shot exact-request broker. Reject unapproved, changed and replayed operations and capture actual subprocess stdout/stderr/exit. Keep active-write kill, power loss, API 29/recent-device coverage, cross-directory publication and retained-source aliases distinct. Root, optional Termux, general PTY and original UI remain later milestones. Gate 2 is not passed until its remaining executed tool evidence exists.

The isolated [native grant/process components](apps/android/execution/COMMAND_PROOF.md) now pass host qualification and Android compilation/lint. Next connect native identity and human approval to a bounded authenticated broker and an original registered tool inside the existing agent turn. Those integrations remain unimplemented; the classes alone cannot pass the command milestone.

## Current command integration checkpoint

The [APK #3 command proof](apps/android/execution/COMMAND_PROOF.md) implements the original-tool/native-approval path and passes host composition/relocation checks. Next run the signed update on the existing physical Android 11 ARM64 phone, deny the first request, approve the second and review native start counts, replay/mutation rejection and recovered original records. Do not begin broader providers or claim Gate 2 passed before that evidence is accepted.

## Accepted local-engine checkpoint

The [Gate 2 review](ANDROID_GATE2_REVIEW.md) accepts the supplied fixed-command local proof on one Android 11 ARM64 phone. Next qualify Gate 3 command availability, streaming, failure, cancellation and PTY behavior; preserve explicit provider capabilities and unavailable states. This acceptance does not verify model inference, original Web UI, arbitrary plugins, root, Termux or production readiness.

## Gate 3 next runnable milestone

The fixed process/PTY native diagnostic is IMPLEMENTED and host tested. Physical verification is BLOCKED without an attached device. Run APK #4 on the Android 11 ARM64 phone, preserve complete output, and review actual process, shell and PTY capabilities before adapting original subprocess/terminal interfaces. The [diagnostic guide](apps/android/execution/process-proof/PROCESS_CAPABILITY_PROOF.md) defines scope and phone steps. No general shell, original terminal or frontend integration is accepted yet.

## APK #4 selected-device checkpoint

The [physical review](ANDROID_GATE3_REVIEW.md) verifies the fixed capability suite on Android 11/API 30 ARM64. Overall Gate 3 remains IN PROGRESS for version coverage and limits. Next runnable task: inspect and design the smallest adapter for the existing Subprocess/TerminalBackend contracts, preserving native authorization and reporting missing capabilities. Do not assume Bash or general shell support from a passing native PTY fixture.

## Bounded original subprocess integration

The [fixed native adapter](apps/android/execution/SUBPROCESS_ADAPTER.md) is IMPLEMENTED and host tested through the original service/profile. Next acceptance is the APK #5 original-tool test on the phone, requiring native Deny then Approve and original session recovery. Then design persistent authenticated PTY I/O and accurate process signal outcomes before extending TerminalBackend or enabling general commands. Do not infer interactive-shell support from the earlier fixed PTY fixture.

## Fixed original subprocess phone checkpoint

APK #5 is VERIFIED for the submitted Android 11 ARM64 fixed-pwd service run; see [the selected-device review](ANDROID_GATE3_REVIEW.md). The next engineering milestone first evaluates the original node-pty Android build/helper packaging before selecting a bounded live PTY adaptation. Require real input/output/resize/termination tests through the existing SubprocessTerminalHandle and original terminal registry. Do not default to a new native bridge or custom multiplexer. Preserve explicit authorization and do not enable arbitrary shells or claim a generic terminal from the fixed capability fixture. Version/lifecycle coverage remains outstanding.

## Original node-pty before a custom bridge

The [source experiment](apps/android/execution/NODE_PTY_QUALIFICATION.md) builds the original addon without C++ changes and passes host tests. APK #6 must verify actual Android loading, PTY I/O, nonzero exit and signals before production use. If accepted, implement the existing terminal-process contract with real ownership and foreground observations; keep Linux/Bash assumptions disabled until separately verified. No custom multiplexer or Termux fallback is selected.
