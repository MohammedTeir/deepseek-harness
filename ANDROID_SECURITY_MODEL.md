# Android security risk register

## Summary

Proposed controls only. Upstream `SAFETY.md` states the project is experimental and unaudited. No Android sandbox or authorization system is implemented or verified here.

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
| Session loss/corruption | Native lock loader rejects Android; SQLite/JSONL durability needed | Rebuilt/adapted locking with contention tests, atomic-write/fsync and crash recovery evidence |

Model output, repository content, tools, MCP results and plugins cannot authorize themselves. Denial, changed arguments, replay, expired approval and process death must fail closed. Root stays optional and disabled until its separate gate passes. Avoid logging API keys, launch tokens, sensitive command output or file content by default. The synchronized credential provider now exposes masked previews; these are credential-derived data, not permission to expose full keys. Preserve structured approval rejection/cancellation/unavailability codes in any future native broker.
