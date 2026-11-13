# Android architecture recommendations

## Summary

Recommend retaining the original Cordis/profile engine and Web UI behind a Kotlin lifecycle/permission host. The [Gate 1 review](ANDROID_GATE1_REVIEW.md) selects an APK-loaded shared-library experiment; production packaging remains subject to qualification. The user-reported v5 phone results qualify the fixed Node API probes in both modes on one Android 11/API 30 ARM64 phone; the later APK #2 physical review accepts authentic profile/session recovery on that phone, and the bounded APK #3 command proof is accepted in the [Gate 2 review](ANDROID_GATE2_REVIEW.md). The packaged executable is selected for the next bounded profile experiment, not production qualification.

| Candidate | Reuse and benefits | Blocking questions | Recommendation |
|---|---|---|---|
| Android-built Node shared library in a dedicated app process, JNI lifecycle bridge | Original JS/profile/plugin execution; APK native-library loading; explicit supervisor | Node >=24.9 unsupported upstream Android target; V8/NDK build; global lifecycle, addon symbol visibility, workers, child processes and 16 KB alignment | Retain as API/lifecycle reference; app_process64 execPath does not launch child Node unchanged |
| Android-built executable packaged through a supported immutable APK/native-library mechanism | Real process isolation and conventional stdio/termination | Package installation/extraction rules, linker/interpreter, SELinux, target SDK, executable naming/loading behavior; must demonstrate compliant execution without writable-directory exec | Selected for the next bounded Harness profile experiment after user-reported installed execution and child exit zero; qualify remaining APIs, lifecycle and supported Android versions |
| Maintained Node-mobile embedding | Existing mobile embedding work | Current inspected source major is recorded in platform references; must meet actual >=24.9 engine/API needs, not merely load JavaScript | Reject any older runtime until a compatible maintained version is demonstrated |
| QuickJS/WASM/browser-worker runtime | Portable computation for narrow libraries | No drop-in Node API, native addons, processes or actual current Harness profile; would require extensive replacement | Not a full Harness runtime strategy |
| Tauri Mobile or Capacitor | Native/Web UI carrier tooling | Does not provide Node, compatible PTY or N-API by itself | No demonstrated advantage over Kotlin/WebView for this port |
| Remote host or required Termux | Existing desktop execution | Violates standalone local-engine requirement | Not an acceptable core architecture |

The [v5 physical-phone record](apps/android/evidence/phone-v5-user-results.json) reports successful execution from installer-owned nativeLibraryDir, a non-writable installed executable, and a same-UID child with real stdout and exit zero. This resolves the fixed child-launch comparison on that device and favors the packaged executable for the next authentic profile experiment. JNI remains a reference; it reports app_process64 as execPath. Both modes require the same authentic Harness profile acceptance criteria before a production decision. Do not downgrade Node requirements, substitute the agent loop, or infer feasibility from a library symbol or HTML rendering. Shared-library lifecycle and executable packaging are both technical risks; there is no automatic winner.

## Proposed separation

The Android supervisor owns lifecycle, app identity, permission UI and a narrowly typed OS broker. The authentic profile runner owns Cordis services, model adapters, session events and tool registry. Original frontend assets and runtime boot injections retain their existing responsibilities. Android-specific providers implement existing filesystem/process/credential seams. Policy enforcement lives outside model/plugin-controlled code where privilege separation is required.

Compare an authenticated loopback original server against an AssetLoader frontend plus a deliberately adapted original protocol. Loopback minimizes index/RPC changes but must pass Android networking, origin and cross-app authentication tests. AssetLoader provides a stable HTTPS asset origin but requires explicit routing, cookie, dynamic-module and streaming adaptation. Do not choose either from successful static rendering alone.

## Runtime composition constraints

