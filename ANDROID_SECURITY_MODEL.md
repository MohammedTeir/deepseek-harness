# Android security risk register

## Summary

Upstream `SAFETY.md` states the project is experimental and unaudited. APK #3 implements bounded fixed-command native authorization for reviewed code; its physical acceptance is pending. Broader proposed controls and hostile-plugin isolation are not implemented or verified.

| Risk | Evidence / effect | Mitigation and required proof |
|---|---|---|
| Node plugins bypass tool policy | Plugins share Node APIs; MCP stdio SDK spawns outside Harness subprocess service | Reviewed bundled code initially; audit every spawn path; trusted native execution broker and isolation testing |
| Same-UID services read secrets | Android process separation is not UID/file separation | Keep secrets behind scoped broker/Keystore use; evaluate isolated worker UID; never describe encryption-at-rest as protection against an authorized malicious plugin |
| Loopback cross-app access | Other local apps may reach a port; browser-origin assumptions differ | Loopback-only bind plus authenticated handshakes, strict Host/Origin, per-launch credentials, replay/expiry and negative tests |
| Privileged-origin navigation | Web content or injected plugin scripts can reach bridges | No broad JS bridge; allowlisted origin/resources; reject external navigation and malformed paths; release debugging off |
| Root escalation/prompt injection | Untrusted text and shell indirection can change effects | No direct agent/plugin `su`; exact canonical immutable requests, native consent, policy before invocation, separate revocation and default-deny destructive actions |
| Plugin/package supply chain | Install hooks, downloaded tools and dynamic modules | Trace locked bytes/licenses, disallow arbitrary installation in first profile, do not execute package hooks during audit |
| Storage escape and stale SAF grants | URI grants are not normal POSIX paths | App-private workspace by default; URI-aware adapter, grant revocation and traversal tests; no broad storage permission assumption |
| Cancellation and orphan processes | Process trees/PTYs and Android lifecycle differ | Provider-specific process ownership, bounded termination and real device tests; no indefinite background guarantee |
| Session loss/corruption | V6 user reports the original Android lock entry passing; actual Android JSONL profile durability still needs v7 tests | Rebuilt/adapted locking with contention tests, atomic-write/fsync and crash recovery evidence |
| Missing POSIX identity methods | Node excludes Android getuid/geteuid; spill-local cleanup skips ownership validation when geteuid is absent | Review and adapt production ownership checks before enabling them; the probe's separate native UID does not patch global Node APIs or establish those checks |

Model output, repository content, tools, MCP results and plugins cannot authorize themselves. Denial, changed arguments, replay, expired approval and process death must fail closed. Root stays optional and disabled until its separate gate passes. Avoid logging API keys, launch tokens, sensitive command output or file content by default. The synchronized credential provider now exposes masked previews; these are credential-derived data, not permission to expose full keys. Preserve structured approval rejection/cancellation/unavailability codes in any future native broker.

V7's private services accept only fixed diagnostics and load native code from the installer-owned directory. The interpreted image rejects path escape, unexpected members, changed digests and native ELF files; alias cleanup does not follow symlinks. Host negative tests do not establish Android filesystem or process-kill security. Its original no-execution profile excludes unqualified shell/PTY and spill ownership cleanup. The original internal-module addon probes private Node runtime structures and must fail closed when unsupported. None of these controls isolates a hostile same-UID plugin, implements trusted tool approval, protects arbitrary credentials or qualifies root execution.

V7 user evidence reaches original runtime initialization but fails durable session recovery. V8 requires a successful shutdown response and verifies storage primitives instead of suppressing failures or weakening atomic publication. Its added SDK stderr snapshot is read-only, untrusted and nonredacted; retain it only under the caller's logging policy. The Android diagnostic removes credential-like environment variables, bounds retained notes and lists only its private test session paths. It does not implement a storage sandbox, infer a phone cause from host faults or bypass the blocked persistence milestone.

The isolated atomic proof uses no Android permissions, accepts only a fixed test start, and writes only its own newly created private test tree. Installer-owned native execution, anchored directory descriptors and validated fixed basenames limit the proof; they do not isolate malicious same-UID writers. Unsupported syscall and synchronization errors fail closed. The [review](apps/android/atomic-proof/ATOMIC_PERSISTENCE_REVIEW.md) requires physical acceptance before any production publication integration and separates process-kill observations from power-loss durability.

The APK #2 publication worker opens one owned private directory with O_NOFOLLOW, validates regular staging and distinct restricted basenames, and performs no-replace publication without elevation or fallback. Caller-owned staging must remain trusted; this is not same-UID isolation. Sync errors reject without deleting the visible destination. The carrier pins source/native/Node hashes and loads only an installer-owned fixed SONAME. See [implementation limits and evidence](apps/android/runtime/ATOMIC_PERSISTENCE_ADAPTER.md).

## Bounded command qualification implementation

[APK #3](apps/android/execution/COMMAND_PROOF.md) adds a private native human-decision path and AF_UNIX peer/secret checks for one fixed command, with exact native session/call/workspace bindings and one-shot consumption. The agent IPC exposes cancellation but no approval decision. Same-UID hostile-plugin confinement is not provided; only reviewed bundled code is qualified. Device peer rejection, UI/lifecycle behavior and human-approved execution remain unverified until physical tests; no general sandbox, credential isolation, root or Termux guarantee follows.

## APK #3 physical review

The [phone command review](apps/android/evidence/phone-command-apk3-review.json) accepts the supplied exact-request, one-shot, denial and authentication-negative cases under the ordinary app UID. It does not verify a separate-UID attack, hostile same-UID isolation, all expiry/cancellation paths or background process termination. The manual leave-Activity message is retained as UI evidence only.
