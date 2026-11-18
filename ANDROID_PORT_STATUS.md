

### Follow-up device result — child exited with status 1

The user has now retested and reports the updated diagnostic: the web-profile child **exited before publishing a URL with exit code 1**, with only the same `libc++_shared.so` ignored-DT-entry linker warning in captured output. This confirms the supervisor's early-exit reporting path is working; it does **not** identify why the child exits. The [new evidence record](apps/android/evidence/p3a007-user-exit-code-1-2026-11-18.json) preserves the exact message. The tested APK SHA-256 (including any signed-copy hash), device model, Android API and ABI remain unknown, and no Android logcat was supplied. The warning is still not established as causal. P3A-007 remains **IMPLEMENTED / device validation BLOCKED**; root-cause diagnosis needs the exact APK/device identity and process logcat. No claim that the web profile boots is supported.