Use `dsh` profile launch; do not create a new hardcoded agent. The shipped sdk-minimal composition is a reference for reducing the first proof, not a final single-vendor product. The experimental Android ARM64 lock selector and [no-execution overlay](ANDROID_RUNTIME_GUIDE.md#original-lock-selector-and-bounded-profile) provide a bounded host-tested composition. V6 has selected-mode user phone evidence for that selector. V7 packages an observed original-profile startup/session image and the real internal-loader addon; the user now reaches original initialization but session recovery fails. V8 investigates that storage/shutdown failure; broader dependency support and durable Android recovery remain unverified. Keep bash/PTY/subprocess and ownership-sensitive spill cleanup disabled until their providers are qualified, while retaining actual sessions and compatible tools. Restore compatible providers/plugins incrementally; unsupported desktop automation, browser engines and package installers must report capability failures.

No permanent root shell or plugin-controlled `su` is permitted. App UID process separation alone does not isolate files or credentials from a hostile Node plugin. Trusted code distribution, separate broker authority and deny-by-default execution remain necessary.

## Persistence compatibility checkpoint

The [atomic publication review](apps/android/atomic-proof/ATOMIC_PERSISTENCE_REVIEW.md) selects a same-directory renameat2 no-replace experiment, not a production adapter. APK #1 runs in a separate diagnostic package and does not alter the original JSONL implementation. Physical-device acceptance is required before selecting or integrating a native/filesystem adapter. Attachment aliases retain-source semantics and cross-directory staging remain separate unresolved requirements.

The accepted [APK #1 physical checkpoint](apps/android/evidence/atomic-poc-physical-review.json) permits the narrow [APK #2 publication integration](apps/android/runtime/ATOMIC_PERSISTENCE_ADAPTER.md). The original JSONL materialization and generation paths share a platform entry: non-Android keeps hardlinks, Android ARM64 uses the carrier's fixed no-replace binding. Callers retain synchronization, collision validation and cleanup. Cross-directory publication and retained-source aliases are excluded pending separate qualification. This does not select a new engine or qualify Android sessions before phone tests.

## Original tool qualification composition

The [APK #3 reference](apps/android/execution/COMMAND_PROOF.md) connects the original tool pipeline and approval service to the private native fixed-command broker. A genuine pre-step context initiates qualification without a model response; canonical results persist through the existing command lifecycle rather than fabricated model-step tool events. Runtime restart/recovery is exercised on the host; the physical command/UI checkpoint remains pending. This does not change the original frontend or select general shell/PTY support.

## APK #3 physical review

The [Gate 2 review](ANDROID_GATE2_REVIEW.md) accepts the bounded original local-engine/tool/native-approval composition on the reported phone. Qualification-triggered tool results persist through the original command lifecycle; model-requested tool history, original frontend integration, broad process capability and hostile-plugin isolation remain separate.

## Gate 3 diagnostic boundary

The new process/PTY proof is a fixed native capability suite hosted by a private Android service. It is independent of Harness tool qualification and preserves the existing Node/profile architecture. It informs a later adapter for original subprocess and terminal interfaces; it is not that adapter. The original UI and Bash terminal protocol remain unchanged. See [the qualification guide](apps/android/execution/process-proof/PROCESS_CAPABILITY_PROOF.md).

## Original subprocess service adapter

AndroidFixedPwdSubprocess subclasses the original service and is mounted as a separate profile plugin. The registered tool now uses ctx.subprocess with a scoped immutable call binding. The authenticated native broker and human grant remain the execution authority. Only bounded collected fixed pwd is supported; batch RPC cannot provide raw streams or a live SubprocessTerminalHandle. See [the adapter contract](apps/android/execution/SUBPROCESS_ADAPTER.md).

## Original node-pty selection experiment

An isolated service qualifies the locked original node-pty source and JavaScript using an installer-owned NAPI addon and fixed native fixture. A scoped loader adapts its package-local native lookup; no agent or original terminal implementation is replaced. Cross-compilation and host behavior support testing this reuse path before considering a new bridge. Device execution and general terminal-session ownership remain unverified. See [the experiment](apps/android/execution/NODE_PTY_QUALIFICATION.md).

## Original terminal backend seam

The [fixed terminal registry qualification](apps/android/execution/TERMINAL_REGISTRY_QUALIFICATION.md) exercises the original profile, genuine Agent ownership, tool/approval pipeline, registry rollback and persisted history with real host PTY processes. Status: IMPLEMENTED with host verification; Android integration NOT STARTED. Automated host decisions are not native human approval. Android guards remain active and no APK changes are included. Gate 3 remains IN PROGRESS; next implement native-authorized allocation before a new physical-device checkpoint.

## Fixed native terminal vertical slice

The [APK #7 reference](apps/android/execution/TERMINAL_ANDROID_PROOF.md) records the original registry/tool/approval path, authenticated native broker, human UI and fixed Android PTY factory. Host and relocated-profile tests and Android build/inspection pass. Physical execution is BLOCKED pending phone evidence. This is a fixed benign fixture, not general shell or the original Web UI. Gate 3 remains IN PROGRESS; preserve existing data when updating the single runtime app.
