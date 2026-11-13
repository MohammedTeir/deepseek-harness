# Gate 2 local-engine qualification review

## Decision

Status: VERIFIED for the bounded local-engine qualification on the user-tested Redmi Note 8 Pro, Android 11/API 30, ARM64. The [physical review record](apps/android/evidence/phone-command-apk3-review.json) accepts the submitted original-tool/native-approval result against the delivered APK and native-library fingerprints. This accepts Gate 2's local runtime/profile/session/tool criteria. External model inference remains NOT YET VERIFIED because no test credentials were supplied; no model request or model-generated tool call is claimed. This is not complete Android product, sandbox, terminal or release acceptance.

| Local criterion | Executed evidence | Result |
|---|---|---|
| Real Android ARM64 Node and original profile | Node v24.22.1/android/arm64, original SDK server identity, matching installed APK/native hashes and ordinary UID 10751 | VERIFIED within reported phone scope |
| Genuine original registry/executor/approval | Existing source composition plus original approval audit and canonical tool-batch outcomes in the submitted session | VERIFIED for qualification-triggered tool |
| Explicit human denial and approval | Tester reports Deny then Approve; original audit records rejected then allowed-once; rejected batch retains APPROVAL_REJECTED | VERIFIED by user-reported manual execution |
| Real harmless command | Native process count 1, actual stdout/cwd, empty stderr and exit 0; execution peer PID 7309 differs from controller 7294 and supervisor 7246 | VERIFIED for fixed /system/bin/pwd |
| One-shot and exact request protection | Two concurrent consumers, one rejection, replay USED, changed command/arguments/cwd/session/call rejected, UID claim malformed | VERIFIED for supplied fixed cases |
| Transport failure/authority rejection | Unauthenticated, malformed, duplicate and unsupported approval-action requests reject | VERIFIED for supplied probes; separate-UID attack untested |
| Persistent result and recovery | Identical six original approval/command records after full Node runtime restart, plus actual JSONL hashes; prior APK #2 physical acceptance retained | VERIFIED for runtime restart |

## Accepted evidence and limits

The [normalized complete phone report](apps/android/evidence/phone-command-apk3-run1.json) retains the submitted values, nested canonical tool batches, repeated recovered history, four JSONL hashes and diagnostic notes. JSON formatting and slash escapes are normalized; decision and result fields are not rewritten. The original controller's gate2Passed remains false by design: it does not make the review decision. ModelRequestExecuted remains false. The unchanged validator passes this actual report against the committed APK #3 build record.

This is user-reported physical execution, not developer-controlled ADB instrumentation, a screenshot audit or cryptographic device attestation. The tool is initiated by a bounded original pre-step extension, not by an LLM response. The actual pipeline result persists through command/done alongside approval events; no model-step tool/call or tool/result history is fabricated. The [owning command reference](apps/android/execution/COMMAND_PROOF.md) explains that distinction.

The tester separately reports BLOCKED: command proof cancelled while leaving the Activity after leaving a confirmation and returning. This is the intended fail-closed UI transition. That text alone does not prove child-process termination, absence of background work, active-write integrity or full lifecycle recovery. A complete cancellation-run audit and a repeated full command report were not supplied.

The nonfatal linker DT-entry warning and SDK closed-input shutdown notes remain in the report. The pinned controller requires successful explicit shutdown replies before its SDK close issues another best-effort request, and successful runtime recovery follows. Exit 0 and the actual recovered records support the accepted case; notes are not filtered or converted into successes.

## Remaining engineering work

Gate 3 is the next milestone: qualify Android command availability and supported subprocess streaming, nonzero exit/stderr, timeout, cancellation, termination and PTY capabilities on identifiable devices. Do not generalize fixed pwd into unrestricted shell support. Original frontend/secure transport is Gate 4. API 29/recent-device coverage, separate-UID adversarial probes, negative instrumentation execution, hostile same-UID plugin isolation, broad lifecycle/power-loss tests and external model requests remain separately unverified. Root and Termux stay optional future providers; no production release or merge is authorized by this review.
