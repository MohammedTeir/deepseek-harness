# Android architecture recommendations

## Summary

Recommend retaining the original Cordis/profile engine and Web UI behind a Kotlin lifecycle/permission host. The [Gate 1 review](ANDROID_GATE1_REVIEW.md) selects an APK-loaded shared-library experiment; production packaging remains subject to qualification. The user-reported v5 phone results qualify the fixed Node API probes in both modes on one Android 11/API 30 ARM64 phone; authentic Harness execution is still unverified. The packaged executable is selected for the next bounded profile experiment, not production qualification.

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
