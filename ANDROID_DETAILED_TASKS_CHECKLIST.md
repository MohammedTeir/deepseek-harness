

### 2026-11-18 follow-up — child exit code 1

- [x] Preserve the new user diagnostic in `apps/android/evidence/p3a007-user-exit-code-1-2026-11-18.json`; it confirms child exit code 1 before URL publication.
- [ ] Obtain SHA-256 of the tested APK (and signed copy if modified), device model, Android API/ABI, and Android logcat for the failed launch. The sole captured linker warning says the DT entry is ignored and is not proven causal.
- [ ] Diagnose and correct the underlying process exit, then have the user retest the exact CI-built artifact. P3A-007 physical validation remains **BLOCKED**; Gate 4 remains open.
