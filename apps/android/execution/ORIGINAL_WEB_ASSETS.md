

### Follow-up user device result — 2026-11-18, exit code 1

The updated diagnostic now reports `Web profile exited before publishing a URL (exit code 1)`, followed only by the `libc++_shared.so` unused processor-specific `DT` entry warning (`ignoring`). The [structured evidence](../evidence/p3a007-user-exit-code-1-2026-11-18.json) preserves the exact message. This confirms an early child exit, not a timeout, but does not show the cause; no additional runtime exception is captured. The warning is not established as causal. Tested APK SHA-256 (the installed signed copy if different), device model, Android API, ABI and Android logcat are still needed. Do not change native packaging or suppress the warning based on this message alone. P3A-007 and Gate 4 remain open pending diagnosis and a successful exact-APK device run.
