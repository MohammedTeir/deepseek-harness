

### P3A-007 follow-up result — child exit code 1

The latest user report shows the child process exits with code 1 before publishing its URL. The only captured child output is the Android linker warning that an unknown processor-specific `DT` entry in `libc++_shared.so` is ignored; this does not prove that warning caused the exit. The [failure evidence](apps/android/evidence/p3a007-user-exit-code-1-2026-11-18.json) records the unknown APK digest and device properties. Request the tested APK identity and Android logcat around launch before selecting a root-cause fix. P3A-007 device validation remains blocked and Gate 4 is open.
