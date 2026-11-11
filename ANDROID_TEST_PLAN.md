# Android acceptance tests

Reference. Every device claim must identify model/emulator, ABI, API, WebView version and source revision. No physical device or emulator is currently available in this environment; package inspection is not launch evidence.

| Test | Expected acceptance | Current evidence |
| --- | --- | --- |
| Original frontend build | Real source to dist, unchanged screens | Vite and full artifact builds pass on Linux |
| Host build/unit/lint | APK packages assets; origin and approval denial tests pass | See current status |
| Origin isolation | Foreign navigation, frames, resources, redirects and external intents cannot execute privileged actions | JVM policy tests; WebView device tests pending |
| Native diagnostic | Denial executes nothing; Allow once returns actual pwd/exit; replay/expiry rejected | Provider source and authorization tests; device execution pending |
| Runtime ABI | Bionic ARM64 Node >=24.9, worker/fs/TLS/SQLite/native addon tests | Host probe rejects non-Android; Android blocked |
| Original UI navigation | Real chat/sessions/settings/plugin screens, touch, IME, rotate/back | Blocked on boot payload/runtime |
| Agent round trip | Real dsh profile -> model -> trusted approval -> Android command -> stdout/exit in original UI | Blocked; no mock substituted |
| Persistence | Session survives restart and interrupted writes retain locking rules | Blocked on native flock/runtime |
| Storage/secrets | SAF grants/revocation and Keystore roundtrip, no key in logs/exports | Not implemented |
| Terminal | Real command/input/output, exit, timeout, cancellation, cleanup and PTY | General terminal not implemented |
| Plugins/MCP | Per-plugin verdict; HTTP vs stdio verified separately, denied tools cannot bypass policy | Not verified |
| Lifecycle | OS kill, rotation, crash, shutdown, interrupted-task reporting and finite background work | Agent not implemented |
| Optional providers | Termux absent does not break core; no silent root fallback; explicit root denial/revocation | Providers not implemented |
| Performance | Measured startup/RSS/battery/storage on identifiable configurations | No numbers claimed |
| Distribution | CI run artifact SHA, licenses, install/launch on API29 and recent Android | Workflow source only until run |

Host test doubles or policy tests must never be described as Android command execution. External model tests need user-provided test credentials through a protected configured mechanism; no secrets in chat or commits.
