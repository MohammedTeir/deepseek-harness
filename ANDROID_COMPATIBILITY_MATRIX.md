# Android compatibility matrix

Reference. Source compatibility classifications are not Android runtime verification.

| Feature | Classification | Source evidence | Test evidence / remediation |
| --- | --- | --- | --- |
| Original frontend assets | REUSE DIRECTLY | apps/web/src/main.ts, vite.config.ts | Original Vite build passed; Android host copies dist. Screen navigation unverified. |
| Responsive/touch/IME/back | ADAPT | apps/android/app/src/main/java/ai/deepseek/harness/android/MainActivity.kt | Resize and history back implemented; device UX NOT YET VERIFIED. |
| Client plugin boot | ADAPT | packages/client/web/src/boot.ts | Requires real host injections/bundles; blocked until runtime. |
| Agent loop/tool registry | REUSE DIRECTLY | packages/core/agent-loop, packages/core/tools | No replacement engine; Android execution NOT YET VERIFIED. |
| Model adapters/streaming | NOT YET VERIFIED | packages/llm, packages/client/connection | Requires compatible runtime, TLS and test credentials. |
| Cordis profiles/bundles | ADAPT | apps/cli/src/profile-boot.ts, packages/bundle/base | Need Android provider composition and plugin compatibility filter. |
| Node runtime | BLOCKED | package.json engines; Node Mobile release v18.20.4 | Requires >=24.9; no accepted Android runtime. Desktop candidate probe rejects platform. |
| Session persistence | BLOCKED | packages/session/session-persistence-jsonl/src/lease.ts | Native flock Android build/provider needed; do not disable write locking. |
| Native system addon | REIMPLEMENT ADAPTER | native/system/packages/entry/src/flock.ts | Android rejected by selector; NDK flock and device contention tests needed. |
| SQLite storage | NOT YET VERIFIED | packages/storage/storage-sqlite/src/schema.ts | Host sqlite probe passes; device unverified. Base JSON backend still needs session locking. |
| Shell/process | REIMPLEMENT ADAPTER | packages/subprocess/subprocess-local, packages/shell/shell | Fixed Kotlin pwd diagnostic implemented; not Harness-connected, not a general terminal. |
| PTY terminal | BLOCKED | packages/subprocess/subprocess-local/package.json | node-pty Android ABI/PTY unavailable; original terminal frontend retained upstream. |
| Filesystem/SAF | REIMPLEMENT ADAPTER | packages/fs; Android Document APIs | SAF not implemented; no broad storage permissions. |
| Credentials/Keystore | REIMPLEMENT ADAPTER | packages/credentials; base credential rows | Not implemented; no credentials accepted by prototype. |
| Plugins/workflows | NOT YET VERIFIED | packages/boot/plugin-manager, packages/workflow | Need per-plugin runtime/dependency allowlist and real profile boot. |
| MCP HTTP | NOT YET VERIFIED | packages/mcp | Requires device TLS/network tests. |
| MCP stdio | ADAPT | packages/mcp, subprocess-local | Each server needs Android-compatible executables and explicit authorization. |
| Landlock sandbox | BLOCKED | native/system/docs/support-matrix.md | Android SELinux/kernel policy untested; cannot call app UID isolation a tool sandbox. |
| Desktop computer/browser automation | BLOCKED | packages/computer-use, packages/browser-use | Desktop drivers not Android providers. |
| Termux optional provider | NOT YET VERIFIED | ANDROID_TERMUX_INTEGRATION.md | No dependency, dispatch, permission or output test implemented. |
| Root optional provider | NOT YET VERIFIED | ANDROID_ROOT_INTEGRATION.md | No su invocation or fallback implemented. |
| Background execution/recovery | ADAPT | Activity lifecycle; Android platform policy | Activity teardown revokes diagnostic approvals; agent recovery not implemented. |

The complete [acceptance plan](ANDROID_TEST_PLAN.md) remains open until installed-device tests pass.
