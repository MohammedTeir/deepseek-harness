# Android architecture recommendations

## Summary

Recommend retaining the original Cordis/profile engine and Web UI behind a Kotlin lifecycle/permission host. The [Gate 1 review](ANDROID_GATE1_REVIEW.md) selects an APK-loaded shared-library experiment; production packaging remains subject to qualification. No architecture option is device-verified.

| Candidate | Reuse and benefits | Blocking questions | Recommendation |
|---|---|---|---|
| Android-built Node shared library in a dedicated app process, JNI lifecycle bridge | Original JS/profile/plugin execution; APK native-library loading; explicit supervisor | Node >=24.9 unsupported upstream Android target; V8/NDK build; global lifecycle, addon symbol visibility, workers, child processes and 16 KB alignment | Selected bounded prototype; not selected as proven |
| Android-built executable packaged through a supported immutable APK/native-library mechanism | Real process isolation and conventional stdio/termination | Package installation/extraction rules, linker/interpreter, SELinux, target SDK, executable naming/loading behavior; must demonstrate compliant execution without writable-directory exec | Compare in the same feasibility decision; reject if platform packaging cannot be demonstrated |
| Maintained Node-mobile embedding | Existing mobile embedding work | Current inspected source major is recorded in platform references; must meet actual >=24.9 engine/API needs, not merely load JavaScript | Reject any older runtime until a compatible maintained version is demonstrated |
| QuickJS/WASM/browser-worker runtime | Portable computation for narrow libraries | No drop-in Node API, native addons, processes or actual current Harness profile; would require extensive replacement | Not a full Harness runtime strategy |
| Tauri Mobile or Capacitor | Native/Web UI carrier tooling | Does not provide Node, compatible PTY or N-API by itself | No demonstrated advantage over Kotlin/WebView for this port |
| Remote host or required Termux | Existing desktop execution | Violates standalone local-engine requirement | Not an acceptable core architecture |

The bounded experiment starts with APK-loaded shared libraries because the host need not execute native files from writable storage. Compare the packaged-executable alternative using the same authentic Harness profile acceptance criteria before a production decision. Do not downgrade Node requirements, substitute the agent loop, or infer feasibility from a library symbol or HTML rendering. Shared-library lifecycle and executable packaging are both technical risks; there is no automatic winner.

## Proposed separation

The Android supervisor owns lifecycle, app identity, permission UI and a narrowly typed OS broker. The authentic profile runner owns Cordis services, model adapters, session events and tool registry. Original frontend assets and runtime boot injections retain their existing responsibilities. Android-specific providers implement existing filesystem/process/credential seams. Policy enforcement lives outside model/plugin-controlled code where privilege separation is required.

Compare an authenticated loopback original server against an AssetLoader frontend plus a deliberately adapted original protocol. Loopback minimizes index/RPC changes but must pass Android networking, origin and cross-app authentication tests. AssetLoader provides a stable HTTPS asset origin but requires explicit routing, cookie, dynamic-module and streaming adaptation. Do not choose either from successful static rendering alone.

## Runtime composition constraints

Use `dsh` profile launch; do not create a new hardcoded agent. The shipped sdk-minimal composition is a reference for reducing the first proof, not a final single-vendor product. Audit and replace its bash, native lock and subprocess assumptions while retaining actual sessions and tools. Restore compatible providers/plugins incrementally; unsupported desktop automation, browser engines and package installers must report capability failures.

No permanent root shell or plugin-controlled `su` is permitted. App UID process separation alone does not isolate files or credentials from a hostile Node plugin. Trusted code distribution, separate broker authority and deny-by-default execution remain necessary.
